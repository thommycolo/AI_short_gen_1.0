"""AI Short Generator 1.0 - Pre-Production Review Engine & 0.60s Composite Verification Frame"""

import os
import subprocess
from pathlib import Path
from dataclasses import dataclass
from typing import List, Dict, Any, Optional

from app.config import (
    CACHE_DIR, REVIEW_FRAME_TIMESTAMP_SEC, DEFAULT_FONT_NAME,
    DEFAULT_FONT_SIZE, DEFAULT_TEXT_COLOR, DEFAULT_HIGHLIGHT_COLOR,
    DEFAULT_OUTLINE_COLOR, DEFAULT_MARGIN_V, PADDING_INTRO_SEC,
    PADDING_OUTRO_SEC
)
from app.core.subtitle_generator import hex_to_ass_color
from app.core.thumbnail_generator import StorySeriesThumbnailGenerator
from app.utils.file_manager import sanitize_ffmpeg_path
from app.utils.ffmpeg_installer import find_system_ffmpeg


@dataclass
class StoryReviewItem:
    story_id: int
    title: str = ""
    script_snippet: str = ""
    word_count: int = 0
    estimated_audio_duration_sec: float = 0.0
    total_video_duration_sec: float = 0.0
    voice_name: str = "Ryan"
    voice_type: str = "en-US"
    instruct_mood: str = "Viral Hook"
    video_source_title: str = ""
    clip_index_label: str = "Part 1"
    bgm_title: str = "None"
    bgm_lufs: float = -24.0
    font_name: str = "Montserrat Black"
    font_size: int = 68
    primary_color_hex: str = "#DCE0EA"
    highlight_color_hex: str = "#BFA175"
    verification_frame_path: str = ""
    intro_banner_text: str = ""
    outro_cta_text: str = ""
    is_feasibility_ok: bool = True

    # Aliases per interoperabilità
    context_title: Optional[str] = None
    text_preview: Optional[str] = None
    est_audio_dur: Optional[float] = None
    est_video_dur: Optional[float] = None
    voice_profile: Optional[str] = None
    voice_instruct: Optional[str] = None
    source_video_title: Optional[str] = None
    video_time_interval: Optional[str] = None
    composite_frame_path: Optional[str] = None
    thumbnail_cover_path: Optional[str] = None

    def __post_init__(self):
        if self.context_title and not self.title:
            self.title = self.context_title
        elif self.title and not self.context_title:
            self.context_title = self.title

        if self.text_preview and not self.script_snippet:
            self.script_snippet = self.text_preview
        elif self.script_snippet and not self.text_preview:
            self.text_preview = self.script_snippet

        if self.est_audio_dur is not None:
            self.estimated_audio_duration_sec = self.est_audio_dur
        if self.est_video_dur is not None:
            self.total_video_duration_sec = self.est_video_dur

        if self.voice_profile:
            self.voice_name = self.voice_profile
        if self.voice_instruct:
            self.instruct_mood = self.voice_instruct

        if self.source_video_title and not self.video_source_title:
            self.video_source_title = self.source_video_title

        if self.composite_frame_path and not self.verification_frame_path:
            self.verification_frame_path = self.composite_frame_path


