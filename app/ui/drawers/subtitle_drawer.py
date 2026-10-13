"""AI Short Generator 1.0 - Subtitle Drawer (Designer Sottotitoli & Safe-Zone Studio)"""

import os
import shutil
import subprocess
import copy
from typing import Optional, Dict, Any, List
from pathlib import Path

from PySide6.QtWidgets import (
    QDialog, QVBoxLayout, QHBoxLayout, QLabel, QPushButton, QFrame,
    QScrollArea, QWidget, QSlider, QCheckBox, QComboBox, QRadioButton,
    QButtonGroup, QInputDialog, QMessageBox, QFileDialog, QColorDialog,
    QTabWidget, QLineEdit
)
from PySide6.QtCore import Qt, Signal, QTimer
from PySide6.QtGui import (
    QPixmap, QPainter, QColor, QFont, QPen, QBrush, QFontDatabase,
    QPainterPath, QLinearGradient, QFontMetrics
)

from app.config import (
    DEFAULT_FONT_NAME, DEFAULT_FONT_SIZE, DEFAULT_TEXT_COLOR,
    DEFAULT_HIGHLIGHT_COLOR, DEFAULT_OUTLINE_COLOR, DEFAULT_OUTLINE_WIDTH,
    DEFAULT_SHADOW_RADIUS, DEFAULT_MARGIN_V, SUBTITLE_SAFE_WIDTH_PX,
    CANVAS_WIDTH, CANVAS_HEIGHT, FONTS_DIR, VIDEO_POOL_DIR, CACHE_DIR
)
from app.core.preset_manager import PresetManager
from app.utils.ffmpeg_installer import find_system_ffmpeg
from app.utils.logger import log


