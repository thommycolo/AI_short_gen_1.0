"""AI Short Generator 1.0 - Series Thumbnail Generator (Same-Frame Series Branding)"""

import os
import subprocess
from pathlib import Path
from typing import List, Optional
from PIL import Image, ImageDraw, ImageFont

from app.config import (
    CANVAS_WIDTH, CANVAS_HEIGHT, FONTS_DIR, RENDERS_DIR, CACHE_DIR,
    DEFAULT_FONT_NAME, DEFAULT_TEXT_COLOR, DEFAULT_HIGHLIGHT_COLOR,
    DEFAULT_OUTLINE_COLOR
)
from app.utils.ffmpeg_installer import find_system_ffmpeg


class StorySeriesThumbnailGenerator:
    """
    Genera le thumbnail seriali per l'intera storia con fotogramma di sfondo identico
    e titolazione a due righe: [titolo storia] \n part.[numero clip].
    Utilizza rendering FreeType (Pillow) ad altissima velocità (< 25ms per immagine) su CPU.
    """
    CANVAS_WIDTH = CANVAS_WIDTH
    CANVAS_HEIGHT = CANVAS_HEIGHT
    DEFAULT_TITLE_FONT_SIZE = 76
    DEFAULT_PART_FONT_SIZE = 64
    OUTLINE_WIDTH = 8

    def __init__(
        self,
        fonts_dir: Path = FONTS_DIR,
        renders_dir: Path = RENDERS_DIR,
        cache_dir: Path = CACHE_DIR
    ):
        self.fonts_dir = Path(fonts_dir)
        self.renders_dir = Path(renders_dir)
        self.cache_dir = Path(cache_dir)
        self.renders_dir.mkdir(parents=True, exist_ok=True)
        self.cache_dir.mkdir(parents=True, exist_ok=True)

    def extract_story_master_frame(self, master_video_path: str, story_id: int, timestamp_sec: float = 0.600) -> str:
        """
        Estrae il fotogramma di riferimento unificato ad alta fedeltà (JPEG 1080x1920)
        che fungerà da sfondo identico per tutte le thumbnail della serie.
        """
        output_frame = str(self.cache_dir / f"story_{story_id}_master_thumb_bg.jpg")
        ffmpeg_bin, _ = find_system_ffmpeg()
        ffmpeg_cmd = ffmpeg_bin if ffmpeg_bin else "ffmpeg"

        cmd = [
            ffmpeg_cmd, "-y",
            "-ss", f"{timestamp_sec:.3f}",
            "-i", str(master_video_path),
            "-vframes", "1",
            "-q:v", "2",
            output_frame
        ]
        subprocess.run(cmd, capture_output=True, check=True)
        return output_frame

    def _resolve_font_path(self, font_name: str) -> str:
        """Risolve il path del file .ttf corrispondente al nome tipografico scelto per lo Short."""
        font_clean = font_name.lower().replace(" ", "").replace("_", "")
        if self.fonts_dir.exists():
            for font_file in self.fonts_dir.glob("*.ttf"):
                stem_clean = font_file.stem.lower().replace(" ", "").replace("_", "")
                if font_clean in stem_clean or stem_clean in font_clean:
                    return str(font_file.resolve())

        win_fonts = Path("C:/Windows/Fonts")
        if win_fonts.exists():
            for f in win_fonts.glob("*.ttf"):
                if font_clean in f.stem.lower():
                    return str(f.resolve())
            arial = win_fonts / "arialbd.ttf"
            if arial.exists():
                return str(arial.resolve())

        fallback = list(self.fonts_dir.glob("*.ttf"))
        return str(fallback[0].resolve()) if fallback else "arial.ttf"

    def generate_series_thumbnails(
        self,
        story_id: int,
        context_title: str,
        total_parts: int,
        master_frame_path: str = "",
        font_name: str = DEFAULT_FONT_NAME,
        primary_color_hex: str = DEFAULT_TEXT_COLOR,
        highlight_color_hex: str = DEFAULT_HIGHLIGHT_COLOR,
        outline_color_hex: str = DEFAULT_OUTLINE_COLOR,
        master_frame_jpg: Optional[str] = None
    ) -> List[str]:
        """
        Genera le copertine per tutte le N parti della storia riutilizzando
        lo stesso fotogramma di sfondo con testo a due righe:
        Riga 1: context_title
        Riga 2: part.[part_num]
        """
        if not master_frame_path and master_frame_jpg:
            master_frame_path = master_frame_jpg

        generated_thumbnails: List[str] = []
        font_path = self._resolve_font_path(font_name)

        if not os.path.exists(master_frame_path):
            # Fallback canvas se frame non esiste
            base_bg_image = Image.new("RGB", (self.CANVAS_WIDTH, self.CANVAS_HEIGHT), color="#21242C")
        else:
            base_bg_image = Image.open(master_frame_path).convert("RGBA")
            if base_bg_image.size != (self.CANVAS_WIDTH, self.CANVAS_HEIGHT):
                base_bg_image = base_bg_image.resize((self.CANVAS_WIDTH, self.CANVAS_HEIGHT), Image.Resampling.LANCZOS)

        # Adattamento dinamico dimensione font se il titolo è lungo
        title_text = context_title.replace("_", " ").strip()
        title_font_size = self.DEFAULT_TITLE_FONT_SIZE
        if len(title_text) > 22:
            title_font_size = max(42, int(self.DEFAULT_TITLE_FONT_SIZE * (22 / len(title_text))))
        part_font_size = self.DEFAULT_PART_FONT_SIZE

        try:
            title_font = ImageFont.truetype(font_path, title_font_size)
            part_font = ImageFont.truetype(font_path, part_font_size)
        except Exception:
            title_font = ImageFont.load_default()
            part_font = ImageFont.load_default()

        for part_num in range(1, total_parts + 1):
            thumb_image = base_bg_image.copy()
            draw = ImageDraw.Draw(thumb_image)

            part_text = f"part.{part_num}"

            title_bbox = draw.textbbox((0, 0), title_text, font=title_font)
            title_w = title_bbox[2] - title_bbox[0]
            title_h = title_bbox[3] - title_bbox[1]

            part_bbox = draw.textbbox((0, 0), part_text, font=part_font)
            part_w = part_bbox[2] - part_bbox[0]
            part_h = part_bbox[3] - part_bbox[1]

            spacing_y = 22
            total_block_h = title_h + spacing_y + part_h

            # Coordinate di centraggio (Safe Zone 1:1 e 3:4 - baricentro a Y=900)
            center_x = self.CANVAS_WIDTH // 2
            start_y = 900 - (total_block_h // 2)

            title_pos_x = center_x - (title_w // 2)
            title_pos_y = start_y

            part_pos_x = center_x - (part_w // 2)
            part_pos_y = start_y + title_h + spacing_y

            # 1. Disegna Riga 1 (Titolo) con Stroke Outlined
            draw.text(
                (title_pos_x, title_pos_y),
                title_text,
                font=title_font,
                fill=primary_color_hex,
                stroke_width=self.OUTLINE_WIDTH,
                stroke_fill=outline_color_hex
            )

            # 2. Disegna Riga 2 (part.[N]) con Stroke Outlined
            draw.text(
                (part_pos_x, part_pos_y),
                part_text,
                font=part_font,
                fill=primary_color_hex,
                stroke_width=self.OUTLINE_WIDTH,
                stroke_fill=outline_color_hex
            )

            # Salvataggio thumbnail JPEG ad alta qualità
            safe_title = context_title.replace(" ", "_")
            output_filename = f"{safe_title}_part{part_num}_thumb.jpg"
            output_path = str(self.renders_dir / output_filename)

            rgb_thumb = thumb_image.convert("RGB")
            rgb_thumb.save(output_path, "JPEG", quality=95, optimize=True)
            generated_thumbnails.append(output_path)

        return generated_thumbnails