class PreProductionReviewEngine:
    """
    Genera i dati di riepilogo sintetico e il frame di verifica a 0.600s
    per ogni elemento della coda prima di avviare il rendering finale.
    Include Intro Title Banner e Outro CTA Banner nel preview.
    """

    def __init__(self, cache_dir: Path = CACHE_DIR):
        self.cache_dir = Path(cache_dir)
        self.cache_dir.mkdir(parents=True, exist_ok=True)

    def prepare_queue_review(self, queue_items: List[Dict[str, Any]]) -> List[StoryReviewItem]:
        """Elabora la lista delle storie in coda e genera per ciascuna il frame composito a 0.60s."""
        review_items: List[StoryReviewItem] = []

        for item in queue_items:
            story_id = item.get("story_id", 1)
            title = item.get("title", "Untitled")
            text = item.get("text", "")
            clip_path = item.get("clip_path", "")
            voice_cfg = item.get("voice_config", {})
            sub_cfg = item.get("subtitle_config", {})
            bgm_cfg = item.get("bgm_config", {})
            part_num = item.get("part_num", 1)
            total_parts = item.get("total_parts", 1)

            word_count = len(text.split())
            speed = float(item.get("speed_rate", 1.0))
            est_audio_dur = min(43.0, round((word_count / 2.50) / speed, 1))
            tot_video_dur = est_audio_dur + (PADDING_INTRO_SEC + PADDING_OUTRO_SEC)

            intro_text = f"{title.replace('_', ' ')} part.{part_num}"
            outro_text = f"Follow for part.{part_num + 1}" if part_num < total_parts else "Follow for more!"

            # Generazione ASS temporaneo per il frame a 0.60s
            ass_path = self._generate_temp_review_ass(story_id, title, part_num, text, sub_cfg)

            # Estrazione frame composito con FFmpeg a t = 0.600s
            frame_output = self.cache_dir / f"review_{story_id}_0_6s.jpg"
            self._render_frame_at_0_6s(clip_path, str(ass_path), str(frame_output))

            # Generazione Thumbnail seriale per review
            thumb_cover_path = ""
            try:
                if frame_output.exists():
                    thumb_gen = StorySeriesThumbnailGenerator(cache_dir=self.cache_dir)
                    thumbs = thumb_gen.generate_series_thumbnails(
                        story_id=story_id,
                        context_title=title,
                        total_parts=total_parts,
                        master_frame_path=str(frame_output),
                        font_name=sub_cfg.get("font_name", DEFAULT_FONT_NAME),
                        primary_color_hex=sub_cfg.get("primary_color_hex", DEFAULT_TEXT_COLOR),
                        highlight_color_hex=sub_cfg.get("highlight_color_hex", DEFAULT_HIGHLIGHT_COLOR)
                    )
                    if thumbs:
                        thumb_cover_path = thumbs[0]
            except Exception:
                pass

            review_items.append(StoryReviewItem(
                story_id=story_id,
                title=title,
                script_snippet=" ".join(text.split()[:14]) + "..." if len(text.split()) > 14 else text,
                word_count=word_count,
                estimated_audio_duration_sec=est_audio_dur,
                total_video_duration_sec=tot_video_dur,
                voice_name=voice_cfg.get("speaker", "Ryan (en-US)"),
                voice_type=voice_cfg.get("type", "Custom Voice"),
                instruct_mood=voice_cfg.get("instruct", "Viral Hook"),
                video_source_title=item.get("source_video_title", "Continuous Video Source"),
                clip_index_label=f"Clip {part_num} di {total_parts}",
                bgm_title=bgm_cfg.get("title", "Lofi Chill Background"),
                bgm_lufs=bgm_cfg.get("target_lufs", -24.0),
                font_name=sub_cfg.get("font_name", DEFAULT_FONT_NAME),
                font_size=sub_cfg.get("font_size", DEFAULT_FONT_SIZE),
                primary_color_hex=sub_cfg.get("primary_color_hex", DEFAULT_TEXT_COLOR),
                highlight_color_hex=sub_cfg.get("highlight_color_hex", DEFAULT_HIGHLIGHT_COLOR),
                verification_frame_path=str(frame_output),
                thumbnail_cover_path=thumb_cover_path,
                intro_banner_text=intro_text,
                outro_cta_text=outro_text,
                is_feasibility_ok=True
            ))

        return review_items

    def generate_review_composite_frame(
        self,
        clip_path: str,
        story_title: str,
        clip_num: int = 1,
        sub_cfg: Optional[dict] = None,
        story_id: int = 1,
        script_text: str = ""
    ) -> str:
        """Genera il fotogramma di verifica a 0.600s per una singola storia/clip."""
        cfg = sub_cfg or {}
        ass_path = self._generate_temp_review_ass(
            story_id=story_id,
            title=story_title,
            part_num=clip_num,
            script_text=script_text or story_title,
            sub_cfg=cfg
        )
        frame_output = self.cache_dir / f"review_{story_id}_0_6s.jpg"
        self._render_frame_at_0_6s(clip_path, str(ass_path), str(frame_output))
        return str(frame_output)

    def _generate_temp_review_ass(
        self,
        story_id: int,
        title: str,
        part_num: int,
        script_text: str,
        sub_cfg: dict
    ) -> Path:
        """Crea uno snippet di sottotitoli ASS con Intro Banner a centro schermo e prima battuta attiva a t = 0.50s."""
        ass_path = self.cache_dir / f"temp_review_{story_id}.ass"
        words = script_text.split()[:4]
        if not words:
            words = ["DISCOVER", "THIS", "STORY"]

        first_word = words[0].upper()
        other_words = " ".join([w.upper() for w in words[1:]])

        font_name = sub_cfg.get("font_name", DEFAULT_FONT_NAME)
        font_size = sub_cfg.get("font_size", DEFAULT_FONT_SIZE)
        margin_v = sub_cfg.get("margin_v", DEFAULT_MARGIN_V)
        intro_banner_text = f"{title.replace('_', ' ')} part.{part_num}"

        primary_ass = hex_to_ass_color(sub_cfg.get("primary_color_hex", DEFAULT_TEXT_COLOR))
        highlight_ass = hex_to_ass_color(sub_cfg.get("highlight_color_hex", DEFAULT_HIGHLIGHT_COLOR))
        outline_ass = hex_to_ass_color(sub_cfg.get("outline_color_hex", DEFAULT_OUTLINE_COLOR))

        ass_content = f"""[Script Info]
Title: Review Frame 0.6s
ScriptType: v4.00+
PlayResX: 1080
PlayResY: 1920

[V4+ Styles]
Format: Name, Fontname, Fontsize, PrimaryColour, SecondaryColour, OutlineColour, BackColour, Bold, Italic, Underline, StrikeOut, ScaleX, ScaleY, Spacing, Angle, BorderStyle, Outline, Shadow, Alignment, MarginL, MarginR, MarginV, Encoding
Style: TitleBanner,{font_name},64,&H00FFFFFF,&H00FFFFFF,{outline_ass},&H00000000,-1,0,0,0,100,100,2,0,1,0,0,5,60,60,0,1
Style: SubtitleWord,{font_name},{font_size},{primary_ass},{primary_ass},{outline_ass},&H00000000,-1,0,0,0,100,100,1,0,1,0,0,2,60,60,{margin_v},1

[Events]
Format: Layer, Start, End, Style, Name, MarginL, MarginR, MarginV, Effect, Text
; Intro Title Banner al centro (0.0s -> 1.00s)
Dialogue: 1,0:00:00.00,0:00:01.00,TitleBanner,,0,0,0,,{{\\fade(150,200)}}{intro_banner_text}
; Sottotitolo uniforme senza evidenziazione (1.00s -> 2.00s)
Dialogue: 0,0:00:01.00,0:00:02.00,SubtitleWord,,0,0,0,,{first_word} {other_words}
"""
        ass_path.write_text(ass_content, encoding="utf-8")
        return ass_path

    def _render_frame_at_0_6s(self, clip_path: str, ass_path: str, output_jpg: str):
        """Estrae il fotogramma al millisecondo 600 con sottotitolo impresso ed escape sicuro percorsi Windows."""
        safe_ass = sanitize_ffmpeg_path(ass_path)
        ffmpeg_bin, _ = find_system_ffmpeg()
        ffmpeg_cmd = ffmpeg_bin if ffmpeg_bin else "ffmpeg"

        if not clip_path or not os.path.exists(clip_path):
            cmd = [
                ffmpeg_cmd, "-y",
                "-f", "lavfi", "-i", "color=c=#21242C:s=1080x1920:d=1",
                "-vf", f"subtitles='{safe_ass}'",
                "-vframes", "1",
                "-q:v", "2",
                output_jpg
            ]
        else:
            cmd = [
                ffmpeg_cmd, "-y",
                "-ss", f"{REVIEW_FRAME_TIMESTAMP_SEC:.3f}",
                "-i", clip_path,
                "-vf", f"subtitles='{safe_ass}'",
                "-vframes", "1",
                "-q:v", "2",
                output_jpg
            ]
        try:
            subprocess.run(cmd, capture_output=True, check=True)
        except Exception:
            # Fallback generazione immagine con pillow se ffmpeg non ha libass
            from PIL import Image, ImageDraw
            img = Image.new("RGB", (1080, 1920), color="#21242C")
            draw = ImageDraw.Draw(img)
            draw.text((540, 960), "Review Frame 0.6s", fill="#DCE0EA", anchor="mm")
            img.save(output_jpg, "JPEG")
