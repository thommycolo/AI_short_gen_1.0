"""AI Short Generator 1.0 - Subtitle Generator, Geometric ASS Bounding Box & Centered Banners"""

import os
from pathlib import Path
from typing import List, Dict, Any, Optional

try:
    from PIL import ImageFont
except ImportError:
    ImageFont = None

from app.config import (
    CANVAS_WIDTH, CANVAS_HEIGHT, SUBTITLE_SAFE_WIDTH_PX,
    SUBTITLE_MAX_WORDS_PER_LINE, SUBTITLE_MAX_LINES, DEFAULT_MARGIN_V,
    DEFAULT_FONT_NAME, DEFAULT_FONT_SIZE, DEFAULT_TEXT_COLOR,
    DEFAULT_HIGHLIGHT_COLOR, DEFAULT_OUTLINE_COLOR, DEFAULT_OUTLINE_WIDTH,
    DEFAULT_SHADOW_RADIUS, PADDING_INTRO_SEC, PADDING_OUTRO_SEC,
    INTRO_BANNER_START_SEC, INTRO_BANNER_END_SEC, OUTRO_CTA_LEAD_TIME_SEC,
    FONTS_DIR
)


def hex_to_ass_color(hex_str: str, alpha: str = "00") -> str:
    """
    Converte un colore esadecimale Web (#RRGGBB) nello standard ASS (&H[AA][BB][GG][RR]&).
    Inverte i canali Rosso e Blu (BGR), scongiurando la resa cromatica sbiadita o errata
    e preservando fedelmente la palette soft dark / oro (#BFA175 -> &H0075A1BF&).
    """
    h = hex_str.lstrip("#")
    if len(h) == 6:
        r, g, b = h[0:2], h[2:4], h[4:6]
        return f"&H{alpha}{b}{g}{r}&".upper()
    return f"&H{alpha}FFFFFF&"


