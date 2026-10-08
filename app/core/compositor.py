"""AI Short Generator 1.0 - Hardware Video Compositor (NVENC Single-Pass & Preventive Normalization)"""

import os
import re
import subprocess
import threading
from pathlib import Path
from typing import List, Dict, Any, Optional, Callable

from app.config import (
    CANVAS_WIDTH, CANVAS_HEIGHT, TARGET_FPS, PADDING_INTRO_SEC,
    PADDING_OUTRO_SEC
)
from app.utils.file_manager import sanitize_ffmpeg_path
from app.utils.ffmpeg_installer import find_system_ffmpeg
from app.utils.logger import log


class VideoCompositor:
    """
    Esegue il montaggio in singolo passaggio accelerato da GPU (NVENC):
    - Grafo di normalizzazione preventiva (fps=60, setsar=1, format=nv12, 1080x1920)
    - Concatenazione hardware anti-crash per spezzoni da master differenti della stessa categoria
    - Burn-in sottotitoli ASS e banner centrati
    - Transcodifica finale H.264 High Profile con fallback CPU (-crf 18)
    """

    def __init__(self):
        self._check_nvenc_support()

    def _check_nvenc_support(self) -> bool:
        ffmpeg_bin, _ = find_system_ffmpeg()
        ffmpeg_cmd = ffmpeg_bin if ffmpeg_bin else "ffmpeg"
        try:
            res = subprocess.run([ffmpeg_cmd, "-encoders"], capture_output=True, text=True)
            self.has_nvenc = "h264_nvenc" in res.stdout
        except Exception:
            self.has_nvenc = False
        return self.has_nvenc

    def render_short_video(
        self,
        video_segments: List[Dict[str, Any]], # [{"file_path": str, "start_sec": float, "duration_sec": float}]
        audio_file_path: str,
        ass_subtitles_path: str,
        output_mp4_path: str,
        total_duration_sec: float,
        on_progress: Optional[Callable[[float], None]] = None,
        cancellation_manager: Optional[Any] = None
    ) -> str:
        """
        Assembla il video definitivo con audio e sottotitoli in un unico passaggio.
        """
        Path(output_mp4_path).parent.mkdir(parents=True, exist_ok=True)
        ffmpeg_bin, _ = find_system_ffmpeg()
        ffmpeg_cmd = ffmpeg_bin if ffmpeg_bin else "ffmpeg"
        safe_ass = sanitize_ffmpeg_path(ass_subtitles_path)

        cmd = [ffmpeg_cmd, "-y"]

        # 1. Input Video
        for seg in video_segments:
            cmd.extend([
                "-ss", f"{seg['start_sec']:.3f}",
                "-t", f"{seg['duration_sec']:.3f}",
                "-i", str(seg['file_path'])
            ])

        # Input Audio
        audio_input_idx = len(video_segments)
        cmd.extend(["-i", str(audio_file_path)])

        # 2. Filter Graph di Normalizzazione Hardware
        filter_parts = []
        n_segments = len(video_segments)

        for i in range(n_segments):
            # Normalizzazione preventiva per ogni flusso prima del concat
            filter_parts.append(
                f"[{i}:v]fps={TARGET_FPS},setsar=1,format=nv12,"
                f"scale={CANVAS_WIDTH}:{CANVAS_HEIGHT}:force_original_aspect_ratio=increase,"
                f"crop={CANVAS_WIDTH}:{CANVAS_HEIGHT}[v{i}]"
            )

        if n_segments == 1:
            concat_output = "[v0]"
        else:
            v_inputs = "".join(f"[v{i}]" for i in range(n_segments))
            filter_parts.append(f"{v_inputs}concat=n={n_segments}:v=1:a=0[vconcat]")
            concat_output = "[vconcat]"

        # Overlay sottotitoli ASS (include Title Banner e Outro CTA Banner)
        filter_parts.append(f"{concat_output}subtitles='{safe_ass}'[vfinal]")

        filter_complex_str = "; ".join(filter_parts)

        cmd.extend([
            "-filter_complex", filter_complex_str,
            "-map", "[vfinal]",
            "-map", f"{audio_input_idx}:a",
            "-t", f"{total_duration_sec:.3f}"
        ])

        # 3. Parametri Encoder (NVENC GPU con fallback CPU)
        if self.has_nvenc:
            cmd.extend([
                "-c:v", "h264_nvenc",
                "-preset", "p4",
                "-cq", "20",
                "-profile:v", "high"
            ])
        else:
            cmd.extend([
                "-c:v", "libx264",
                "-preset", "fast",
                "-crf", "18",
                "-profile:v", "high"
            ])

        cmd.extend([
            "-c:a", "aac",
            "-b:a", "192k",
            "-pix_fmt", "yuv420p",
            "-progress", "pipe:1",
            str(output_mp4_path)
        ])

        # Esecuzione subprocess monitorata con drain asincrono di stderr (anti-deadlock buffer OS)
        process = subprocess.Popen(
            cmd,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            text=True,
            encoding="utf-8",
            errors="replace",
            bufsize=1
        )

        stderr_lines: List[str] = []

        def _drain_stderr(pipe):
            try:
                for err_line in iter(pipe.readline, ""):
                    stderr_lines.append(err_line)
            except Exception:
                pass
            finally:
                try:
                    pipe.close()
                except Exception:
                    pass

        stderr_thread = threading.Thread(target=_drain_stderr, args=(process.stderr,), daemon=True)
        stderr_thread.start()

        if cancellation_manager:
            cancellation_manager.register_ffmpeg_process(process)

        try:
            while True:
                if cancellation_manager and cancellation_manager.is_cancelled():
                    process.terminate()
                    break

                line = process.stdout.readline() if process.stdout else ""
                if not line and process.poll() is not None:
                    break

                if "out_time_us=" in line:
                    try:
                        us_val = float(line.split("=")[1].strip())
                        cur_sec = us_val / 1000000.0
                        pct = min(100.0, max(0.0, (cur_sec / total_duration_sec) * 100.0))
                        if on_progress:
                            on_progress(pct)
                    except Exception:
                        pass

            rc = process.wait()
            stderr_thread.join(timeout=2.0)
            if rc != 0:
                stderr_out = "".join(stderr_lines[-30:]) if stderr_lines else ""
                raise RuntimeError(f"FFmpeg compositing fallito (code {rc}): {stderr_out}")

        finally:
            if cancellation_manager:
                cancellation_manager.unregister_ffmpeg_process()
            if process.stdout:
                try:
                    process.stdout.close()
                except Exception:
                    pass

        return str(output_mp4_path)

