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
    OUTRO_PAUSE_SEC, INTRO_BANNER_START_SEC, INTRO_BANNER_END_SEC, OUTRO_CTA_LEAD_TIME_SEC,
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
        style_config: Optional[dict] = None,
        narration_duration: Optional[float] = None,
        outro_cta_text: Optional[str] = None
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
        is_all_caps = bool(cfg.get("is_all_caps", True))
        anim_style = str(cfg.get("animation_style", "WORD_POP")).upper()
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

        # Intro & Outro Banner styles (indipendenti dai sottotitoli)
        intro_cfg = cfg.get("intro_style", {})
        intro_enabled = bool(intro_cfg.get("enabled", True))
        intro_font = intro_cfg.get("font_name", font_name)
        intro_size = int(intro_cfg.get("font_size", 64))
        intro_is_all_caps = bool(intro_cfg.get("is_all_caps", False))
        intro_primary_ass = hex_to_ass_color(intro_cfg.get("primary_color_hex", "#FFFFFF"))
        intro_outline_ass = hex_to_ass_color(intro_cfg.get("outline_color_hex", outline_hex))
        intro_out_w = int(intro_cfg.get("outline_width", 6))
        intro_shadow_r = int(intro_cfg.get("shadow_radius", 4))
        intro_box_enabled = bool(intro_cfg.get("box_enabled", False))
        intro_border_style = 3 if intro_box_enabled else 1
        intro_box_color = hex_to_ass_color(intro_cfg.get("box_color_hex", "#14171E"), alpha="40") if intro_box_enabled else shadow_ass
        intro_margin_v = int(intro_cfg.get("margin_v", 960))
        if intro_margin_v <= 0:
            intro_margin_v = 960

        outro_cfg = cfg.get("outro_style", {})
        outro_enabled = bool(outro_cfg.get("enabled", True))
        outro_font = outro_cfg.get("font_name", font_name)
        outro_size = int(outro_cfg.get("font_size", 66))
        outro_is_all_caps = bool(outro_cfg.get("is_all_caps", False))
        outro_primary_ass = hex_to_ass_color(outro_cfg.get("primary_color_hex", primary_hex))
        outro_outline_ass = hex_to_ass_color(outro_cfg.get("outline_color_hex", outline_hex))
        outro_out_w = int(outro_cfg.get("outline_width", 7))
        outro_shadow_r = int(outro_cfg.get("shadow_radius", 4))
        outro_box_enabled = bool(outro_cfg.get("box_enabled", False))
        outro_border_style = 3 if outro_box_enabled else 1
        outro_box_color = hex_to_ass_color(outro_cfg.get("box_color_hex", "#14171E"), alpha="40") if outro_box_enabled else shadow_ass
        outro_margin_v = int(outro_cfg.get("margin_v", 960))
        if outro_margin_v <= 0:
            outro_margin_v = 960

        # Calcolo durata se non passata esplicitamente
        if not total_video_duration and word_events:
            last_end = max(w["end"] for w in word_events)
            total_video_duration = last_end + PADDING_INTRO_SEC + PADDING_OUTRO_SEC
        elif not total_video_duration:
            total_video_duration = 38.0

        if narration_duration is not None:
            cta_start_sec = PADDING_INTRO_SEC + narration_duration + OUTRO_PAUSE_SEC
        elif word_events:
            last_end = max(w["end"] for w in word_events)
            cta_start_sec = PADDING_INTRO_SEC + last_end + OUTRO_PAUSE_SEC
        else:
            cta_start_sec = max(0.0, total_video_duration - OUTRO_CTA_LEAD_TIME_SEC)

        intro_title_text = intro_cfg.get("text") or f"{context_title.replace('_', ' ')} part.{part_num}"
        if intro_is_all_caps:
            intro_title_text = intro_title_text.upper()
        # Converte newlines in \N per ASS
        intro_title_text = intro_title_text.replace("\r\n", "\\N").replace("\n", "\\N")

        if outro_cta_text is None:
            outro_cta_text = outro_cfg.get("text") or (f"Follow for part.{part_num + 1}" if part_num < total_parts else "Follow for more!")
        elif outro_cfg.get("text"):
            outro_cta_text = outro_cfg["text"]
        if outro_is_all_caps:
            outro_cta_text = outro_cta_text.upper()
        # Converte newlines in \N per ASS
        outro_cta_text = outro_cta_text.replace("\r\n", "\\N").replace("\n", "\\N")

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
            f"Style: TitleBanner,{intro_font},{intro_size},{intro_primary_ass},{highlight_ass},{intro_outline_ass},{intro_box_color},-1,0,0,0,100,100,2,0,{intro_border_style},{intro_out_w},{intro_shadow_r},2,60,60,{intro_margin_v},1",
            f"Style: OutroBanner,{outro_font},{outro_size},{outro_primary_ass},{highlight_ass},{outro_outline_ass},{outro_box_color},-1,0,0,0,100,100,2,0,{outro_border_style},{outro_out_w},{outro_shadow_r},2,60,60,{outro_margin_v},1",
            "",
            "[Events]",
            "Format: Layer, Start, End, Style, Name, MarginL, MarginR, MarginV, Effect, Text",
        ]

        # Intro Title Banner (0.0s -> 1.5s, centro schermo)
        if intro_enabled:
            ass_lines.append(
                f"Dialogue: 1,{format_ass_time(INTRO_BANNER_START_SEC)},{format_ass_time(INTRO_BANNER_END_SEC)},TitleBanner,,0,0,0,,{{\\fade(150,200)}}{intro_title_text}"
            )

        # Rendering sottotitoli in base allo stile di animazione dinamica selezionato
        if anim_style == "WORD_POP":
            # Word Pop: Parola per parola sincronizzata con effetto pop scaling
            for i, w in enumerate(word_events):
                w_start = w["start"] + PADDING_INTRO_SEC
                if i + 1 < len(word_events):
                    next_start = word_events[i + 1]["start"] + PADDING_INTRO_SEC
                    w_end = min(next_start, max(w["end"] + PADDING_INTRO_SEC, next_start - 0.04))
                else:
                    w_end = w["end"] + PADDING_INTRO_SEC
                w_text = w["word"].upper() if is_all_caps else w["word"]
                pop_text = f"{{\\fscx115\\fscy115\\t(0,70,\\fscx100\\fscy100)}}{w_text}"
                ass_lines.append(
                    f"Dialogue: 0,{format_ass_time(w_start)},{format_ass_time(w_end)},KaraokeWord,,0,0,0,,{pop_text}"
                )
        elif anim_style == "BOUNCE":
            # Bounce: Due parole a rimbalzo (chunk da 2 parole sincronizzate)
            pairs = [word_events[i:i + 2] for i in range(0, len(word_events), 2)]
            for p_idx, pair in enumerate(pairs):
                p_start = pair[0]["start"] + PADDING_INTRO_SEC
                if p_idx + 1 < len(pairs):
                    next_p_start = pairs[p_idx + 1][0]["start"] + PADDING_INTRO_SEC
                    p_end = min(next_p_start, max(pair[-1]["end"] + PADDING_INTRO_SEC, next_p_start - 0.05))
                else:
                    p_end = pair[-1]["end"] + PADDING_INTRO_SEC
                pair_words = [w["word"].upper() if is_all_caps else w["word"] for w in pair]
                pair_text = " ".join(pair_words)
                bounce_text = f"{{\\fscx112\\fscy112\\t(0,80,\\fscx100\\fscy100)}}{pair_text}"
                ass_lines.append(
                    f"Dialogue: 0,{format_ass_time(p_start)},{format_ass_time(p_end)},KaraokeWord,,0,0,0,,{bounce_text}"
                )
        elif anim_style in ("KARAOKE", "KARAOKE_LINEAR"):
            # Karaoke Lineare: Frase su schermo con evidenziazione parola per parola nel colore highlight
            chunks = self.wrap_words_geometrically(word_events, font_name, font_size)
            for chunk in chunks:
                for active_idx, active_word in enumerate(chunk):
                    w_start = active_word["start"] + PADDING_INTRO_SEC
                    if active_idx + 1 < len(chunk):
                        next_w_start = chunk[active_idx + 1]["start"] + PADDING_INTRO_SEC
                        w_end = min(next_w_start, max(active_word["end"] + PADDING_INTRO_SEC, next_w_start - 0.04))
                    else:
                        w_end = active_word["end"] + PADDING_INTRO_SEC

                    line_parts = []
                    for idx, w in enumerate(chunk):
                        w_str = w["word"].upper() if is_all_caps else w["word"]
                        if idx == active_idx:
                            line_parts.append(f"{{\\c{highlight_ass}}}{w_str}{{\\c{primary_ass}}}")
                        else:
                            line_parts.append(w_str)

                    formatted_text = ""
                    for idx, p in enumerate(line_parts):
                        if idx > 0 and idx % SUBTITLE_MAX_WORDS_PER_LINE == 0:
                            formatted_text += "\\N" + p
                        else:
                            formatted_text += (" " if formatted_text and not formatted_text.endswith("\\N") else "") + p

                    ass_lines.append(
                        f"Dialogue: 0,{format_ass_time(w_start)},{format_ass_time(w_end)},KaraokeWord,,0,0,0,,{formatted_text}"
                    )
        else:
            # Statico: Raggruppamento geometrico classico
            chunks = self.wrap_words_geometrically(word_events, font_name, font_size)
            for chunk in chunks:
                chunk_start = chunk[0]["start"] + PADDING_INTRO_SEC
                chunk_end = chunk[-1]["end"] + PADDING_INTRO_SEC
                words_text = [w["word"].upper() if is_all_caps else w["word"] for w in chunk]
                formatted_text = ""
                for i, p in enumerate(words_text):
                    if i > 0 and i % SUBTITLE_MAX_WORDS_PER_LINE == 0:
                        formatted_text += "\\N" + p
                    else:
                        formatted_text += (" " if formatted_text and not formatted_text.endswith("\\N") else "") + p
                ass_lines.append(
                    f"Dialogue: 0,{format_ass_time(chunk_start)},{format_ass_time(chunk_end)},KaraokeWord,,0,0,0,,{formatted_text}"
                )

        # Outro CTA Banner (entra a 1.0s dalla fine narrazione sincronizzato all'audio letto dal TTS)
        if outro_enabled:
            ass_lines.append(
                f"Dialogue: 1,{format_ass_time(cta_start_sec)},{format_ass_time(total_video_duration)},OutroBanner,,0,0,0,,{{\\fade(150,0)}}{outro_cta_text}"
            )

        Path(output_ass_path).parent.mkdir(parents=True, exist_ok=True)
        content = "\n".join(ass_lines) + "\n"
        with open(output_ass_path, "w", encoding="utf-8") as f:
            f.write(content)

        return output_ass_path
