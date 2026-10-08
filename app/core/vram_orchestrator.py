"""AI Short Generator 1.0 - VRAM Lifecycle Orchestrator (Subprocess Spawn Isolation & 3-Phase Pipeline)"""

import os
import re
import gc
import json
import time
import subprocess
import multiprocessing
from pathlib import Path
from dataclasses import dataclass
from typing import List, Dict, Any, Optional, Callable

from app.config import (
    CACHE_DIR, RENDERS_DIR, PADDING_INTRO_SEC, PADDING_OUTRO_SEC,
    PADDING_TOTAL_SEC, VRAM_APP_NET_BUDGET_MB, VRAM_MAX_CEILING_MB
)
from app.core.tts_engine import Qwen3VoiceSuite
from app.core.discourse_chunker import DiscourseCoherenceChunker
from app.core.silero_vad_trimmer import SileroVADSilenceTrimmer
from app.core.subtitle_generator import SubtitleGenerator
from app.core.thumbnail_generator import StorySeriesThumbnailGenerator
from app.core.continuous_video_manager import ContinuousVideoPoolManager
from app.core.compositor import VideoCompositor
from app.core.bgm_manager import BgmManager
from app.core.cancellation_manager import ProductionCancellationManager
from app.utils.logger import log

try:
    from faster_whisper import WhisperModel
except ImportError:
    WhisperModel = None


# Worker function for Phase A (TTS)
def _tts_worker_proc(task_data: dict, result_queue: multiprocessing.Queue):
    """Eseguito in processo isolato (spawn): alla chiusura, Windows WDDM bonifica 100% VRAM."""
    os.environ["PYTORCH_CUDA_ALLOC_CONF"] = "expandable_segments:True"
    try:
        text = task_data["text"]
        out_wav = task_data["output_wav"]
        speaker = task_data.get("speaker", "Ryan")
        instruct = task_data.get("instruct", "")
        speed = float(task_data.get("speed", 1.0))

        suite = Qwen3VoiceSuite()
        measured_dur = suite.generate_custom(
            text=text,
            output_path=out_wav,
            speaker=speaker,
            instruct=instruct,
            speed=speed
        )
        result_queue.put({"success": True, "duration": measured_dur})
    except Exception as e:
        result_queue.put({"success": False, "error": str(e)})


# Worker function for Phase B (Whisper)
def _whisper_worker_proc(task_data: dict, result_queue: multiprocessing.Queue):
    """Eseguito in processo isolato (spawn) su CUDA INT8 (1.1 GB): esce subito rilasciando la GPU."""
    try:
        audio_path = task_data["audio_path"]
        text_words = task_data.get("text", "").split()
        dur = float(task_data.get("duration", 30.0))

        word_events = []
        if WhisperModel is not None:
            try:
                import torch
                from app.config import MODELS_DIR
                local_whisper = MODELS_DIR / "faster-whisper-large-v3-turbo"
                if (local_whisper / "model.bin").exists():
                    model_source = str(local_whisper)
                else:
                    model_source = "large-v3-turbo"

                device = "cuda" if (torch and torch.cuda.is_available()) else "cpu"
                compute_type = "int8_float16" if device == "cuda" else "int8"
                try:
                    whisper = WhisperModel(model_source, device=device, compute_type=compute_type)
                except Exception as e_cuda:
                    log.warning(f"Whisper CUDA init fallito ({e_cuda}), fallback su CPU INT8.")
                    whisper = WhisperModel(model_source, device="cpu", compute_type="int8")

                segments, _ = whisper.transcribe(audio_path, language="en", word_timestamps=True)
                for seg in segments:
                    if seg.words:
                        for w in seg.words:
                            word_events.append({
                                "word": w.word.strip(),
                                "start": float(w.start),
                                "end": float(w.end),
                                "probability": float(w.probability)
                            })
                del whisper
            except Exception as e_w:
                log.warning(f"Whisper alignment fallito: {e_w}. Utilizzo fallback proporzionale.")
                word_events = []

        if not word_events and text_words:
            # Fallback temporale proporzionale preciso
            step = dur / max(1, len(text_words))
            for i, w in enumerate(text_words):
                st = i * step
                en = (i + 1) * step
                word_events.append({"word": w, "start": st, "end": en, "probability": 1.0})

        result_queue.put({"success": True, "word_events": word_events})
    except Exception as e:
        # Fallback di sicurezza incondizionato
        try:
            text_words = task_data.get("text", "").split()
            dur = float(task_data.get("duration", 30.0))
            fb = []
            if text_words:
                step = dur / max(1, len(text_words))
                for i, w in enumerate(text_words):
                    fb.append({"word": w, "start": i * step, "end": (i + 1) * step, "probability": 1.0})
            result_queue.put({"success": True, "word_events": fb})
        except Exception:
            result_queue.put({"success": False, "error": str(e)})