def format_ass_time(seconds: float) -> str:
    """Formatta i secondi nello standard temporale ASS H:MM:SS.CC (centesimi)."""
    h = int(seconds // 3600)
    m = int((seconds % 3600) // 60)
    s = seconds % 60
    return f"{h}:{m:02d}:{s:05.2f}"


class SubtitleGenerator:
    """
    Genera il file di sottotitoli ASS a multi-livello sincronizzato al millisecondo:
    - Bounding Box Geometrico in pixel (ImageFont.getlength() <= 880px)
    - Offset Vocale +0.500s (adelay)
    - Intro Title Banner al Centro (Alignment 5, 0.0s -> 1.5s, medesimo font)
    - Outro CTA Banner al Centro (Alignment 5, T_video - 1.0s -> fine, medesimo font)
    - Karaoke dinamico parola per parola nella Safe-Zone inferiore (Alignment 2, Y=440)
    """

    def __init__(self, fonts_dir: Path = FONTS_DIR):
        self.fonts_dir = Path(fonts_dir)

    def resolve_font_path(self, font_name: str) -> Optional[str]:
        """Trova il font .ttf o .otf nella cartella assets/fonts/ o cartella di sistema."""
        font_clean = font_name.lower().replace(" ", "").replace("_", "")
        if self.fonts_dir.exists():
            for ext in ("*.ttf", "*.otf", "*.TTF", "*.OTF"):
                for font_file in self.fonts_dir.glob(ext):
                    stem_clean = font_file.stem.lower().replace(" ", "").replace("_", "")
                    if font_clean in stem_clean or stem_clean in font_clean:
                        return str(font_file.resolve())

        # Cerca nei font di sistema Windows
        win_fonts = Path("C:/Windows/Fonts")
        if win_fonts.exists():
            for ext in ("*.ttf", "*.otf", "*.TTF", "*.OTF"):
                for f in win_fonts.glob(ext):
                    if font_clean in f.stem.lower():
                        return str(f.resolve())

        return None

    def wrap_words_geometrically(
        self,
        words: List[Dict[str, Any]],
        font_name: str,
        font_size: int,
        max_width_px: int = SUBTITLE_SAFE_WIDTH_PX
    ) -> List[List[Dict[str, Any]]]:
        r"""
        Auto-impaginazione geometrica reale tramite ImageFont.getlength() (Pillow):
        - Safe Zone <= 880px
        - Max 3 parole per riga, max 2 righe per visualizzazione (max 6 parole a schermo)
        - Inserisce ritorno a capo \N o spezza in eventi successivi.
        """
        font = None
        font_path = self.resolve_font_path(font_name)
        if ImageFont and font_path:
            try:
                font = ImageFont.truetype(font_path, font_size)
            except Exception:
                font = None

        chunks: List[List[Dict[str, Any]]] = []
        current_chunk: List[Dict[str, Any]] = []
        current_line_words: List[str] = []
        current_lines = 1

        for w_item in words:
            w_text = w_item["word"].upper()

            # Misura larghezza
            test_line = " ".join(current_line_words + [w_text])
            if font is not None:
                line_len = font.getlength(test_line)
            else:
                line_len = len(test_line) * (font_size * 0.6)

            need_new_line = (line_len > max_width_px) or (len(current_line_words) >= SUBTITLE_MAX_WORDS_PER_LINE)

            if need_new_line and current_line_words:
                if current_lines < SUBTITLE_MAX_LINES:
                    current_lines += 1
                    current_line_words = [w_text]
                    current_chunk.append(w_item)
                else:
                    # Raggiunto il limite dello schermo (2 righe piene): chiudi evento visivo
                    if current_chunk:
                        chunks.append(current_chunk)
                    current_chunk = [w_item]
                    current_line_words = [w_text]
                    current_lines = 1
            else:
                current_line_words.append(w_text)
                current_chunk.append(w_item)

        if current_chunk:
            chunks.append(current_chunk)

        return chunks

    def generate_ass(
        self,
        word_events: List[Dict[str, Any]],
        output_ass_path: str,
        context_title: str,
        part_num: int = 1,
        total_parts: int = 1,
        total_video_duration: Optional[float] = None,
        style_config: Optional[dict] = None
    ) -> str:
        """
        Genera il file .ass completo per il montaggio finale:
        - Layer 1: Intro Title Banner (0.0s -> 1.5s, center)
        - Layer 0: Karaoke dynamic subtitles (lead-in +0.500s, Alignment 2, Y=440)
        - Layer 1: Outro CTA Banner (T_video - 1.0s -> T_video, center)
        """
        cfg = style_config or {}
        font_name = cfg.get("font_name", DEFAULT_FONT_NAME)
        font_size = int(cfg.get("font_size", DEFAULT_FONT_SIZE))
        primary_hex = cfg.get("primary_color_hex", DEFAULT_TEXT_COLOR)
        highlight_hex = cfg.get("highlight_color_hex", DEFAULT_HIGHLIGHT_COLOR)
        outline_hex = cfg.get("outline_color_hex", DEFAULT_OUTLINE_COLOR)
        outline_width = int(cfg.get("outline_width", DEFAULT_OUTLINE_WIDTH))
        shadow_radius = int(cfg.get("shadow_radius", DEFAULT_SHADOW_RADIUS))
        margin_v = int(cfg.get("margin_v", DEFAULT_MARGIN_V))

        primary_ass = hex_to_ass_color(primary_hex)
        highlight_ass = hex_to_ass_color(highlight_hex)
        outline_ass = hex_to_ass_color(outline_hex)
        shadow_ass = "&H80000000"

        # Calcolo durata se non passata esplicitamente
        if not total_video_duration and word_events:
            last_end = max(w["end"] for w in word_events)
            total_video_duration = last_end + PADDING_INTRO_SEC + PADDING_OUTRO_SEC
        elif not total_video_duration:
            total_video_duration = 38.0

        cta_start_sec = max(0.0, total_video_duration - OUTRO_CTA_LEAD_TIME_SEC)
        intro_title_text = f"{context_title.replace('_', ' ')} part.{part_num}"
        outro_cta_text = f"Subscribe for part.{part_num + 1}" if part_num < total_parts else "Subscribe for more!"

        ass_lines = [
            "[Script Info]",
            "Title: AI Short Generator Dynamic Multi-Layer Karaoke",
            "ScriptType: v4.00+",
            f"PlayResX: {CANVAS_WIDTH}",
            f"PlayResY: {CANVAS_HEIGHT}",
            "",
            "[V4+ Styles]",
            "Format: Name, Fontname, Fontsize, PrimaryColour, SecondaryColour, OutlineColour, BackColour, Bold, Italic, Underline, StrikeOut, ScaleX, ScaleY, Spacing, Angle, BorderStyle, Outline, Shadow, Alignment, MarginL, MarginR, MarginV, Encoding",
            f"Style: KaraokeWord,{font_name},{font_size},{primary_ass},{highlight_ass},{outline_ass},{shadow_ass},-1,0,0,0,100,100,1,0,1,{outline_width},{shadow_radius},2,60,60,{margin_v},1",
            f"Style: TitleBanner,{font_name},64,&H00FFFFFF,{highlight_ass},{outline_ass},{shadow_ass},-1,0,0,0,100,100,2,0,1,6,4,5,60,60,0,1",
            f"Style: OutroBanner,{font_name},66,{primary_ass},{highlight_ass},{outline_ass},{shadow_ass},-1,0,0,0,100,100,2,0,1,7,4,5,60,60,0,1",
            "",
            "[Events]",
            "Format: Layer, Start, End, Style, Name, MarginL, MarginR, MarginV, Effect, Text",
            f"Dialogue: 1,{format_ass_time(INTRO_BANNER_START_SEC)},{format_ass_time(INTRO_BANNER_END_SEC)},TitleBanner,,0,0,0,,{{\\fade(150,200)}}{intro_title_text}"
        ]

        # Raggruppamento geometrico dei sottotitoli parlati
        chunks = self.wrap_words_geometrically(word_events, font_name, font_size)

        for chunk in chunks:
            chunk_start = chunk[0]["start"] + PADDING_INTRO_SEC
            chunk_end = chunk[-1]["end"] + PADDING_INTRO_SEC

            # Testo uniforme e naturale, nessuna parola evidenziata
            words_text = [w["word"].upper() for w in chunk]
            formatted_text = ""
            for i, p in enumerate(words_text):
                if i > 0 and i % SUBTITLE_MAX_WORDS_PER_LINE == 0:
                    formatted_text += "\\N" + p
                else:
                    formatted_text += (" " if formatted_text and not formatted_text.endswith("\\N") else "") + p

            ass_lines.append(
                f"Dialogue: 0,{format_ass_time(chunk_start)},{format_ass_time(chunk_end)},KaraokeWord,,0,0,0,,{formatted_text}"
            )

        # Outro CTA Banner (T_video - 1.0s -> T_video)
        ass_lines.append(
            f"Dialogue: 1,{format_ass_time(cta_start_sec)},{format_ass_time(total_video_duration)},OutroBanner,,0,0,0,,{{\\fade(150,0)}}{outro_cta_text}"
        )

        Path(output_ass_path).parent.mkdir(parents=True, exist_ok=True)
        content = "\n".join(ass_lines) + "\n"
        with open(output_ass_path, "w", encoding="utf-8") as f:
            f.write(content)

        return output_ass_path