class SubtitleCanvasWidget(QWidget):
    """
    Monitor 9:16 (270x480) con ritaglio centrale WYSIWYG, rendering frame reale,
    animazione dinamica dei sottotitoli e anteprima dei titoli di testa e di coda.
    """

    def __init__(self, parent: Optional[QWidget] = None):
        super().__init__(parent)
        self.setFixedSize(270, 480)
        self.background_pixmap: Optional[QPixmap] = None

        # Modalità anteprima: "SUBTITLES", "INTRO", "OUTRO"
        self.view_mode: str = "SUBTITLES"
        self.scrub_sec: float = 2.5
        self.clip_duration_sec: float = 38.0
        self.clip_words: List[str] = []

        # Stile Sottotitoli Standard
        self.font_family = DEFAULT_FONT_NAME
        self.font_size = DEFAULT_FONT_SIZE
        self.is_all_caps = True
        self.color_base = DEFAULT_TEXT_COLOR
        self.color_highlight = DEFAULT_HIGHLIGHT_COLOR
        self.color_outline = DEFAULT_OUTLINE_COLOR
        self.outline_width = DEFAULT_OUTLINE_WIDTH
        self.shadow_radius = DEFAULT_SHADOW_RADIUS
        self.margin_v = DEFAULT_MARGIN_V
        self.animation_style = "WORD_POP"

        # Stile Titolo di Testa (Intro)
        self.intro_enabled = True
        self.intro_text = "Space_BlackHoles part.1"
        self.intro_font_family = DEFAULT_FONT_NAME
        self.intro_font_size = 64
        self.intro_is_all_caps = True
        self.intro_color = "#FFFFFF"
        self.intro_outline_color = "#181A20"
        self.intro_outline_width = 6
        self.intro_shadow_radius = 4
        self.intro_box_enabled = True
        self.intro_box_color = "#14171E"
        self.intro_box_opacity = 85
        self.intro_margin_v = 0 # 0 = centro schermo

        # Stile Titolo di Coda (Outro CTA)
        self.outro_enabled = True
        self.outro_text = "Follow for part.2"
        self.outro_font_family = DEFAULT_FONT_NAME
        self.outro_font_size = 66
        self.outro_is_all_caps = False
        self.outro_color = "#DCE0EA"
        self.outro_outline_color = "#181A20"
        self.outro_outline_width = 7
        self.outro_shadow_radius = 4
        self.outro_box_enabled = True
        self.outro_box_color = "#14171E"
        self.outro_box_opacity = 85
        self.outro_margin_v = 0 # 0 = centro schermo

        # Overlays
        self.show_safe_zones = True

    def set_background_image(self, image_path: str):
        """Carica l'immagine ed esegue il ritaglio 9:16 centrale (WYSIWYG) a 270x480."""
        if image_path and os.path.exists(image_path):
            pix = QPixmap(image_path)
            if not pix.isNull():
                scaled = pix.scaled(270, 480, Qt.KeepAspectRatioByExpanding, Qt.SmoothTransformation)
                crop_x = max(0, (scaled.width() - 270) // 2)
                crop_y = max(0, (scaled.height() - 480) // 2)
                self.background_pixmap = scaled.copy(crop_x, crop_y, 270, 480)
            else:
                self.background_pixmap = None
        else:
            self.background_pixmap = None
        self.update()

    def set_view_mode(self, mode: str):
        self.view_mode = mode
        self.update()

    def set_scrub_time(self, sec: float):
        self.scrub_sec = max(0.0, sec)
        self.update()

    def set_clip_text(self, text_or_words):
        if isinstance(text_or_words, str):
            self.clip_words = text_or_words.split()
        elif isinstance(text_or_words, list):
            self.clip_words = text_or_words
        self.update()

    def update_subtitle_style(self, style_dict: dict):
        self.font_family = style_dict.get("font_name", self.font_family)
        self.font_size = int(style_dict.get("font_size", self.font_size))
        self.is_all_caps = bool(style_dict.get("is_all_caps", self.is_all_caps))
        self.color_base = style_dict.get("primary_color_hex", self.color_base)
        self.color_highlight = style_dict.get("highlight_color_hex", self.color_highlight)
        self.color_outline = style_dict.get("outline_color_hex", self.color_outline)
        self.outline_width = int(style_dict.get("outline_width", self.outline_width))
        self.shadow_radius = int(style_dict.get("shadow_radius", self.shadow_radius))
        self.margin_v = int(style_dict.get("margin_v", self.margin_v))
        self.animation_style = style_dict.get("animation_style", self.animation_style)
        self.update()

    def update_intro_style(self, intro_dict: dict):
        self.intro_enabled = bool(intro_dict.get("enabled", self.intro_enabled))
        self.intro_text = intro_dict.get("text", self.intro_text)
        self.intro_font_family = intro_dict.get("font_name", self.intro_font_family)
        self.intro_font_size = int(intro_dict.get("font_size", self.intro_font_size))
        self.intro_is_all_caps = bool(intro_dict.get("is_all_caps", self.intro_is_all_caps))
        self.intro_color = intro_dict.get("primary_color_hex", self.intro_color)
        self.intro_outline_color = intro_dict.get("outline_color_hex", self.intro_outline_color)
        self.intro_outline_width = int(intro_dict.get("outline_width", self.intro_outline_width))
        self.intro_shadow_radius = int(intro_dict.get("shadow_radius", self.intro_shadow_radius))
        self.intro_box_enabled = bool(intro_dict.get("box_enabled", self.intro_box_enabled))
        self.intro_box_color = intro_dict.get("box_color_hex", self.intro_box_color)
        self.intro_box_opacity = int(intro_dict.get("box_opacity", self.intro_box_opacity))
        self.intro_margin_v = int(intro_dict.get("margin_v", self.intro_margin_v))
        self.update()

    def update_outro_style(self, outro_dict: dict):
        self.outro_enabled = bool(outro_dict.get("enabled", self.outro_enabled))
        self.outro_text = outro_dict.get("text", self.outro_text)
        self.outro_font_family = outro_dict.get("font_name", self.outro_font_family)
        self.outro_font_size = int(outro_dict.get("font_size", self.outro_font_size))
        self.outro_is_all_caps = bool(outro_dict.get("is_all_caps", self.outro_is_all_caps))
        self.outro_color = outro_dict.get("primary_color_hex", self.outro_color)
        self.outro_outline_color = outro_dict.get("outline_color_hex", self.outro_outline_color)
        self.outro_outline_width = int(outro_dict.get("outline_width", self.outro_outline_width))
        self.outro_shadow_radius = int(outro_dict.get("shadow_radius", self.outro_shadow_radius))
        self.outro_box_enabled = bool(outro_dict.get("box_enabled", self.outro_box_enabled))
        self.outro_box_color = outro_dict.get("box_color_hex", self.outro_box_color)
        self.outro_box_opacity = int(outro_dict.get("box_opacity", self.outro_box_opacity))
        self.outro_margin_v = int(outro_dict.get("margin_v", self.outro_margin_v))
        self.update()

    def paintEvent(self, event):
        painter = QPainter(self)
        painter.setRenderHint(QPainter.Antialiasing)
        painter.setRenderHint(QPainter.TextAntialiasing)

        # 1. Background image (con ritaglio centrale WYSIWYG) o mockup template 9:16
        if self.background_pixmap:
            painter.drawPixmap(0, 0, self.background_pixmap)
        else:
            grad = QLinearGradient(0, 0, 0, 480)
            grad.setColorAt(0.0, QColor("#1D212A"))
            grad.setColorAt(0.5, QColor("#13161C"))
            grad.setColorAt(1.0, QColor("#0D0E12"))
            painter.fillRect(0, 0, 270, 480, grad)

            painter.setPen(QColor(42, 50, 69, 120))
            painter.drawRect(0, 0, 269, 479)
            painter.drawLine(90, 0, 90, 480)
            painter.drawLine(180, 0, 180, 480)
            painter.drawLine(0, 160, 270, 160)
            painter.drawLine(0, 320, 270, 320)

            painter.setPen(QColor("#6B82A6"))
            painter.setFont(QFont("Segoe UI", 9, QFont.Bold))
            painter.drawText(0, 205, 270, 25, Qt.AlignCenter, "🎬 TEMPLATE VIDEO 9:16")
            painter.setFont(QFont("Segoe UI", 8))
            painter.setPen(QColor("#555E75"))
            painter.drawText(0, 230, 270, 20, Qt.AlignCenter, "[ Ritaglio Centrale WYSIWYG ]")

        # 2. Safe-Zone Overlays (TikTok, Reels, Shorts)
        if self.show_safe_zones:
            top_h = int(140 * (480 / 1920.0))
            painter.fillRect(0, 0, 270, top_h, QColor(107, 130, 166, 60))
            painter.setPen(QPen(QColor(107, 130, 166, 180), 1, Qt.DashLine))
            painter.drawLine(0, top_h, 270, top_h)
            painter.setFont(QFont("Segoe UI", 8, QFont.Bold))
            painter.setPen(QColor(160, 185, 220, 230))
            painter.drawText(8, top_h - 10, "TOP SAFE-ZONE (140px)")

            bot_h = int(360 * (480 / 1920.0))
            bot_y = 480 - bot_h
            painter.fillRect(0, bot_y, 270, bot_h, QColor(170, 115, 115, 60))
            painter.setPen(QPen(QColor(170, 115, 115, 200), 1, Qt.DashLine))
            painter.drawLine(0, bot_y, 270, bot_y)
            painter.setFont(QFont("Segoe UI", 8, QFont.Bold))
            painter.setPen(QColor(240, 170, 170, 230))
            painter.drawText(8, bot_y + 22, "BOTTOM SOCIAL UI (360px)")

            side_w = 26
            painter.fillRect(270 - side_w, top_h, side_w, bot_y - top_h, QColor(170, 115, 115, 35))
            painter.drawLine(270 - side_w, top_h, 270 - side_w, bot_y)

        # 3. Rendering in base alla modalità attiva (Anteprima Titoli o Sottotitoli)
        if self.view_mode == "INTRO":
            self._render_intro_banner(painter)
        elif self.view_mode == "OUTRO":
            self._render_outro_banner(painter)
        else:
            self._render_subtitles_animation(painter)

    def _render_intro_banner(self, painter: QPainter):
        """Render esatto del fotogramma del Titolo di Testa."""
        banner_text = self.intro_text or "TITOLO INTRO"
        if self.intro_is_all_caps:
            banner_text = banner_text.upper()

        scale_ratio = 480.0 / 1920.0
        scaled_size = max(11, int(self.intro_font_size * scale_ratio * 1.35))
        font = QFont(self.intro_font_family, scaled_size, QFont.Bold)
        painter.setFont(font)
        fm = painter.fontMetrics()
        t_w = fm.horizontalAdvance(banner_text)
        t_h = fm.height()

        y_pos = int((1920 - self.intro_margin_v) * scale_ratio) if self.intro_margin_v > 0 else 220
        y_pos = max(60, min(420, y_pos))

        # Box Sfondo Banner (se abilitato)
        if self.intro_box_enabled:
            pad_x = 16
            pad_y = 8
            b_w = min(254, t_w + pad_x * 2)
            b_h = t_h + pad_y * 2
            b_x = (270 - b_w) // 2
            b_y = y_pos - t_h // 2 - pad_y

            box_col = QColor(self.intro_box_color)
            box_col.setAlpha(int(255 * (self.intro_box_opacity / 100.0)))
            painter.setBrush(QBrush(box_col))
            painter.setPen(QPen(QColor(self.intro_outline_color), 1.5))
            painter.drawRoundedRect(b_x, b_y, b_w, b_h, 6, 6)

        # Disegno Testo con Contorno e Ombra
        x_pos = max(10, (270 - t_w) // 2)
        baseline_y = y_pos + t_h // 4

        path = QPainterPath()
        path.addText(x_pos, baseline_y, font, banner_text)

        if self.intro_shadow_radius > 0:
            shadow_path = QPainterPath()
            s_off = max(1, int(self.intro_shadow_radius * 0.45))
            shadow_path.addText(x_pos + s_off, baseline_y + s_off, font, banner_text)
            painter.fillPath(shadow_path, QBrush(QColor(0, 0, 0, 180)))

        if self.intro_outline_width > 0:
            pen = QPen(QColor(self.intro_outline_color), max(1.5, self.intro_outline_width * 0.45))
            pen.setJoinStyle(Qt.RoundJoin)
            painter.strokePath(path, pen)

        painter.fillPath(path, QBrush(QColor(self.intro_color)))

        # Badge modalità
        self._draw_mode_badge(painter, "🎬 TITOLO DI TESTA (0.0s - 1.5s)", "#6B82A6")

    def _render_outro_banner(self, painter: QPainter):
        """Render esatto del fotogramma del Titolo di Coda."""
        banner_text = self.outro_text or "FOLLOW FOR MORE!"
        if self.outro_is_all_caps:
            banner_text = banner_text.upper()

        scale_ratio = 480.0 / 1920.0
        scaled_size = max(11, int(self.outro_font_size * scale_ratio * 1.35))
        font = QFont(self.outro_font_family, scaled_size, QFont.Bold)
        painter.setFont(font)
        fm = painter.fontMetrics()
        t_w = fm.horizontalAdvance(banner_text)
        t_h = fm.height()

        y_pos = int((1920 - self.outro_margin_v) * scale_ratio) if self.outro_margin_v > 0 else 235
        y_pos = max(60, min(420, y_pos))

        # Box Sfondo Banner (se abilitato)
        if self.outro_box_enabled:
            pad_x = 16
            pad_y = 8
            b_w = min(254, t_w + pad_x * 2)
            b_h = t_h + pad_y * 2
            b_x = (270 - b_w) // 2
            b_y = y_pos - t_h // 2 - pad_y

            box_col = QColor(self.outro_box_color)
            box_col.setAlpha(int(255 * (self.outro_box_opacity / 100.0)))
            painter.setBrush(QBrush(box_col))
            painter.setPen(QPen(QColor(self.outro_outline_color), 1.5))
            painter.drawRoundedRect(b_x, b_y, b_w, b_h, 6, 6)

        x_pos = max(10, (270 - t_w) // 2)
        baseline_y = y_pos + t_h // 4

        path = QPainterPath()
        path.addText(x_pos, baseline_y, font, banner_text)

        if self.outro_shadow_radius > 0:
            shadow_path = QPainterPath()
            s_off = max(1, int(self.outro_shadow_radius * 0.45))
            shadow_path.addText(x_pos + s_off, baseline_y + s_off, font, banner_text)
            painter.fillPath(shadow_path, QBrush(QColor(0, 0, 0, 180)))

        if self.outro_outline_width > 0:
            pen = QPen(QColor(self.outro_outline_color), max(1.5, self.outro_outline_width * 0.45))
            pen.setJoinStyle(Qt.RoundJoin)
            painter.strokePath(path, pen)

        painter.fillPath(path, QBrush(QColor(self.outro_color)))

        # Badge modalità
        self._draw_mode_badge(painter, "🏁 TITOLO DI CODA (OUTRO CTA)", "#BFA175")

    def _render_subtitles_animation(self, painter: QPainter):
        """Render dinamico dei sottotitoli collegato allo stile di animazione e allo scrub."""
        scale_ratio = 480.0 / 1920.0
        scaled_font_size = max(10, int(self.font_size * scale_ratio * 1.35))
        sub_font = QFont(self.font_family, scaled_font_size, QFont.Black if "black" in self.font_family.lower() else QFont.Bold)
        painter.setFont(sub_font)

        y_pos = int((1920 - self.margin_v) * scale_ratio)
        y_pos = max(45, min(450, y_pos))

        words = self.clip_words if self.clip_words else ["BLACK", "HOLES", "ARE", "MOST", "MYSTERIOUS", "OBJECTS", "IN", "THE", "COSMOS"]
        if not self.is_all_caps:
            words = [w.capitalize() for w in words]
        else:
            words = [w.upper() for w in words]

        anim = (self.animation_style or "WORD_POP").upper()

        if anim == "WORD_POP":
            # Word Pop: 1 sola parola alla volta che fa "pop" sincronizzata sullo scrub
            active_idx = int(self.scrub_sec * 2.5) % max(1, len(words))
            pop_word = words[active_idx]

            pop_font = QFont(self.font_family, int(scaled_font_size * 1.15), QFont.Black if "black" in self.font_family.lower() else QFont.Bold)
            painter.setFont(pop_font)
            fm = painter.fontMetrics()
            w_w = fm.horizontalAdvance(pop_word)
            x_pos = (270 - w_w) // 2

            self._draw_styled_text(painter, pop_font, pop_word, x_pos, y_pos, self.color_highlight)
            self._draw_mode_badge(painter, f"💥 WORD POP: Parola #{active_idx + 1}", "#7E95BC")

        elif anim == "BOUNCE":
            # Bounce: Esattamente 2 parole a rimbalzo (Bounce Chunk)
            pair_idx = (int(self.scrub_sec * 1.25) * 2) % max(1, len(words))
            pair_slice = words[pair_idx:pair_idx + 2]
            pair_text = " ".join(pair_slice)

            bounce_font = QFont(self.font_family, int(scaled_font_size * 1.08), QFont.Black if "black" in self.font_family.lower() else QFont.Bold)
            painter.setFont(bounce_font)
            fm = painter.fontMetrics()
            w_w = fm.horizontalAdvance(pair_text)
            x_pos = (270 - w_w) // 2

            self._draw_styled_text(painter, bounce_font, pair_text, x_pos, y_pos, self.color_base)
            self._draw_mode_badge(painter, "🏀 BOUNCE: 2 Parole a Rimbalzo", "#729B84")

        elif anim in ("KARAOKE", "KARAOKE_LINEAR"):
            # Karaoke Lineare: Frase intera a schermo con evidenziazione parola per parola
            chunk_start = (int(self.scrub_sec / 3.0) * 5) % max(1, len(words))
            chunk = words[chunk_start:chunk_start + 5]
            if not chunk:
                chunk = words[:5]
            active_in_chunk = int(self.scrub_sec * 2.0) % len(chunk)

            # Suddivisione in 2 righe max 3 parole per riga
            line1_words = chunk[:3]
            line2_words = chunk[3:]

            fm = painter.fontMetrics()
            b1_y = max(35, y_pos - int(scaled_font_size * 1.1))
            b2_y = y_pos

            # Disegno Linea 1 parola per parola
            self._draw_karaoke_line(painter, sub_font, line1_words, 0, active_in_chunk, b1_y)
            # Disegno Linea 2 parola per parola
            if line2_words:
                self._draw_karaoke_line(painter, sub_font, line2_words, len(line1_words), active_in_chunk, b2_y)

            self._draw_mode_badge(painter, "🎤 KARAOKE LINEARE: Evidenziazione attiva", "#C4A36B")

        else:
            # Statico: due righe standard
            w1 = " ".join(words[:3])
            w2 = " ".join(words[3:6]) if len(words) > 3 else ""

            fm = painter.fontMetrics()
            b1_y = max(35, y_pos - int(scaled_font_size * 1.1))
            b2_y = y_pos

            x1 = (270 - fm.horizontalAdvance(w1)) // 2
            self._draw_styled_text(painter, sub_font, w1, x1, b1_y, self.color_base)
            if w2:
                x2 = (270 - fm.horizontalAdvance(w2)) // 2
                self._draw_styled_text(painter, sub_font, w2, x2, b2_y, self.color_base)

            self._draw_mode_badge(painter, "📄 STATICO: Due Righe", "#666E7F")

    def _draw_karaoke_line(self, painter: QPainter, font: QFont, line_words: List[str], global_offset: int, active_idx: int, y: int):
        fm = painter.fontMetrics()
        space_w = fm.horizontalAdvance(" ")
        total_w = sum(fm.horizontalAdvance(w) for w in line_words) + space_w * max(0, len(line_words) - 1)
        cur_x = (270 - total_w) // 2

        for i, word in enumerate(line_words):
            word_idx = global_offset + i
            is_active = (word_idx == active_idx)
            color = self.color_highlight if is_active else self.color_base
            w_w = fm.horizontalAdvance(word)

            self._draw_styled_text(painter, font, word, cur_x, y, color)
            cur_x += w_w + space_w

    def _draw_styled_text(self, painter: QPainter, font: QFont, text: str, x: int, y: int, color_hex: str):
        path = QPainterPath()
        path.addText(x, y, font, text)

        if self.shadow_radius > 0:
            shadow_path = QPainterPath()
            s_off = max(1, int(self.shadow_radius * 0.45))
            shadow_path.addText(x + s_off, y + s_off, font, text)
            painter.fillPath(shadow_path, QBrush(QColor(0, 0, 0, 180)))

        if self.outline_width > 0:
            pen = QPen(QColor(self.color_outline), max(1.5, self.outline_width * 0.45))
            pen.setJoinStyle(Qt.RoundJoin)
            painter.strokePath(path, pen)

        painter.fillPath(path, QBrush(QColor(color_hex)))

    def _draw_mode_badge(self, painter: QPainter, label: str, border_color: str):
        painter.setFont(QFont("Segoe UI", 8, QFont.Bold))
        fm = painter.fontMetrics()
        w = fm.horizontalAdvance(label) + 16
        h = 20
        x = (270 - w) // 2
        y = 12

        painter.setBrush(QBrush(QColor(20, 24, 32, 220)))
        painter.setPen(QPen(QColor(border_color), 1.2))
        painter.drawRoundedRect(x, y, w, h, 4, 4)

        painter.setPen(QColor("#DCE0EA"))
        painter.drawText(x, y, w, h, Qt.AlignCenter, label)


class SubtitleDrawer(QDialog):
    """
    Drawer 3: Subtitle Designer, Anteprima Visiva Live (9:16 WYSIWYG),
    Navigatore Clip con Editing Indipendente, Copia/Incolla Specifiche e Gestione Titoli.
    """

    settings_saved = Signal(dict)
    apply_to_all_requested = Signal(dict)

    def __init__(
        self,
        preset_manager: Optional[PresetManager] = None,
        current_settings: Optional[dict] = None,
        video_frame_path: Optional[str] = None,
        video_pool_mgr: Optional[Any] = None,
        script_data: Optional[dict] = None,
        timing_config: Optional[dict] = None,
        video_file_path: Optional[str] = None,
        parent: Optional[QWidget] = None
    ):
        super().__init__(parent)
        self.preset_manager = preset_manager or PresetManager()
        self.current_settings = copy.deepcopy(current_settings or {})
        self.video_pool_mgr = video_pool_mgr
        self.temp_frame_path = video_frame_path or ""
        self.script_data = script_data or {}
        self.timing_config = timing_config or {}
        self.video_file_path = video_file_path or ""

        # Appunti interni per funzione Copia/Incolla Specifiche
        self.copied_specs_clipboard: Optional[dict] = None

        self.setWindowTitle("DESIGNER SOTTOTITOLI & SAFE-ZONE STUDIO")
        self.resize(920, 760)
        self.setMinimumSize(880, 700)
        self.setObjectName("DrawerWindow")

        # Inizializzazione Clip della storia attiva
        self._init_clips_model()

        # Timer debounced per estrazione fotogramma dallo scrub
        self.frame_scrub_timer = QTimer(self)
        self.frame_scrub_timer.setSingleShot(True)
        self.frame_scrub_timer.timeout.connect(self._on_scrub_timer_timeout)

        self._init_ui()
        self._load_available_fonts()
        self._load_presets_combo()
        self._load_clip_data_to_ui(self.current_clip_idx)
        self._auto_detect_video_frame()

    def _init_clips_model(self):
        """Inizializza la lista delle clip generate dal testo attivo e la mappa delle impostazioni indipendenti."""
        custom_chunks = self.timing_config.get("custom_chunks") or self.script_data.get("custom_chunks") or []
        raw_text = self.script_data.get("raw_text") or self.script_data.get("full_text", "")
        title = self.script_data.get("context_title", "Short Story")

        if not custom_chunks and raw_text:
            custom_chunks = [raw_text]
        elif not custom_chunks:
            custom_chunks = ["Black holes are the most mysterious objects in the observable cosmos."]

        self.clips: List[Dict[str, Any]] = []
        for i, chunk in enumerate(custom_chunks):
            self.clips.append({
                "clip_idx": i,
                "part_num": i + 1,
                "text": chunk,
                "title": f"{title} part.{i + 1}"
            })

        self.current_clip_idx: int = 0

        # Mappa impostazioni indipendenti per ogni clip
        self.clip_styles: Dict[int, Dict[str, Any]] = {}

        # Carica eventuali stili per-clip salvati in precedenza
        saved_clip_map = self.current_settings.get("clip_settings", {})

        for i, clip in enumerate(self.clips):
            if i in saved_clip_map:
                self.clip_styles[i] = copy.deepcopy(saved_clip_map[i])
            elif str(i) in saved_clip_map:
                self.clip_styles[i] = copy.deepcopy(saved_clip_map[str(i)])
            else:
                # Default iniziale derivato dalle impostazioni attive correnti
                intro_title = clip["title"]
                custom_intros = self.timing_config.get("custom_intros", [])
                if isinstance(custom_intros, list) and i < len(custom_intros) and custom_intros[i]:
                    intro_title = custom_intros[i]

                is_final = (i == len(self.clips) - 1)
                outro_banner = "Follow for more!" if is_final else f"Follow for part.{i + 2}"
                custom_outros = self.timing_config.get("custom_outros", [])
                if isinstance(custom_outros, list) and i < len(custom_outros) and isinstance(custom_outros[i], dict):
                    outro_banner = custom_outros[i].get("banner") or outro_banner

                self.clip_styles[i] = {
                    "subtitle": {
                        "animation_style": self.current_settings.get("animation_style", "WORD_POP"),
                        "font_name": self.current_settings.get("font_name", DEFAULT_FONT_NAME),
                        "font_size": int(self.current_settings.get("font_size", DEFAULT_FONT_SIZE)),
                        "is_all_caps": bool(self.current_settings.get("is_all_caps", 1)),
                        "primary_color_hex": self.current_settings.get("primary_color_hex", DEFAULT_TEXT_COLOR),
                        "highlight_color_hex": self.current_settings.get("highlight_color_hex", DEFAULT_HIGHLIGHT_COLOR),
                        "outline_color_hex": self.current_settings.get("outline_color_hex", DEFAULT_OUTLINE_COLOR),
                        "outline_width": int(self.current_settings.get("outline_width", DEFAULT_OUTLINE_WIDTH)),
                        "shadow_radius": int(self.current_settings.get("shadow_radius", DEFAULT_SHADOW_RADIUS)),
                        "margin_v": int(self.current_settings.get("margin_v", DEFAULT_MARGIN_V))
                    },
                    "intro": {
                        "enabled": True,
                        "text": intro_title,
                        "font_name": self.current_settings.get("intro_font_name", DEFAULT_FONT_NAME),
                        "font_size": int(self.current_settings.get("intro_font_size", 64)),
                        "is_all_caps": True,
                        "primary_color_hex": self.current_settings.get("intro_color_hex", "#FFFFFF"),
                        "outline_color_hex": self.current_settings.get("intro_outline_hex", DEFAULT_OUTLINE_COLOR),
                        "outline_width": int(self.current_settings.get("intro_outline_width", 6)),
                        "shadow_radius": int(self.current_settings.get("intro_shadow_radius", 4)),
                        "box_enabled": True,
                        "box_color_hex": "#14171E",
                        "box_opacity": 85,
                        "margin_v": 0 # 0 = centro schermo
                    },
                    "outro": {
                        "enabled": True,
                        "text": outro_banner,
                        "font_name": self.current_settings.get("outro_font_name", DEFAULT_FONT_NAME),
                        "font_size": int(self.current_settings.get("outro_font_size", 66)),
                        "is_all_caps": False,
                        "primary_color_hex": self.current_settings.get("outro_color_hex", "#DCE0EA"),
                        "outline_color_hex": self.current_settings.get("outro_outline_hex", DEFAULT_OUTLINE_COLOR),
                        "outline_width": int(self.current_settings.get("outro_outline_width", 7)),
                        "shadow_radius": int(self.current_settings.get("outro_shadow_radius", 4)),
                        "box_enabled": True,
                        "box_color_hex": "#14171E",
                        "box_opacity": 85,
                        "margin_v": 0 # 0 = centro schermo
                    }
                }

    def _init_ui(self):
        main_layout = QVBoxLayout(self)
        main_layout.setContentsMargins(18, 14, 18, 14)
        main_layout.setSpacing(10)

        # 1. Header Bar
        header_bar = QHBoxLayout()
        lbl_title = QLabel("DESIGNER SOTTOTITOLI & SAFE-ZONE STUDIO")
        lbl_title.setStyleSheet("font-size: 15px; font-weight: 700; color: #DCE0EA;")
        header_bar.addWidget(lbl_title)
        header_bar.addStretch()

        lbl_autosave = QLabel("Auto-Save on Close: ON 🟢")
        lbl_autosave.setStyleSheet("font-size: 11px; font-weight: 600; color: #729B84; background-color: #21242C; padding: 4px 8px; border-radius: 4px; border: 1px solid #343946;")
        header_bar.addWidget(lbl_autosave)
        main_layout.addLayout(header_bar)

        # 2. Barra Navigatore Clip & Copia/Incolla Specifiche
        clip_nav_card = QFrame()
        clip_nav_card.setObjectName("CardSurface")
        clip_nav_layout = QHBoxLayout(clip_nav_card)
        clip_nav_layout.setContentsMargins(10, 6, 10, 6)
        clip_nav_layout.setSpacing(8)

        self.btn_prev_clip = QPushButton("◀ Clip Prec.")
        self.btn_prev_clip.setToolTip("Passa alla clip precedente di questo testo")
        self.btn_prev_clip.clicked.connect(self._on_prev_clip)
        clip_nav_layout.addWidget(self.btn_prev_clip)

        self.lbl_clip_badge = QLabel("🎬 Clip 1 di 1")
        self.lbl_clip_badge.setStyleSheet("font-size: 12px; font-weight: 700; color: #DCE0EA; padding: 0 6px;")
        clip_nav_layout.addWidget(self.lbl_clip_badge)

        self.btn_next_clip = QPushButton("Clip Succ. ▶")
        self.btn_next_clip.setToolTip("Passa alla clip successiva di questo testo")
        self.btn_next_clip.clicked.connect(self._on_next_clip)
        clip_nav_layout.addWidget(self.btn_next_clip)

        clip_nav_layout.addSpacing(16)

        # Azioni di Editing Indipendente e Copia/Incolla Specifiche
        self.btn_copy_specs = QPushButton("📋 Copia Specifiche")
        self.btn_copy_specs.setToolTip("Copia tutte le specifiche (sottotitoli, intro e outro) della clip selezionata")
        self.btn_copy_specs.clicked.connect(self._on_copy_specs)
        clip_nav_layout.addWidget(self.btn_copy_specs)

        self.btn_paste_specs = QPushButton("📥 Incolla Specifiche")
        self.btn_paste_specs.setToolTip("Incolla le specifiche copiate sulla clip corrente")
        self.btn_paste_specs.setEnabled(False)
        self.btn_paste_specs.clicked.connect(self._on_paste_specs)
        clip_nav_layout.addWidget(self.btn_paste_specs)

        self.btn_apply_all_clips = QPushButton("🔗 Applica a Tutte le Clip")
        self.btn_apply_all_clips.setToolTip("Propaga lo stile di questa clip a tutte le altre clip della storia")
        self.btn_apply_all_clips.clicked.connect(self._on_apply_all_clips)
        clip_nav_layout.addWidget(self.btn_apply_all_clips)

        clip_nav_layout.addStretch()

        self.lbl_status = QLabel("")
        self.lbl_status.setStyleSheet("color: #729B84; font-size: 11px; font-weight: 600;")
        clip_nav_layout.addWidget(self.lbl_status)

        main_layout.addWidget(clip_nav_card)

        # 3. Preset Row
        preset_row = QHBoxLayout()
        lbl_p = QLabel("Preset Font Attivo:")
        lbl_p.setStyleSheet("color: #949CAE; font-weight: 600;")
        self.cmb_presets = QComboBox()
        self.cmb_presets.setMinimumWidth(220)
        self.cmb_presets.currentIndexChanged.connect(self._on_preset_selected)

        self.btn_save_preset = QPushButton("💾 Salva Nuovo Preset")
        self.btn_save_preset.clicked.connect(self._save_new_preset)

        self.btn_apply_all = QPushButton("🔗 Applica Questo Font a Tutte le Storie in Coda")
        self.btn_apply_all.clicked.connect(self._on_apply_to_all_stories)

        preset_row.addWidget(lbl_p)
        preset_row.addWidget(self.cmb_presets)
        preset_row.addWidget(self.btn_save_preset)
        preset_row.addStretch()
        preset_row.addWidget(self.btn_apply_all)
        main_layout.addLayout(preset_row)

        # 4. Split 2 Colonne: Sinistra Tab Impostazioni Indipendenti, Destra Monitor 9:16 WYSIWYG
        body_layout = QHBoxLayout()
        body_layout.setSpacing(16)

        # --- COLONNA SINISTRA: TAB IMPOSTAZIONI INDIPENDENTI ---
        self.tab_settings = QTabWidget()
        self.tab_settings.setObjectName("SettingsTabs")

        # TAB 1: Sottotitoli Standard
        tab_sub = self._create_subtitles_tab()
        self.tab_settings.addTab(tab_sub, "💬 Sottotitoli Standard")

        # TAB 2: Titoli di Testa (Intro)
        tab_intro = self._create_intro_tab()
        self.tab_settings.addTab(tab_intro, "🎬 Titoli di Testa (Intro)")

        # TAB 3: Titoli di Coda (Outro)
        tab_outro = self._create_outro_tab()
        self.tab_settings.addTab(tab_outro, "🏁 Titoli di Coda (Outro)")

        body_layout.addWidget(self.tab_settings, stretch=5)

        # --- COLONNA DESTRA: ANTEPRIMA VISIVA LIVE 9:16 WYSIWYG ---
        right_panel = QFrame()
        right_panel.setObjectName("CardSurface")
        right_layout = QVBoxLayout(right_panel)
        right_layout.setContentsMargins(10, 8, 10, 8)
        right_layout.setSpacing(8)

        lbl_r_title = QLabel("ANTEPRIMA VISIVA LIVE (9:16 WYSIWYG)")
        lbl_r_title.setStyleSheet("font-size: 12px; font-weight: 700; color: #6B82A6;")
        right_layout.addWidget(lbl_r_title)

        # Barra commutazione anteprima (Titoli di Testa / Sottotitoli / Titoli di Coda)
        view_switcher_row = QHBoxLayout()
        view_switcher_row.setSpacing(4)
        self.btn_view_intro = QPushButton("🎬 Titolo di Testa")
        self.btn_view_sub = QPushButton("💬 Sottotitoli")
        self.btn_view_outro = QPushButton("🏁 Titolo di Coda")

        for b in (self.btn_view_intro, self.btn_view_sub, self.btn_view_outro):
            b.setCheckable(True)
            b.setStyleSheet("font-size: 11px; padding: 4px 8px;")
        self.btn_view_sub.setChecked(True)

        self.btn_view_intro.clicked.connect(lambda: self._set_preview_view_mode("INTRO"))
        self.btn_view_sub.clicked.connect(lambda: self._set_preview_view_mode("SUBTITLES"))
        self.btn_view_outro.clicked.connect(lambda: self._set_preview_view_mode("OUTRO"))

        self.tab_settings.currentChanged.connect(self._on_tab_changed)
        self.btn_view_outro.clicked.connect(lambda: self._set_preview_view_mode("OUTRO"))

        view_switcher_row.addWidget(self.btn_view_intro)
        view_switcher_row.addWidget(self.btn_view_sub)
        view_switcher_row.addWidget(self.btn_view_outro)
        right_layout.addLayout(view_switcher_row)

        # Canvas Monitor (270x480)
        self.canvas = SubtitleCanvasWidget()
        right_layout.addWidget(self.canvas, alignment=Qt.AlignCenter)

        # Controlli Scrub & Navigazione Fotogrammi Sotto il Canvas
        row_scrub = QHBoxLayout()
        self.lbl_scrub = QLabel("⏱️ Scrub: 02.5s / 10.0s")
        self.lbl_scrub.setStyleSheet("color: #949CAE; font-size: 11px; font-weight: 600;")

        self.btn_prev_frame = QPushButton("◀ -0.5s")
        self.btn_prev_frame.setToolTip("Sposta indietro di 0.5s")
        self.btn_prev_frame.clicked.connect(lambda: self.sld_scrub.setValue(max(0, self.sld_scrub.value() - 5)))

        self.sld_scrub = QSlider(Qt.Horizontal)
        self.sld_scrub.setRange(0, 100)
        self.sld_scrub.setValue(25)
        self.sld_scrub.setToolTip(
            "Scrub Temporale: trascina per esplorare in tempo reale i singoli fotogrammi del video\n"
            "e visualizzare l'animazione esatta dei sottotitoli e dei titoli corrispondenti."
        )
        self.sld_scrub.valueChanged.connect(self._on_scrub_slider_changed)

        self.btn_next_frame = QPushButton("+0.5s ▶")
        self.btn_next_frame.setToolTip("Sposta avanti di 0.5s")
        self.btn_next_frame.clicked.connect(lambda: self.sld_scrub.setValue(min(self.sld_scrub.maximum(), self.sld_scrub.value() + 5)))

        row_scrub.addWidget(self.lbl_scrub)
        row_scrub.addWidget(self.btn_prev_frame)
        row_scrub.addWidget(self.sld_scrub, stretch=1)
        row_scrub.addWidget(self.btn_next_frame)
        right_layout.addLayout(row_scrub)

        body_layout.addWidget(right_panel, stretch=4)
        main_layout.addLayout(body_layout)

        # Footer
        footer = QHBoxLayout()
        btn_reset = QPushButton("Ripristina Valori")
        btn_reset.clicked.connect(self._reset_defaults)
        footer.addWidget(btn_reset)
        footer.addStretch()

        btn_save = QPushButton("Salva & Chiudi (Auto-Saved on Close)")
        btn_save.setObjectName("AccentButton")
        btn_save.clicked.connect(self.accept)
        footer.addWidget(btn_save)
        main_layout.addLayout(footer)

    def _create_subtitles_tab(self) -> QWidget:
        """Crea il pannello di impostazione per i Sottotitoli Standard."""
        scroll = QScrollArea()
        scroll.setWidgetResizable(True)
        container = QWidget()
        l = QVBoxLayout(container)
        l.setSpacing(12)

        # Card 1: Animazione Dinamica
        c_anim = QFrame()
        c_anim.setObjectName("CardSurface")
        l_anim = QVBoxLayout(c_anim)
        lbl_anim_t = QLabel("STILE ANIMAZIONE DINAMICA:")
        lbl_anim_t.setStyleSheet("font-size: 12px; font-weight: 700; color: #6B82A6;")
        l_anim.addWidget(lbl_anim_t)

        self.btn_grp_anim = QButtonGroup(self)
        self.rb_pop = QRadioButton("Word Pop (Parola per parola sincronizzata)")
        self.rb_bounce = QRadioButton("Due Parole a Rimbalzo (Bounce Chunk)")
        self.rb_karaoke = QRadioButton("Karaoke Lineare (Evidenziazione su riga)")
        self.rb_pop.setChecked(True)

        self.btn_grp_anim.addButton(self.rb_pop, 1)
        self.btn_grp_anim.addButton(self.rb_bounce, 2)
        self.btn_grp_anim.addButton(self.rb_karaoke, 3)
        self.btn_grp_anim.buttonClicked.connect(self._on_control_changed)

        l_anim.addWidget(self.rb_pop)
        l_anim.addWidget(self.rb_bounce)
        l_anim.addWidget(self.rb_karaoke)
        l.addWidget(c_anim)

        # Card 2: Tipografia & Font
        c_font = QFrame()
        c_font.setObjectName("CardSurface")
        l_font = QVBoxLayout(c_font)
        lbl_font_t = QLabel("TIPOGRAFIA & FONT:")
        lbl_font_t.setStyleSheet("font-size: 12px; font-weight: 700; color: #6B82A6;")
        l_font.addWidget(lbl_font_t)

        row_f = QHBoxLayout()
        lbl_f = QLabel("Famiglia Font:")
        lbl_f.setFixedWidth(120)
        self.cmb_font = QComboBox()
        self.btn_import_font = QPushButton("➕ Importa Font (.ttf/.otf)")
        self.btn_import_font.clicked.connect(self._import_custom_font)
        row_f.addWidget(lbl_f)
        row_f.addWidget(self.cmb_font, stretch=1)
        row_f.addWidget(self.btn_import_font)
        l_font.addLayout(row_f)

        row_sz = QHBoxLayout()
        lbl_sz = QLabel("Dimensione Testo:")
        lbl_sz.setFixedWidth(120)
        self.sld_size = QSlider(Qt.Horizontal)
        self.sld_size.setRange(45, 85)
        self.sld_size.setValue(DEFAULT_FONT_SIZE)
        self.lbl_val_size = QLabel(f"{DEFAULT_FONT_SIZE} pt")
        self.lbl_val_size.setFixedWidth(45)
        self.sld_size.valueChanged.connect(lambda v: (self.lbl_val_size.setText(f"{v} pt"), self._on_control_changed()))
        row_sz.addWidget(lbl_sz)
        row_sz.addWidget(self.sld_size)
        row_sz.addWidget(self.lbl_val_size)
        l_font.addLayout(row_sz)

        row_case = QHBoxLayout()
        lbl_case = QLabel("Stile Lettere:")
        lbl_case.setFixedWidth(120)
        self.cmb_case = QComboBox()
        self.cmb_case.addItems(["TUTTO MAIUSCOLO (All Caps)", "Come da Testo (Originale)"])
        self.cmb_case.currentIndexChanged.connect(self._on_control_changed)
        row_case.addWidget(lbl_case)
        row_case.addWidget(self.cmb_case)
        l_font.addLayout(row_case)
        l.addWidget(c_font)

        # Card 3: Palette Colori & Personalizzazione
        c_col = QFrame()
        c_col.setObjectName("CardSurface")
        l_col = QVBoxLayout(c_col)
        lbl_col_t = QLabel("PALETTE COLORI & PERSONALIZZAZIONE:")
        lbl_col_t.setStyleSheet("font-size: 12px; font-weight: 700; color: #6B82A6;")
        l_col.addWidget(lbl_col_t)

        # Colore Base
        row_cbase = QHBoxLayout()
        lbl_cbase = QLabel("Colore del Font:")
        lbl_cbase.setFixedWidth(120)
        self.cmb_color_base = QComboBox()
        self.color_presets = [
            ("#FFFFFF", "Bianco Puro"),
            ("#DCE0EA", "Perla Morbido"),
            ("#FFFF00", "Giallo Viral"),
            ("#FFD700", "Oro Caldo"),
            ("#BFA175", "Sabbia Dorata"),
            ("#00FFCC", "Ciano Neon"),
            ("#00FF66", "Verde Lime"),
            ("#FF3366", "Rosso Corallo"),
            ("#FF9900", "Arancio Caldo")
        ]
        for hex_code, name in self.color_presets:
            self.cmb_color_base.addItem(f"{hex_code} ({name})", hex_code)
        self.cmb_color_base.currentIndexChanged.connect(self._on_color_combo_changed)

        self.lbl_color_preview = QLabel()
        self.lbl_color_preview.setFixedSize(26, 26)
        self.lbl_color_preview.setStyleSheet(f"background-color: {DEFAULT_TEXT_COLOR}; border: 1px solid #555E75; border-radius: 4px;")

        self.btn_pick_color = QPushButton("🎨 Scegli...")
        self.btn_pick_color.setStyleSheet("padding: 4px 8px; font-size: 11px;")
        self.btn_pick_color.clicked.connect(self._on_pick_custom_color)

        row_cbase.addWidget(lbl_cbase)
        row_cbase.addWidget(self.cmb_color_base, stretch=1)
        row_cbase.addWidget(self.lbl_color_preview)
        row_cbase.addWidget(self.btn_pick_color)
        l_col.addLayout(row_cbase)

        # Colore Evidenziazione (Highlight / Karaoke)
        row_chigh = QHBoxLayout()
        lbl_chigh = QLabel("Colore Highlight (Karaoke):")
        lbl_chigh.setFixedWidth(120)
        self.cmb_color_high = QComboBox()
        for hex_code, name in [
            ("#BFA175", "Sabbia Dorata"),
            ("#FFFF00", "Giallo Viral"),
            ("#00FFCC", "Ciano Neon"),
            ("#FF3366", "Rosso Corallo"),
            ("#FFFFFF", "Bianco Puro")
        ]:
            self.cmb_color_high.addItem(f"{hex_code} ({name})", hex_code)
        self.cmb_color_high.currentIndexChanged.connect(self._on_control_changed)

        self.btn_pick_high = QPushButton("🎨 Scegli...")
        self.btn_pick_high.setStyleSheet("padding: 4px 8px; font-size: 11px;")
        self.btn_pick_high.clicked.connect(self._on_pick_custom_highlight)

        row_chigh.addWidget(lbl_chigh)
        row_chigh.addWidget(self.cmb_color_high, stretch=1)
        row_chigh.addWidget(self.btn_pick_high)
        l_col.addLayout(row_chigh)

        # Spessore Bordo
        row_edge = QHBoxLayout()
        lbl_edge = QLabel("Spessore Bordo:")
        lbl_edge.setFixedWidth(120)
        self.sld_edge = QSlider(Qt.Horizontal)
        self.sld_edge.setRange(0, 10)
        self.sld_edge.setValue(DEFAULT_OUTLINE_WIDTH)
        self.lbl_val_edge = QLabel(f"{DEFAULT_OUTLINE_WIDTH} px")
        self.lbl_val_edge.setFixedWidth(45)
        self.sld_edge.valueChanged.connect(lambda v: (self.lbl_val_edge.setText(f"{v} px"), self._on_control_changed()))
        row_edge.addWidget(lbl_edge)
        row_edge.addWidget(self.sld_edge)
        row_edge.addWidget(self.lbl_val_edge)
        l_col.addLayout(row_edge)

        # Ombra Morbida
        row_shd = QHBoxLayout()
        lbl_shd = QLabel("Ombra Morbida:")
        lbl_shd.setFixedWidth(120)
        self.sld_shadow = QSlider(Qt.Horizontal)
        self.sld_shadow.setRange(0, 8)
        self.sld_shadow.setValue(DEFAULT_SHADOW_RADIUS)
        self.lbl_val_shd = QLabel(f"{DEFAULT_SHADOW_RADIUS} px")
        self.lbl_val_shd.setFixedWidth(45)
        self.sld_shadow.valueChanged.connect(lambda v: (self.lbl_val_shd.setText(f"{v} px"), self._on_control_changed()))
        row_shd.addWidget(lbl_shd)
        row_shd.addWidget(self.sld_shadow)
        row_shd.addWidget(self.lbl_val_shd)
        l_col.addLayout(row_shd)

        l.addWidget(c_col)

        # Card 4: Posizionamento & Safe-Zones
        c_pos = QFrame()
        c_pos.setObjectName("CardSurface")
        l_pos = QVBoxLayout(c_pos)
        lbl_pos_t = QLabel("POSIZIONAMENTO & SAFE ZONES SOCIAL:")
        lbl_pos_t.setStyleSheet("font-size: 12px; font-weight: 700; color: #6B82A6;")
        l_pos.addWidget(lbl_pos_t)

        row_y = QHBoxLayout()
        lbl_y = QLabel("Altezza Testo (Y Fondo):")
        lbl_y.setFixedWidth(140)
        self.sld_y = QSlider(Qt.Horizontal)
        self.sld_y.setRange(50, 800)
        self.sld_y.setValue(DEFAULT_MARGIN_V)
        self.lbl_val_y = QLabel(f"{DEFAULT_MARGIN_V} px")
        self.lbl_val_y.setFixedWidth(55)
        self.sld_y.valueChanged.connect(lambda v: (self.lbl_val_y.setText(f"{v} px"), self._on_control_changed()))
        row_y.addWidget(lbl_y)
        row_y.addWidget(self.sld_y)
        row_y.addWidget(self.lbl_val_y)
        l_pos.addLayout(row_y)

        self.chk_safe = QCheckBox("Mostra Maschere Safe-Zones (TikTok, Reels, Shorts)")
        self.chk_safe.setChecked(True)
        self.chk_safe.toggled.connect(self._on_toggle_safe_zones)
        l_pos.addWidget(self.chk_safe)

        l.addWidget(c_pos)
        scroll.setWidget(container)
        return scroll

    def _create_intro_tab(self) -> QWidget:
        """Crea il pannello di impostazione indipendente per i Titoli di Testa (Intro)."""
        scroll = QScrollArea()
        scroll.setWidgetResizable(True)
        container = QWidget()
        l = QVBoxLayout(container)
        l.setSpacing(12)

        # Card 1: Stato & Testo Intro per singola clip
        c_text = QFrame()
        c_text.setObjectName("CardSurface")
        l_text = QVBoxLayout(c_text)

        lbl_t = QLabel("TITOLO DI TESTA (INTRO BANNER):")
        lbl_t.setStyleSheet("font-size: 12px; font-weight: 700; color: #6B82A6;")
        l_text.addWidget(lbl_t)

        self.chk_intro_enable = QCheckBox("Abilita Titolo di Testa a Inizio Clip (0.0s - 1.5s)")
        self.chk_intro_enable.setChecked(True)
        self.chk_intro_enable.toggled.connect(self._on_intro_control_changed)
        l_text.addWidget(self.chk_intro_enable)

        row_tx = QHBoxLayout()
        lbl_tx = QLabel("Testo Titolo Intro:")
        lbl_tx.setFixedWidth(130)
        self.txt_intro_title = QLineEdit()
        self.txt_intro_title.setPlaceholderText("Es. Cosmos_BlackHoles part.1")
        self.txt_intro_title.textChanged.connect(self._on_intro_control_changed)
        row_tx.addWidget(lbl_tx)
        row_tx.addWidget(self.txt_intro_title)
        l_text.addLayout(row_tx)
        l.addWidget(c_text)

        # Card 2: Tipografia Indipendente
        c_font = QFrame()
        c_font.setObjectName("CardSurface")
        l_font = QVBoxLayout(c_font)
        lbl_f_t = QLabel("TIPOGRAFIA TITOLO DI TESTA:")
        lbl_f_t.setStyleSheet("font-size: 12px; font-weight: 700; color: #6B82A6;")
        l_font.addWidget(lbl_f_t)

        row_f = QHBoxLayout()
        lbl_f = QLabel("Famiglia Font:")
        lbl_f.setFixedWidth(130)
        self.cmb_intro_font = QComboBox()
        self.cmb_intro_font.currentIndexChanged.connect(self._on_intro_control_changed)
        row_f.addWidget(lbl_f)
        row_f.addWidget(self.cmb_intro_font)
        l_font.addLayout(row_f)

        row_sz = QHBoxLayout()
        lbl_sz = QLabel("Dimensione Font:")
        lbl_sz.setFixedWidth(130)
        self.sld_intro_size = QSlider(Qt.Horizontal)
        self.sld_intro_size.setRange(32, 90)
        self.sld_intro_size.setValue(64)
        self.lbl_val_intro_size = QLabel("64 pt")
        self.lbl_val_intro_size.setFixedWidth(45)
        self.sld_intro_size.valueChanged.connect(lambda v: (self.lbl_val_intro_size.setText(f"{v} pt"), self._on_intro_control_changed()))
        row_sz.addWidget(lbl_sz)
        row_sz.addWidget(self.sld_intro_size)
        row_sz.addWidget(self.lbl_val_intro_size)
        l_font.addLayout(row_sz)

        row_case = QHBoxLayout()
        lbl_case = QLabel("Stile Lettere:")
        lbl_case.setFixedWidth(130)
        self.cmb_intro_case = QComboBox()
        self.cmb_intro_case.addItems(["TUTTO MAIUSCOLO", "Come da Testo (Originale)"])
        self.cmb_intro_case.currentIndexChanged.connect(self._on_intro_control_changed)
        row_case.addWidget(lbl_case)
        row_case.addWidget(self.cmb_intro_case)
        l_font.addLayout(row_case)
        l.addWidget(c_font)

        # Card 3: Colori & Bordo Indipendenti
        c_col = QFrame()
        c_col.setObjectName("CardSurface")
        l_col = QVBoxLayout(c_col)
        lbl_col_t = QLabel("COLORI & STILE:")
        lbl_col_t.setStyleSheet("font-size: 12px; font-weight: 700; color: #6B82A6;")
        l_col.addWidget(lbl_col_t)

        row_c = QHBoxLayout()
        lbl_c = QLabel("Colore Testo:")
        lbl_c.setFixedWidth(130)
        self.cmb_intro_color = QComboBox()
        for hex_code, name in [("#FFFFFF", "Bianco Puro"), ("#DCE0EA", "Perla Morbido"), ("#FFFF00", "Giallo Viral"), ("#00FFCC", "Ciano Neon")]:
            self.cmb_intro_color.addItem(f"{hex_code} ({name})", hex_code)
        self.cmb_intro_color.currentIndexChanged.connect(self._on_intro_control_changed)

        self.btn_pick_intro_color = QPushButton("🎨 Scegli...")
        self.btn_pick_intro_color.clicked.connect(self._on_pick_intro_color)

        row_c.addWidget(lbl_c)
        row_c.addWidget(self.cmb_intro_color, stretch=1)
        row_c.addWidget(self.btn_pick_intro_color)
        l_col.addLayout(row_c)

        row_edge = QHBoxLayout()
        lbl_edge = QLabel("Spessore Bordo:")
        lbl_edge.setFixedWidth(130)
        self.sld_intro_edge = QSlider(Qt.Horizontal)
        self.sld_intro_edge.setRange(0, 12)
        self.sld_intro_edge.setValue(6)
        self.lbl_val_intro_edge = QLabel("6 px")
        self.lbl_val_intro_edge.setFixedWidth(45)
        self.sld_intro_edge.valueChanged.connect(lambda v: (self.lbl_val_intro_edge.setText(f"{v} px"), self._on_intro_control_changed()))
        row_edge.addWidget(lbl_edge)
        row_edge.addWidget(self.sld_intro_edge)
        row_edge.addWidget(self.lbl_val_intro_edge)
        l_col.addLayout(row_edge)

        # Sfondo Banner Box
        self.chk_intro_box = QCheckBox("Mostra Box di Sfondo Semi-trasparente")
        self.chk_intro_box.setChecked(True)
        self.chk_intro_box.toggled.connect(self._on_intro_control_changed)
        l_col.addWidget(self.chk_intro_box)

        row_op = QHBoxLayout()
        lbl_op = QLabel("Opacità Sfondo Box:")
        lbl_op.setFixedWidth(130)
        self.sld_intro_opacity = QSlider(Qt.Horizontal)
        self.sld_intro_opacity.setRange(20, 100)
        self.sld_intro_opacity.setValue(85)
        self.lbl_val_intro_op = QLabel("85 %")
        self.lbl_val_intro_op.setFixedWidth(45)
        self.sld_intro_opacity.valueChanged.connect(lambda v: (self.lbl_val_intro_op.setText(f"{v} %"), self._on_intro_control_changed()))
        row_op.addWidget(lbl_op)
        row_op.addWidget(self.sld_intro_opacity)
        row_op.addWidget(self.lbl_val_intro_op)
        l_col.addLayout(row_op)

        l.addWidget(c_col)
        scroll.setWidget(container)
        return scroll

    def _create_outro_tab(self) -> QWidget:
        """Crea il pannello di impostazione indipendente per i Titoli di Coda (Outro CTA)."""
        scroll = QScrollArea()
        scroll.setWidgetResizable(True)
        container = QWidget()
        l = QVBoxLayout(container)
        l.setSpacing(12)

        # Card 1: Stato & Testo Outro per singola clip
        c_text = QFrame()
        c_text.setObjectName("CardSurface")
        l_text = QVBoxLayout(c_text)

        lbl_t = QLabel("TITOLO DI CODA (OUTRO CTA BANNER):")
        lbl_t.setStyleSheet("font-size: 12px; font-weight: 700; color: #6B82A6;")
        l_text.addWidget(lbl_t)

        self.chk_outro_enable = QCheckBox("Abilita Titolo di Coda a Fine Clip")
        self.chk_outro_enable.setChecked(True)
        self.chk_outro_enable.toggled.connect(self._on_outro_control_changed)
        l_text.addWidget(self.chk_outro_enable)

        row_tx = QHBoxLayout()
        lbl_tx = QLabel("Testo Outro a Schermo:")
        lbl_tx.setFixedWidth(130)
        self.txt_outro_title = QLineEdit()
        self.txt_outro_title.setPlaceholderText("Es. Follow for part.2 o Follow for more!")
        self.txt_outro_title.textChanged.connect(self._on_outro_control_changed)
        row_tx.addWidget(lbl_tx)
        row_tx.addWidget(self.txt_outro_title)
        l_text.addLayout(row_tx)
        l.addWidget(c_text)

        # Card 2: Tipografia Indipendente
        c_font = QFrame()
        c_font.setObjectName("CardSurface")
        l_font = QVBoxLayout(c_font)
        lbl_f_t = QLabel("TIPOGRAFIA TITOLO DI CODA:")
        lbl_f_t.setStyleSheet("font-size: 12px; font-weight: 700; color: #6B82A6;")
        l_font.addWidget(lbl_f_t)

        row_f = QHBoxLayout()
        lbl_f = QLabel("Famiglia Font:")
        lbl_f.setFixedWidth(130)
        self.cmb_outro_font = QComboBox()
        self.cmb_outro_font.currentIndexChanged.connect(self._on_outro_control_changed)
        row_f.addWidget(lbl_f)
        row_f.addWidget(self.cmb_outro_font)
        l_font.addLayout(row_f)

        row_sz = QHBoxLayout()
        lbl_sz = QLabel("Dimensione Font:")
        lbl_sz.setFixedWidth(130)
        self.sld_outro_size = QSlider(Qt.Horizontal)
        self.sld_outro_size.setRange(32, 90)
        self.sld_outro_size.setValue(66)
        self.lbl_val_outro_size = QLabel("66 pt")
        self.lbl_val_outro_size.setFixedWidth(45)
        self.sld_outro_size.valueChanged.connect(lambda v: (self.lbl_val_outro_size.setText(f"{v} pt"), self._on_outro_control_changed()))
        row_sz.addWidget(lbl_sz)
        row_sz.addWidget(self.sld_outro_size)
        row_sz.addWidget(self.lbl_val_outro_size)
        l_font.addLayout(row_sz)

        row_case = QHBoxLayout()
        lbl_case = QLabel("Stile Lettere:")
        lbl_case.setFixedWidth(130)
        self.cmb_outro_case = QComboBox()
        self.cmb_outro_case.addItems(["Come da Testo (Originale)", "TUTTO MAIUSCOLO"])
        self.cmb_outro_case.currentIndexChanged.connect(self._on_outro_control_changed)
        row_case.addWidget(lbl_case)
        row_case.addWidget(self.cmb_outro_case)
        l_font.addLayout(row_case)
        l.addWidget(c_font)

        # Card 3: Colori & Bordo Indipendenti
        c_col = QFrame()
        c_col.setObjectName("CardSurface")
        l_col = QVBoxLayout(c_col)
        lbl_col_t = QLabel("COLORI & STILE:")
        lbl_col_t.setStyleSheet("font-size: 12px; font-weight: 700; color: #6B82A6;")
        l_col.addWidget(lbl_col_t)

        row_c = QHBoxLayout()
        lbl_c = QLabel("Colore Testo:")
        lbl_c.setFixedWidth(130)
        self.cmb_outro_color = QComboBox()
        for hex_code, name in [("#DCE0EA", "Perla Morbido"), ("#BFA175", "Sabbia Dorata"), ("#FFFFFF", "Bianco Puro"), ("#FFFF00", "Giallo Viral")]:
            self.cmb_outro_color.addItem(f"{hex_code} ({name})", hex_code)
        self.cmb_outro_color.currentIndexChanged.connect(self._on_outro_control_changed)

        self.btn_pick_outro_color = QPushButton("🎨 Scegli...")
        self.btn_pick_outro_color.clicked.connect(self._on_pick_outro_color)

        row_c.addWidget(lbl_c)
        row_c.addWidget(self.cmb_outro_color, stretch=1)
        row_c.addWidget(self.btn_pick_outro_color)
        l_col.addLayout(row_c)

        row_edge = QHBoxLayout()
        lbl_edge = QLabel("Spessore Bordo:")
        lbl_edge.setFixedWidth(130)
        self.sld_outro_edge = QSlider(Qt.Horizontal)
        self.sld_outro_edge.setRange(0, 12)
        self.sld_outro_edge.setValue(7)
        self.lbl_val_outro_edge = QLabel("7 px")
        self.lbl_val_outro_edge.setFixedWidth(45)
        self.sld_outro_edge.valueChanged.connect(lambda v: (self.lbl_val_outro_edge.setText(f"{v} px"), self._on_outro_control_changed()))
        row_edge.addWidget(lbl_edge)
        row_edge.addWidget(self.sld_outro_edge)
        row_edge.addWidget(self.lbl_val_outro_edge)
        l_col.addLayout(row_edge)

        # Sfondo Banner Box
        self.chk_outro_box = QCheckBox("Mostra Box di Sfondo Semi-trasparente")
        self.chk_outro_box.setChecked(True)
        self.chk_outro_box.toggled.connect(self._on_outro_control_changed)
        l_col.addWidget(self.chk_outro_box)

        row_op = QHBoxLayout()
        lbl_op = QLabel("Opacità Sfondo Box:")
        lbl_op.setFixedWidth(130)
        self.sld_outro_opacity = QSlider(Qt.Horizontal)
        self.sld_outro_opacity.setRange(20, 100)
        self.sld_outro_opacity.setValue(85)
        self.lbl_val_outro_op = QLabel("85 %")
        self.lbl_val_outro_op.setFixedWidth(45)
        self.sld_outro_opacity.valueChanged.connect(lambda v: (self.lbl_val_outro_op.setText(f"{v} %"), self._on_outro_control_changed()))
        row_op.addWidget(lbl_op)
        row_op.addWidget(self.sld_outro_opacity)
        row_op.addWidget(self.lbl_val_outro_op)
        l_col.addLayout(row_op)

        l.addWidget(c_col)
        scroll.setWidget(container)
        return scroll

    def _on_tab_changed(self, index: int):
        """Sincronizza la vista di anteprima quando si cambia tab delle impostazioni."""
        if index == 0:
            self._set_preview_view_mode("SUBTITLES")
        elif index == 1:
            self._set_preview_view_mode("INTRO")
        elif index == 2:
            self._set_preview_view_mode("OUTRO")

    def _set_preview_view_mode(self, mode: str):
        """Imposta la modalità di rendering sull'anteprima (Intro, Sottotitoli o Outro)."""
        if hasattr(self, "btn_view_intro"):
            self.btn_view_intro.setChecked(mode == "INTRO")
            self.btn_view_sub.setChecked(mode == "SUBTITLES")
            self.btn_view_outro.setChecked(mode == "OUTRO")

        if hasattr(self, "canvas"):
            self.canvas.set_view_mode(mode)

        if hasattr(self, "sld_scrub"):
            # Posiziona lo scrub al momento indicativo corrispondente
            if mode == "INTRO":
                self.sld_scrub.setValue(5) # 0.5s
                if hasattr(self, "tab_settings") and self.tab_settings.currentIndex() != 1:
                    self.tab_settings.setCurrentIndex(1)
            elif mode == "OUTRO":
                self.sld_scrub.setValue(max(0, self.sld_scrub.maximum() - 5)) # fine clip
                if hasattr(self, "tab_settings") and self.tab_settings.currentIndex() != 2:
                    self.tab_settings.setCurrentIndex(2)
            else:
                self.sld_scrub.setValue(25) # 2.5s narrazione
                if hasattr(self, "tab_settings") and self.tab_settings.currentIndex() != 0:
                    self.tab_settings.setCurrentIndex(0)

    def _load_clip_data_to_ui(self, clip_idx: int):
        """Carica nell'interfaccia i dati e gli stili specifici della clip selezionata."""
        if clip_idx < 0 or clip_idx >= len(self.clips):
            return

        self.current_clip_idx = clip_idx
        clip = self.clips[clip_idx]
        total_clips = len(self.clips)

        self.lbl_clip_badge.setText(f"🎬 Clip {clip_idx + 1} di {total_clips}: \"{clip['title']}\"")
        self.btn_prev_clip.setEnabled(clip_idx > 0)
        self.btn_next_clip.setEnabled(clip_idx < total_clips - 1)

        # Aggiorna il testo dell'anteprima sul canvas
        self.canvas.set_clip_text(clip["text"])

        # Carica configurazione specifica
        styles = self.clip_styles.get(clip_idx, {})
        sub_s = styles.get("subtitle", {})
        intro_s = styles.get("intro", {})
        outro_s = styles.get("outro", {})

        # Sottotitoli UI
        anim = sub_s.get("animation_style", "WORD_POP")
        if anim == "BOUNCE":
            self.rb_bounce.setChecked(True)
        elif anim in ("KARAOKE", "KARAOKE_LINEAR"):
            self.rb_karaoke.setChecked(True)
        else:
            self.rb_pop.setChecked(True)

        idx_f = self.cmb_font.findText(sub_s.get("font_name", DEFAULT_FONT_NAME))
        if idx_f >= 0:
            self.cmb_font.setCurrentIndex(idx_f)
        self.sld_size.setValue(int(sub_s.get("font_size", DEFAULT_FONT_SIZE)))
        self.cmb_case.setCurrentIndex(0 if sub_s.get("is_all_caps", True) else 1)
        self.sld_edge.setValue(int(sub_s.get("outline_width", DEFAULT_OUTLINE_WIDTH)))
        self.sld_shadow.setValue(int(sub_s.get("shadow_radius", DEFAULT_SHADOW_RADIUS)))
        self.sld_y.setValue(int(sub_s.get("margin_v", DEFAULT_MARGIN_V)))

        col_base = str(sub_s.get("primary_color_hex", DEFAULT_TEXT_COLOR)).upper()
        self._set_combo_color(self.cmb_color_base, col_base)
        self._update_color_preview(col_base)

        col_high = str(sub_s.get("highlight_color_hex", DEFAULT_HIGHLIGHT_COLOR)).upper()
        self._set_combo_color(self.cmb_color_high, col_high)

        # Intro UI
        self.chk_intro_enable.setChecked(bool(intro_s.get("enabled", True)))
        self.txt_intro_title.setText(intro_s.get("text", clip["title"]))
        idx_if = self.cmb_intro_font.findText(intro_s.get("font_name", DEFAULT_FONT_NAME))
        if idx_if >= 0:
            self.cmb_intro_font.setCurrentIndex(idx_if)
        self.sld_intro_size.setValue(int(intro_s.get("font_size", 64)))
        self.cmb_intro_case.setCurrentIndex(0 if intro_s.get("is_all_caps", True) else 1)
        self._set_combo_color(self.cmb_intro_color, str(intro_s.get("primary_color_hex", "#FFFFFF")).upper())
        self.sld_intro_edge.setValue(int(intro_s.get("outline_width", 6)))
        self.chk_intro_box.setChecked(bool(intro_s.get("box_enabled", True)))
        self.sld_intro_opacity.setValue(int(intro_s.get("box_opacity", 85)))

        # Outro UI
        self.chk_outro_enable.setChecked(bool(outro_s.get("enabled", True)))
        self.txt_outro_title.setText(outro_s.get("text", "Follow for more!"))
        idx_of = self.cmb_outro_font.findText(outro_s.get("font_name", DEFAULT_FONT_NAME))
        if idx_of >= 0:
            self.cmb_outro_font.setCurrentIndex(idx_of)
        self.sld_outro_size.setValue(int(outro_s.get("font_size", 66)))
        self.cmb_outro_case.setCurrentIndex(1 if outro_s.get("is_all_caps", False) else 0)
        self._set_combo_color(self.cmb_outro_color, str(outro_s.get("primary_color_hex", "#DCE0EA")).upper())
        self.sld_outro_edge.setValue(int(outro_s.get("outline_width", 7)))
        self.chk_outro_box.setChecked(bool(outro_s.get("box_enabled", True)))
        self.sld_outro_opacity.setValue(int(outro_s.get("box_opacity", 85)))

        # Aggiorna il canvas monitor
        self.canvas.update_subtitle_style(sub_s)
        self.canvas.update_intro_style(intro_s)
        self.canvas.update_outro_style(outro_s)

        # Se disponibile video, estrae il fotogramma per la clip attiva
        self._extract_frame_for_current_clip()

    def _save_ui_to_current_clip_data(self):
        """Salva lo stato corrente dei controlli grafici nella mappa della clip attiva."""
        anim = "WORD_POP"
        if self.rb_bounce.isChecked():
            anim = "BOUNCE"
        elif self.rb_karaoke.isChecked():
            anim = "KARAOKE"

        sub_col = self.cmb_color_base.currentText().split(" ")[0] if self.cmb_color_base.currentText() else DEFAULT_TEXT_COLOR
        high_col = self.cmb_color_high.currentText().split(" ")[0] if self.cmb_color_high.currentText() else DEFAULT_HIGHLIGHT_COLOR

        intro_col = self.cmb_intro_color.currentText().split(" ")[0] if self.cmb_intro_color.currentText() else "#FFFFFF"
        outro_col = self.cmb_outro_color.currentText().split(" ")[0] if self.cmb_outro_color.currentText() else "#DCE0EA"

        self.clip_styles[self.current_clip_idx] = {
            "subtitle": {
                "animation_style": anim,
                "font_name": self.cmb_font.currentText(),
                "font_size": self.sld_size.value(),
                "is_all_caps": 1 if self.cmb_case.currentIndex() == 0 else 0,
                "primary_color_hex": sub_col,
                "highlight_color_hex": high_col,
                "outline_color_hex": DEFAULT_OUTLINE_COLOR,
                "outline_width": self.sld_edge.value(),
                "shadow_radius": self.sld_shadow.value(),
                "margin_v": self.sld_y.value()
            },
            "intro": {
                "enabled": self.chk_intro_enable.isChecked(),
                "text": self.txt_intro_title.text().strip(),
                "font_name": self.cmb_intro_font.currentText(),
                "font_size": self.sld_intro_size.value(),
                "is_all_caps": 1 if self.cmb_intro_case.currentIndex() == 0 else 0,
                "primary_color_hex": intro_col,
                "outline_color_hex": DEFAULT_OUTLINE_COLOR,
                "outline_width": self.sld_intro_edge.value(),
                "shadow_radius": 4,
                "box_enabled": self.chk_intro_box.isChecked(),
                "box_color_hex": "#14171E",
                "box_opacity": self.sld_intro_opacity.value(),
                "margin_v": 0
            },
            "outro": {
                "enabled": self.chk_outro_enable.isChecked(),
                "text": self.txt_outro_title.text().strip(),
                "font_name": self.cmb_outro_font.currentText(),
                "font_size": self.sld_outro_size.value(),
                "is_all_caps": 1 if self.cmb_outro_case.currentIndex() == 1 else 0,
                "primary_color_hex": outro_col,
                "outline_color_hex": DEFAULT_OUTLINE_COLOR,
                "outline_width": self.sld_outro_edge.value(),
                "shadow_radius": 4,
                "box_enabled": self.chk_outro_box.isChecked(),
                "box_color_hex": "#14171E",
                "box_opacity": self.sld_outro_opacity.value(),
                "margin_v": 0
            }
        }

    def _on_control_changed(self):
        """Chiamato quando viene modificato un controllo dei Sottotitoli Standard."""
        self._save_ui_to_current_clip_data()
        sub_s = self.clip_styles[self.current_clip_idx]["subtitle"]
        self.canvas.update_subtitle_style(sub_s)

    def _on_intro_control_changed(self):
        """Chiamato quando viene modificato un controllo dei Titoli di Testa."""
        self._save_ui_to_current_clip_data()
        intro_s = self.clip_styles[self.current_clip_idx]["intro"]
        self.canvas.update_intro_style(intro_s)

    def _on_outro_control_changed(self):
        """Chiamato quando viene modificato un controllo dei Titoli di Coda."""
        self._save_ui_to_current_clip_data()
        outro_s = self.clip_styles[self.current_clip_idx]["outro"]
        self.canvas.update_outro_style(outro_s)

    def _on_prev_clip(self):
        if self.current_clip_idx > 0:
            self._save_ui_to_current_clip_data()
            self._load_clip_data_to_ui(self.current_clip_idx - 1)
            self.lbl_status.setText(f"Clip #{self.current_clip_idx + 1} attiva.")

    def _on_next_clip(self):
        if self.current_clip_idx < len(self.clips) - 1:
            self._save_ui_to_current_clip_data()
            self._load_clip_data_to_ui(self.current_clip_idx + 1)
            self.lbl_status.setText(f"Clip #{self.current_clip_idx + 1} attiva.")

    def _on_copy_specs(self):
        """Copia tutte le specifiche (stile sottotitoli, intro e outro) della clip corrente."""
        self._save_ui_to_current_clip_data()
        self.copied_specs_clipboard = copy.deepcopy(self.clip_styles[self.current_clip_idx])
        self.btn_paste_specs.setEnabled(True)
        self.lbl_status.setText(f"✅ Specifiche Clip #{self.current_clip_idx + 1} copiate negli appunti!")

    def _on_paste_specs(self):
        """Incolla le specifiche copiate sulla clip attiva."""
        if not self.copied_specs_clipboard:
            return

        # Mantiene il testo univoco della clip corrente se già digitato, trasferendo tutti gli stili
        cur_intro_text = self.clip_styles[self.current_clip_idx]["intro"]["text"]
        cur_outro_text = self.clip_styles[self.current_clip_idx]["outro"]["text"]

        self.clip_styles[self.current_clip_idx] = copy.deepcopy(self.copied_specs_clipboard)

        if cur_intro_text:
            self.clip_styles[self.current_clip_idx]["intro"]["text"] = cur_intro_text
        if cur_outro_text:
            self.clip_styles[self.current_clip_idx]["outro"]["text"] = cur_outro_text

        self._load_clip_data_to_ui(self.current_clip_idx)
        self.lbl_status.setText(f"📥 Specifiche applicate a Clip #{self.current_clip_idx + 1}!")

    def _on_apply_all_clips(self):
        """Applica gli stili della clip corrente a tutte le clip dello script attivo."""
        self._save_ui_to_current_clip_data()
        source_specs = copy.deepcopy(self.clip_styles[self.current_clip_idx])

        for i in self.clip_styles:
            t_intro = self.clip_styles[i]["intro"]["text"]
            t_outro = self.clip_styles[i]["outro"]["text"]
            self.clip_styles[i] = copy.deepcopy(source_specs)
            if t_intro:
                self.clip_styles[i]["intro"]["text"] = t_intro
            if t_outro:
                self.clip_styles[i]["outro"]["text"] = t_outro

        self.lbl_status.setText("🔗 Stile applicato a tutte le clip dello script!")
        QMessageBox.information(self, "Stile Propagato", "Stile e impostazioni grafiche applicati con successo a tutte le clip di questa storia.")

    def _on_scrub_slider_changed(self, val: int):
        """Aggiorna la timeline di scrubbing e programma l'estrazione del fotogramma reale."""
        sec = val / 10.0
        self.lbl_scrub.setText(f"⏱️ Scrub: {sec:04.1f}s / 10.0s")
        self.canvas.set_scrub_time(sec)
        self.frame_scrub_timer.start(150)

    def _on_scrub_timer_timeout(self):
        """Estrae il fotogramma al timestamp dello slider per l'anteprima reale."""
        self._extract_frame_for_current_clip()

    def _extract_frame_for_current_clip(self):
        """Estrae con FFmpeg il fotogramma esatto con ritaglio centrale 9:16 (WYSIWYG)."""
        video_file = self.video_file_path
        if not video_file or not os.path.exists(video_file):
            if self.video_pool_mgr:
                try:
                    for s in self.video_pool_mgr.get_all_sources():
                        fp = s.get("file_path", "")
                        if fp and os.path.exists(fp):
                            video_file = fp
                            break
                except Exception:
                    pass

        if not video_file and VIDEO_POOL_DIR.exists():
            for p in VIDEO_POOL_DIR.glob("*.mp4"):
                if p.exists() and p.stat().st_size > 10000:
                    video_file = str(p)
                    break

        if not video_file or not os.path.exists(video_file):
            if self.temp_frame_path and os.path.exists(self.temp_frame_path):
                self.canvas.set_background_image(self.temp_frame_path)
            return

        ffmpeg, _ = find_system_ffmpeg() if isinstance(find_system_ffmpeg(), tuple) else (find_system_ffmpeg(), None)
        if not ffmpeg or not os.path.exists(ffmpeg):
            return

        # Calcola offset temporale in base alla clip e allo scrub
        scrub_sec = self.sld_scrub.value() / 10.0
        clip_offset_sec = self.current_clip_idx * 38.0
        total_time_sec = clip_offset_sec + scrub_sec

        out_frame = CACHE_DIR / f"temp_preview_clip_{self.current_clip_idx}_{int(scrub_sec * 10)}.jpg"
        if not out_frame.exists():
            cmd = [
                ffmpeg, "-y",
                "-ss", f"{total_time_sec:.2f}",
                "-i", str(video_file),
                "-vf", f"scale={CANVAS_WIDTH}:{CANVAS_HEIGHT}:force_original_aspect_ratio=increase,crop={CANVAS_WIDTH}:{CANVAS_HEIGHT}",
                "-vframes", "1",
                "-q:v", "2",
                str(out_frame)
            ]
            try:
                subprocess.run(cmd, capture_output=True, timeout=6)
            except Exception as e:
                log.warning(f"Errore estrazione frame scrub: {e}")

        if out_frame.exists() and out_frame.stat().st_size > 400:
            self.canvas.set_background_image(str(out_frame))

    def _auto_detect_video_frame(self):
        """Auto-rileva un frame all'avvio se disponibile."""
        if self.temp_frame_path and os.path.exists(self.temp_frame_path):
            self.canvas.set_background_image(self.temp_frame_path)
        else:
            self._extract_frame_for_current_clip()

    def _set_combo_color(self, combo: QComboBox, hex_code: str):
        found = False
        for i in range(combo.count()):
            if combo.itemText(i).startswith(hex_code):
                combo.setCurrentIndex(i)
                found = True
                break
        if not found:
            combo.addItem(f"{hex_code} (Personalizzato)", hex_code)
            combo.setCurrentIndex(combo.count() - 1)

    def _update_color_preview(self, hex_code: str):
        self.lbl_color_preview.setStyleSheet(f"background-color: {hex_code}; border: 1px solid #555E75; border-radius: 4px;")

    def _on_color_combo_changed(self):
        curr_text = self.cmb_color_base.currentText()
        hex_code = curr_text.split(" ")[0] if curr_text else DEFAULT_TEXT_COLOR
        self._update_color_preview(hex_code)
        self._on_control_changed()

    def _on_pick_custom_color(self):
        curr_text = self.cmb_color_base.currentText()
        hex_code = curr_text.split(" ")[0] if curr_text else DEFAULT_TEXT_COLOR
        picked = QColorDialog.getColor(QColor(hex_code), self, "Scegli Colore Font Sottotitoli")
        if picked.isValid():
            chosen_hex = picked.name().upper()
            self._set_combo_color(self.cmb_color_base, chosen_hex)
            self._update_color_preview(chosen_hex)
            self._on_control_changed()

    def _on_pick_custom_highlight(self):
        curr_text = self.cmb_color_high.currentText()
        hex_code = curr_text.split(" ")[0] if curr_text else DEFAULT_HIGHLIGHT_COLOR
        picked = QColorDialog.getColor(QColor(hex_code), self, "Scegli Colore Evidenziazione (Highlight)")
        if picked.isValid():
            chosen_hex = picked.name().upper()
            self._set_combo_color(self.cmb_color_high, chosen_hex)
            self._on_control_changed()

    def _on_pick_intro_color(self):
        curr_text = self.cmb_intro_color.currentText()
        hex_code = curr_text.split(" ")[0] if curr_text else "#FFFFFF"
        picked = QColorDialog.getColor(QColor(hex_code), self, "Scegli Colore Titolo di Testa")
        if picked.isValid():
            chosen_hex = picked.name().upper()
            self._set_combo_color(self.cmb_intro_color, chosen_hex)
            self._on_intro_control_changed()

    def _on_pick_outro_color(self):
        curr_text = self.cmb_outro_color.currentText()
        hex_code = curr_text.split(" ")[0] if curr_text else "#DCE0EA"
        picked = QColorDialog.getColor(QColor(hex_code), self, "Scegli Colore Titolo di Coda")
        if picked.isValid():
            chosen_hex = picked.name().upper()
            self._set_combo_color(self.cmb_outro_color, chosen_hex)
            self._on_outro_control_changed()

    def _on_toggle_safe_zones(self, checked: bool):
        self.canvas.show_safe_zones = bool(checked)
        self.canvas.update()

    def _load_available_fonts(self):
        for combo in (self.cmb_font, self.cmb_intro_font, self.cmb_outro_font):
            combo.blockSignals(True)
            combo.clear()
            base_fonts = ["Montserrat Black", "Anton", "The Bold Font", "Poppins"]
            for bf in base_fonts:
                combo.addItem(bf)

            fonts_dir = Path(FONTS_DIR)
            if fonts_dir.exists():
                for ext in ("*.ttf", "*.otf", "*.TTF", "*.OTF"):
                    for font_path in fonts_dir.glob(ext):
                        font_id = QFontDatabase.addApplicationFont(str(font_path.resolve()))
                        if font_id != -1:
                            fams = QFontDatabase.applicationFontFamilies(font_id)
                            for fam in fams:
                                if combo.findText(fam) == -1:
                                    combo.addItem(fam)
                        else:
                            stem_name = font_path.stem.replace("-", " ")
                            if combo.findText(stem_name) == -1:
                                combo.addItem(stem_name)
            combo.blockSignals(False)

        self.cmb_font.currentIndexChanged.connect(self._on_control_changed)

    def _import_custom_font(self):
        files, _ = QFileDialog.getOpenFileNames(
            self,
            "Seleziona File Font (.ttf, .otf)",
            "",
            "Font Files (*.ttf *.otf *.TTF *.OTF);;All Files (*)"
        )
        if not files:
            return

        fonts_dir = Path(FONTS_DIR)
        fonts_dir.mkdir(parents=True, exist_ok=True)
        imported_names = []

        for f_path in files:
            src = Path(f_path)
            dest = fonts_dir / src.name
            try:
                if src.resolve() != dest.resolve():
                    shutil.copy2(src, dest)
                font_id = QFontDatabase.addApplicationFont(str(dest.resolve()))
                if font_id != -1:
                    fams = QFontDatabase.applicationFontFamilies(font_id)
                    for fam in fams:
                        for c in (self.cmb_font, self.cmb_intro_font, self.cmb_outro_font):
                            if c.findText(fam) == -1:
                                c.addItem(fam)
                        imported_names.append(fam)
            except Exception as e:
                log.warning(f"Errore importazione font {src.name}: {e}")

        if imported_names:
            last_name = imported_names[-1]
            idx = self.cmb_font.findText(last_name)
            if idx >= 0:
                self.cmb_font.setCurrentIndex(idx)
            self._on_control_changed()
            QMessageBox.information(
                self,
                "Font Importato con Successo",
                f"Famiglia font '{last_name}' aggiunta alla tua libreria e subito attiva per l'anteprima!"
            )

    def _load_presets_combo(self):
        presets = self.preset_manager.get_subtitle_presets()
        self.cmb_presets.clear()
        self.cmb_presets.addItem("Default (Viral Gold Pop)")
        for p in presets:
            self.cmb_presets.addItem(p["preset_name"], p)

    def _on_preset_selected(self, index: int):
        data = self.cmb_presets.currentData()
        if data:
            idx = self.cmb_font.findText(data.get("font_name", DEFAULT_FONT_NAME))
            if idx >= 0:
                self.cmb_font.setCurrentIndex(idx)
            self.sld_size.setValue(int(data.get("font_size", DEFAULT_FONT_SIZE)))
            self.cmb_case.setCurrentIndex(0 if data.get("is_all_caps", 1) else 1)
            self.sld_edge.setValue(int(data.get("outline_width", DEFAULT_OUTLINE_WIDTH)))
            self.sld_shadow.setValue(int(data.get("shadow_radius", DEFAULT_SHADOW_RADIUS)))
            self.sld_y.setValue(int(data.get("margin_v", DEFAULT_MARGIN_V)))

            col = str(data.get("primary_color_hex", DEFAULT_TEXT_COLOR)).upper()
            self._set_combo_color(self.cmb_color_base, col)
            self._update_color_preview(col)

            anim = data.get("animation_style", "WORD_POP")
            if anim == "BOUNCE":
                self.rb_bounce.setChecked(True)
            elif anim in ("KARAOKE", "KARAOKE_LINEAR"):
                self.rb_karaoke.setChecked(True)
            else:
                self.rb_pop.setChecked(True)

            self._on_control_changed()

    def _save_new_preset(self):
        name, ok = QInputDialog.getText(self, "Salva Preset Tipografico", "Inserisci il nome del nuovo preset font:")
        if ok and name.strip():
            settings = self.get_settings()
            self.preset_manager.save_subtitle_preset(name.strip(), settings)
            self._load_presets_combo()
            QMessageBox.information(self, "Preset Salvato", f"Preset '{name.strip()}' salvato con successo.")

    def _reset_defaults(self):
        self.rb_pop.setChecked(True)
        self.cmb_font.setCurrentIndex(0)
        self.sld_size.setValue(DEFAULT_FONT_SIZE)
        self.cmb_case.setCurrentIndex(0)
        self.cmb_color_base.setCurrentIndex(0)
        self._update_color_preview(DEFAULT_TEXT_COLOR)
        self.sld_edge.setValue(DEFAULT_OUTLINE_WIDTH)
        self.sld_shadow.setValue(DEFAULT_SHADOW_RADIUS)
        self.sld_y.setValue(DEFAULT_MARGIN_V)
        self.chk_safe.setChecked(True)
        self._on_control_changed()

    def _on_apply_to_all_stories(self):
        settings = self.get_settings()
        self.apply_to_all_requested.emit(settings)
        QMessageBox.information(self, "Applicato a Tutte", "Lo stile sottotitoli è stato propagato a tutte le storie in coda.")

    def get_settings(self) -> dict:
        """Restituisce le impostazioni complete, inclusa la mappa delle singole clip e i titoli."""
        self._save_ui_to_current_clip_data()

        cur_sub = self.clip_styles[self.current_clip_idx]["subtitle"]
        cur_intro = self.clip_styles[self.current_clip_idx]["intro"]
        cur_outro = self.clip_styles[self.current_clip_idx]["outro"]

        # Liste di testo intro e outro per ogni clip
        custom_intros = [self.clip_styles[i]["intro"]["text"] for i in range(len(self.clips))]
        custom_outros = [{"spoken": self.clip_styles[i]["outro"]["text"], "banner": self.clip_styles[i]["outro"]["text"]} for i in range(len(self.clips))]

        result = dict(cur_sub)
        result["intro_style"] = dict(cur_intro)
        result["outro_style"] = dict(cur_outro)
        result["clip_settings"] = copy.deepcopy(self.clip_styles)
        result["custom_intros"] = custom_intros
        result["custom_outros"] = custom_outros
        return result

    def closeEvent(self, event):
        settings = self.get_settings()
        self.settings_saved.emit(settings)
        super().closeEvent(event)

    def accept(self):
        settings = self.get_settings()
        self.settings_saved.emit(settings)
        super().accept()