@dataclass
class ProductionJob:
    story_id: int
    context_title: str
    text: str
    category: str = "General"
    voice_config: Optional[dict] = None
    subtitle_config: Optional[dict] = None
    bgm_config: Optional[dict] = None
    speed_rate: float = 1.0


class VRAMLifecycleOrchestrator:
    """
    Orchestra la produzione in 3 fasi isolate con budget netto < 2.8 GB:
    - Fase A: Qwen3-TTS subprocess worker (VRAM ~2.5 GB -> dealloca al 100%)
    - Fase B: Faster-Whisper INT8 CUDA subprocess worker (VRAM ~1.1 GB -> dealloca al 100%)
    - Fase C: FFmpeg NVENC Video Compositor (NVENC buffer ~0.4 GB)
    """

    def __init__(
        self,
        video_manager: Optional[ContinuousVideoPoolManager] = None,
        cancellation_mgr: Optional[ProductionCancellationManager] = None,
        bgm_manager: Optional[BgmManager] = None
    ):
        self.video_manager = video_manager or ContinuousVideoPoolManager()
        self.cancellation_mgr = cancellation_mgr or ProductionCancellationManager()
        self.bgm_manager = bgm_manager or BgmManager()
        self.chunker = DiscourseCoherenceChunker()
        self.subtitle_gen = SubtitleGenerator()
        self.thumb_gen = StorySeriesThumbnailGenerator()
        self.compositor = VideoCompositor()

    def run_phase_a_tts_isolated(self, text: str, output_wav: str, voice_cfg: dict, speed: float = 1.0) -> float:
        """Esegue la sintesi vocale in un processo subprocess separato per bonifica totale WDDM."""
        ctx = multiprocessing.get_context("spawn")
        q = ctx.Queue()
        task = {
            "text": text,
            "output_wav": output_wav,
            "speaker": voice_cfg.get("speaker", "Ryan"),
            "instruct": voice_cfg.get("instruct", ""),
            "speed": speed
        }

        p = ctx.Process(target=_tts_worker_proc, args=(task, q))
        p.start()
        p.join(timeout=300)

        if p.is_alive():
            p.terminate()
            raise TimeoutError("Timeout sintesi vocale TTS worker.")

        if q.empty():
            raise RuntimeError("Nessuna risposta dal worker TTS.")

        res = q.get()
        if not res["success"]:
            raise RuntimeError(f"Errore worker TTS: {res.get('error')}")

        return float(res["duration"])

    def run_phase_b_whisper_isolated(self, audio_wav: str, text: str, duration: float) -> List[Dict[str, Any]]:
        """Esegue l'allineamento Whisper in un processo subprocess separato su GPU pulita."""
        ctx = multiprocessing.get_context("spawn")
        q = ctx.Queue()
        task = {
            "audio_path": audio_wav,
            "text": text,
            "duration": duration
        }

        timeout_sec = max(300, int(duration * 6))
        p = ctx.Process(target=_whisper_worker_proc, args=(task, q))
        p.start()
        p.join(timeout=timeout_sec)

        if p.is_alive():
            p.terminate()
            log.warning("Timeout Whisper alignment worker: applicato fallback proporzionale.")
            text_words = text.split()
            fb_events = []
            if text_words:
                step = duration / max(1, len(text_words))
                for i, w in enumerate(text_words):
                    fb_events.append({"word": w, "start": i * step, "end": (i + 1) * step, "probability": 1.0})
            return fb_events

        if q.empty():
            log.warning("Nessuna risposta dal worker Whisper: applicato fallback proporzionale.")
            text_words = text.split()
            fb_events = []
            if text_words:
                step = duration / max(1, len(text_words))
                for i, w in enumerate(text_words):
                    fb_events.append({"word": w, "start": i * step, "end": (i + 1) * step, "probability": 1.0})
            return fb_events

        res = q.get()
        if not res.get("success"):
            log.warning(f"Errore worker Whisper: {res.get('error')}. Applicato fallback proporzionale.")
            text_words = text.split()
            fb_events = []
            if text_words:
                step = duration / max(1, len(text_words))
                for i, w in enumerate(text_words):
                    fb_events.append({"word": w, "start": i * step, "end": (i + 1) * step, "probability": 1.0})
            return fb_events

        return res.get("word_events", [])

    def process_story(
        self,
        job: ProductionJob,
        on_step_progress: Optional[Callable[[int, str, float], None]] = None # (part_num, phase_name, pct)
    ) -> List[str]:
        """
        Elabora l'intera storia producendo tutti i suoi Short sequenziali.
        Se si verifica un'interruzione, applica il rollback atomico per la storia.
        """
        if self.cancellation_mgr.is_cancelled():
            return []

        story_id = job.story_id
        title = job.context_title
        raw_text = job.text
        voice_cfg = job.voice_config or {}
        sub_cfg = job.subtitle_config or {}
        bgm_cfg = job.bgm_config or {}
        speed = job.speed_rate

        # 1. Suddivisione in parti coerenti (+-7s)
        parts = self.chunker.chunk_story_coherently(raw_text, avg_wps=2.50 * speed)
        if not parts:
            parts = [raw_text]
        total_parts = len(parts)

        produced_shorts = []
        master_thumb_frame = None

        try:
            for part_idx, part_text in enumerate(parts):
                part_num = part_idx + 1

                if self.cancellation_mgr.is_cancelled():
                    raise InterruptedError("Produzione interrotta dall'utente.")

                # --- FASE 1: SINTESI VOCALE QWEN3-TTS & GROUND TRUTH ---
                if on_step_progress:
                    on_step_progress(part_num, "Sintesi Vocale Qwen3-TTS", 10.0)

                temp_wav = str(CACHE_DIR / f"temp_voice_{story_id}_p{part_num}.wav")
                audio_dur = self.run_phase_a_tts_isolated(part_text, temp_wav, voice_cfg, speed=speed)

                # Calcolo Ground Truth Temporale
                video_needed_dur = audio_dur + PADDING_TOTAL_SEC # +2.0s

                if on_step_progress:
                    on_step_progress(part_num, "Allineamento Sottotitoli Whisper", 35.0)

                # --- FASE 2: ALLINEAMENTO WHISPER & ASS SUBTITLES ---
                word_events = self.run_phase_b_whisper_isolated(temp_wav, part_text, audio_dur)

                ass_path = str(CACHE_DIR / f"temp_subs_{story_id}_p{part_num}.ass")
                self.subtitle_gen.generate_ass(
                    word_events=word_events,
                    output_ass_path=ass_path,
                    context_title=title,
                    part_num=part_num,
                    total_parts=total_parts,
                    total_video_duration=video_needed_dur,
                    style_config=sub_cfg
                )

                if on_step_progress:
                    on_step_progress(part_num, "Prenotazione Video Continuo & BGM", 60.0)

                # --- FASE 3: RISERVA SEGMENTO CONTINUO DAL VIDEO POOL ---
                candidate_sources = self.video_manager.get_sources(category=job.category)
                if not candidate_sources:
                    candidate_sources = self.video_manager.get_sources(category="General")
                if not candidate_sources:
                    candidate_sources = self.video_manager.get_all_sources()

                if not candidate_sources:
                    raise RuntimeError("Nessuna sorgente video disponibile nel Video Pool.")

                src_id = candidate_sources[0]["id"]
                src_path = candidate_sources[0]["file_path"]

                # Riserva segmento continuo
                start_t, end_t = self.video_manager.reserve_segment_for_story(
                    source_id=src_id,
                    script_id=story_id,
                    duration_sec=video_needed_dur
                )

                # Estrazione frame master per thumbnail unificata di serie
                if master_thumb_frame is None:
                    master_thumb_frame = self.thumb_gen.extract_story_master_frame(
                        master_video_path=src_path,
                        story_id=story_id,
                        timestamp_sec=start_t + 0.600
                    )

                if on_step_progress:
                    on_step_progress(part_num, "Mastering Audio & BGM Ducking", 75.0)

                # --- FASE 4: MASTERING AUDIO (PADDING + BGM DUCKING + TRUE PEAK LIMITER) ---
                bgm_track_path = None
                if bgm_cfg.get("bgm_track_id"):
                    b_track = self.bgm_manager.get_track_by_id(int(bgm_cfg["bgm_track_id"]))
                    if b_track and os.path.exists(b_track["file_path"]):
                        bgm_track_path = b_track["file_path"]

                final_audio_wav = str(CACHE_DIR / f"temp_master_audio_{story_id}_p{part_num}.wav")
                self.bgm_manager.mix_narration_and_bgm_ducking(
                    voice_wav_path=temp_wav,
                    bgm_wav_path=bgm_track_path,
                    voice_duration_sec=audio_dur,
                    output_mixed_audio=final_audio_wav,
                    ducking_db=bgm_cfg.get("ducking_db", bgm_cfg.get("voice_duck_db", -22.0)),
                    intro_outro_db=bgm_cfg.get("intro_outro_db", bgm_cfg.get("intro_outro_duck_db", -14.0))
                )

                if on_step_progress:
                    on_step_progress(part_num, "Montaggio Hardware NVENC Single-Pass", 80.0)

                # --- FASE 5: MONTAGGIO HARDWARE NVENC ---
                safe_title = re.sub(r'[\\/*?:"<>|]', "", title).strip().replace(" ", "_")
                output_mp4 = str(RENDERS_DIR / f"{safe_title}_part{part_num}.mp4")

                segments = [{
                    "file_path": src_path,
                    "start_sec": start_t,
                    "duration_sec": video_needed_dur
                }]

                def _ffmpeg_cb(pct):
                    if on_step_progress:
                        on_step_progress(part_num, "Montaggio Hardware NVENC", 80.0 + (pct * 0.18))

                self.compositor.render_short_video(
                    video_segments=segments,
                    audio_file_path=final_audio_wav,
                    ass_subtitles_path=ass_path,
                    output_mp4_path=output_mp4,
                    total_duration_sec=video_needed_dur,
                    on_progress=_ffmpeg_cb,
                    cancellation_manager=self.cancellation_mgr
                )

                produced_shorts.append(output_mp4)

            # Generazione Thumbnail Seriali Coordinate (Same-Frame Series Branding)
            if master_thumb_frame and os.path.exists(master_thumb_frame):
                self.thumb_gen.generate_series_thumbnails(
                    story_id=story_id,
                    context_title=title,
                    total_parts=total_parts,
                    master_frame_path=master_thumb_frame,
                    font_name=sub_cfg.get("font_name", "Montserrat Black"),
                    primary_color_hex=sub_cfg.get("primary_color_hex", "#DCE0EA"),
                    highlight_color_hex=sub_cfg.get("highlight_color_hex", "#BFA175")
                )

            if on_step_progress:
                on_step_progress(total_parts, "Completato", 100.0)

            return produced_shorts

        except Exception as e:
            # Rollback atomico non-distruttivo per la storia incompleta
            self.cancellation_mgr.execute_granular_rollback(
                completed_story_ids=[],
                uncompleted_story_ids=[story_id]
            )
            raise e

