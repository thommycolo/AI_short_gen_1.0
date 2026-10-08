"""AI Short Generator 1.0 - Subtitle Drawer (Designer Sottotitoli & Safe-Zone Studio)"""

import os
import shutil
import subprocess
from typing import Optional, Dict, Any, List
from pathlib import Path

from PySide6.QtWidgets import (
    QDialog, QVBoxLayout, QHBoxLayout, QLabel, QPushButton, QFrame,
    QScrollArea, QWidget, QSlider, QCheckBox, QComboBox, QRadioButton,
    QButtonGroup, QInputDialog, QMessageBox, QFileDialog, QColorDialog
)
from PySide6.QtCore import Qt, Signal
from PySide6.QtGui import (
    QPixmap, QPainter, QColor, QFont, QPen, QBrush, QFontDatabase,
    QPainterPath, QLinearGradient
)

from app.config import (
    DEFAULT_FONT_NAME, DEFAULT_FONT_SIZE, DEFAULT_TEXT_COLOR,
    DEFAULT_HIGHLIGHT_COLOR, DEFAULT_OUTLINE_COLOR, DEFAULT_OUTLINE_WIDTH,
    DEFAULT_SHADOW_RADIUS, DEFAULT_MARGIN_V, SUBTITLE_SAFE_WIDTH_PX,
    FONTS_DIR, VIDEO_POOL_DIR, CACHE_DIR
)
from app.core.preset_manager import PresetManager
from app.utils.ffmpeg_installer import find_system_ffmpeg
from app.utils.logger import log


class SubtitleCanvasWidget(QWidget):
    """Monitor 9:16 (270x480) con rendering del frame di sfondo reale e anteprima sottotitolo."""

    def __init__(self, parent: Optional[QWidget] = None):
        super().__init__(parent)
        self.setFixedSize(270, 480)
        self.background_pixmap: Optional[QPixmap] = None

        # Style attributes
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

        # Overlays
        self.show_safe_zones = True
        self.show_intro_banner = False

    def set_background_image(self, image_path: str):
        if image_path and os.path.exists(image_path):
            pix = QPixmap(image_path)
            if not pix.isNull():
                self.background_pixmap = pix.scaled(270, 480, Qt.KeepAspectRatioByExpanding, Qt.SmoothTransformation)
            else:
                self.background_pixmap = None
        else:
            self.background_pixmap = None
        self.update()

    def update_style(self, style_dict: dict):
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

    def paintEvent(self, event):
        painter = QPainter(self)
        painter.setRenderHint(QPainter.Antialiasing)
        painter.setRenderHint(QPainter.TextAntialiasing)

        # 1. Background image or professional 9:16 template mockup
        if self.background_pixmap:
            painter.drawPixmap(0, 0, self.background_pixmap)
        else:
            # Sfondo gradiente cinematico verticale
            grad = QLinearGradient(0, 0, 0, 480)
            grad.setColorAt(0.0, QColor("#1D212A"))
            grad.setColorAt(0.5, QColor("#13161C"))
            grad.setColorAt(1.0, QColor("#0D0E12"))
            painter.fillRect(0, 0, 270, 480, grad)

            # Griglia sottile template
            painter.setPen(QColor(42, 50, 69, 120))
            painter.drawRect(0, 0, 269, 479)
            painter.drawLine(90, 0, 90, 480)
            painter.drawLine(180, 0, 180, 480)
            painter.drawLine(0, 160, 270, 160)
            painter.drawLine(0, 320, 270, 320)

            # Badge centrale template
            painter.setPen(QColor("#6B82A6"))
            painter.setFont(QFont("Segoe UI", 9, QFont.Bold))
            painter.drawText(0, 205, 270, 25, Qt.AlignCenter, "🎬 TEMPLATE VIDEO 9:16")
            painter.setFont(QFont("Segoe UI", 8))
            painter.setPen(QColor("#555E75"))
            painter.drawText(0, 230, 270, 20, Qt.AlignCenter, "[ 1080 x 1920 Full HD ]")

        # 2. Safe-Zone Overlays (TikTok, Reels, Shorts)
        if self.show_safe_zones:
            # Top Search Safe Zone (140px out of 1920 -> 35px)
            top_h = int(140 * (480 / 1920.0))
            painter.fillRect(0, 0, 270, top_h, QColor(107, 130, 166, 60))
            painter.setPen(QPen(QColor(107, 130, 166, 180), 1, Qt.DashLine))
            painter.drawLine(0, top_h, 270, top_h)
            painter.setFont(QFont("Segoe UI", 8, QFont.Bold))
            painter.setPen(QColor(160, 185, 220, 230))
            painter.drawText(8, top_h - 10, "TOP SAFE-ZONE (140px)")

            # Bottom UI Safe Zone (360px out of 1920 -> 90px)
            bot_h = int(360 * (480 / 1920.0))
            bot_y = 480 - bot_h
            painter.fillRect(0, bot_y, 270, bot_h, QColor(170, 115, 115, 60))
            painter.setPen(QPen(QColor(170, 115, 115, 200), 1, Qt.DashLine))
            painter.drawLine(0, bot_y, 270, bot_y)
            painter.setFont(QFont("Segoe UI", 8, QFont.Bold))
            painter.setPen(QColor(240, 170, 170, 230))
            painter.drawText(8, bot_y + 22, "BOTTOM SOCIAL UI (360px)")

            # Right zone (like / comment buttons ~26px)
            side_w = 26
            painter.fillRect(270 - side_w, top_h, side_w, bot_y - top_h, QColor(170, 115, 115, 35))
            painter.drawLine(270 - side_w, top_h, 270 - side_w, bot_y)

        # 3. Intro Title Banner (al centro)
        if self.show_intro_banner:
            banner_font_size = max(9, int(self.font_size * 0.28))
            banner_font = QFont(self.font_family, banner_font_size, QFont.Bold)
            painter.setFont(banner_font)
            banner_text = "Space_BlackHoles part.1"
            if self.is_all_caps:
                banner_text = banner_text.upper()

            metrics = painter.fontMetrics()
            t_w = metrics.horizontalAdvance(banner_text) + 24
            t_h = metrics.height() + 10
            p_x = int((270 - t_w) / 2)
            p_y = 195
            painter.setBrush(QColor(20, 23, 30, 220))
            painter.setPen(QPen(QColor(107, 130, 166, 220), 1.5))
            painter.drawRoundedRect(p_x, p_y, t_w, t_h, 6, 6)
            painter.setPen(QColor("#FFFFFF"))
            painter.drawText(0, p_y, 270, t_h, Qt.AlignCenter, banner_text)

        # 4. Subtitle Dynamic Text Rendering
        scale_ratio = 480.0 / 1920.0
        scaled_font_size = max(10, int(self.font_size * scale_ratio * 1.35))
        sub_font = QFont(self.font_family, scaled_font_size, QFont.Black if "black" in self.font_family.lower() else QFont.Bold)
        painter.setFont(sub_font)

        # Calcolo Y da 1920 - margin_v scalato a 480
        y_pos = int((1920 - self.margin_v) * scale_ratio)
        y_pos = max(35, min(455, y_pos))

        w1 = "BLACK HOLES ARE"
        w2 = "MOST MYSTERIOUS"
        if not self.is_all_caps:
            w1 = "Black holes are"
            w2 = "most mysterious"

        # Disegno professionale con outline e riempimento colore scelto
        path1 = QPainterPath()
        path2 = QPainterPath()

        metrics = painter.fontMetrics()
        w1_w = metrics.horizontalAdvance(w1)
        w2_w = metrics.horizontalAdvance(w2)
        x1 = int((270 - w1_w) / 2)
        x2 = int((270 - w2_w) / 2)

        b1_y = max(25, y_pos - 22)
        b2_y = max(45, y_pos)

        path1.addText(x1, b1_y, sub_font, w1)
        path2.addText(x2, b2_y, sub_font, w2)

        # Ombra
        if self.shadow_radius > 0:
            shadow_path1 = QPainterPath()
            shadow_path2 = QPainterPath()
            s_off = max(1, int(self.shadow_radius * 0.4))
            shadow_path1.addText(x1 + s_off, b1_y + s_off, sub_font, w1)
            shadow_path2.addText(x2 + s_off, b2_y + s_off, sub_font, w2)
            painter.fillPath(shadow_path1, QBrush(QColor(0, 0, 0, 160)))
            painter.fillPath(shadow_path2, QBrush(QColor(0, 0, 0, 160)))

        # Bordo / Outline
        if self.outline_width > 0:
            pen = QPen(QColor(self.color_outline), max(1.5, self.outline_width * 0.45))
            pen.setJoinStyle(Qt.RoundJoin)
            painter.strokePath(path1, pen)
            painter.strokePath(path2, pen)

        # Riempimento con colore del font scelto
        painter.fillPath(path1, QBrush(QColor(self.color_base)))
        painter.fillPath(path2, QBrush(QColor(self.color_base)))


class SubtitleDrawer(QDialog):
    """
    Drawer 3: Subtitle Designer, Anteprima Visiva Live (9:16) & Preset Tipografici.
    Auto-Save on Close: ON.
    """

    settings_saved = Signal(dict)
    apply_to_all_requested = Signal(dict)

    def __init__(
        self,
        preset_manager: Optional[PresetManager] = None,
        current_settings: Optional[dict] = None,
        video_frame_path: Optional[str] = None,
        video_pool_mgr: Optional[Any] = None,
        parent: Optional[QWidget] = None
    ):
        super().__init__(parent)
        self.preset_manager = preset_manager or PresetManager()
        self.current_settings = current_settings or {}
        self.video_pool_mgr = video_pool_mgr
        self.temp_frame_path = video_frame_path or ""

        self.setWindowTitle("DESIGNER SOTTOTITOLI & SAFE-ZONE STUDIO")
        self.resize(860, 720)
        self.setObjectName("DrawerWindow")

        self._init_ui()
        self._load_available_fonts()
        self._load_presets_combo()
        self._apply_initial_settings()
        self._auto_detect_video_frame()

    def _init_ui(self):
        main_layout = QVBoxLayout(self)
        main_layout.setContentsMargins(18, 14, 18, 14)
        main_layout.setSpacing(10)

        # Header
        header_bar = QHBoxLayout()
        lbl_title = QLabel("DESIGNER SOTTOTITOLI & SAFE-ZONE STUDIO")
        lbl_title.setStyleSheet("font-size: 15px; font-weight: 700; color: #DCE0EA;")
        header_bar.addWidget(lbl_title)
        header_bar.addStretch()

        lbl_autosave = QLabel("Auto-Save on Close: ON 🟢")
        lbl_autosave.setStyleSheet("font-size: 11px; font-weight: 600; color: #729B84; background-color: #21242C; padding: 4px 8px; border-radius: 4px; border: 1px solid #343946;")
        header_bar.addWidget(lbl_autosave)
        main_layout.addLayout(header_bar)

        # Preset Row
        preset_row = QHBoxLayout()
        lbl_p = QLabel("Preset Font Attivo:")
        lbl_p.setStyleSheet("color: #949CAE; font-weight: 600;")
        self.cmb_presets = QComboBox()
        self.cmb_presets.setMinimumWidth(220)
        self.cmb_presets.currentIndexChanged.connect(self._on_preset_selected)

        self.btn_save_preset = QPushButton("💾 Salva Nuovo Preset")
        self.btn_save_preset.clicked.connect(self._save_new_preset)

        self.btn_apply_all = QPushButton("🔗 Applica Questo Font a Tutte le Storie in Coda")
        self.btn_apply_all.clicked.connect(self._on_apply_to_all)

        preset_row.addWidget(lbl_p)
        preset_row.addWidget(self.cmb_presets)
        preset_row.addWidget(self.btn_save_preset)
        preset_row.addStretch()
        preset_row.addWidget(self.btn_apply_all)
        main_layout.addLayout(preset_row)

        # Split 2 Colonne: Sinistra Controlli, Destra Anteprima 9:16
        body_layout = QHBoxLayout()
        body_layout.setSpacing(16)

        # COLONNA SINISTRA: IMPOSTAZIONI GRAFICHE
        left_scroll = QScrollArea()
        left_scroll.setWidgetResizable(True)
        left_container = QWidget()
        left_layout = QVBoxLayout(left_container)
        left_layout.setSpacing(12)

        # Card 1: Animazione
        c_anim = QFrame()
        c_anim.setObjectName("CardSurface")
        l_anim = QVBoxLayout(c_anim)
        lbl_anim_t = QLabel("STILE ANIMAZIONE DINAMICA:")
        lbl_anim_t.setStyleSheet("font-size: 12px; font-weight: 700; color: #6B82A6;")
        l_anim.addWidget(lbl_anim_t)

        self.btn_grp_anim = QButtonGroup(self)
        self.rb_pop = QRadioButton("Word Pop (Parola per parola sincronizzata)")
        self.rb_karaoke = QRadioButton("Karaoke Lineare (Evidenziazione su riga)")
        self.rb_bounce = QRadioButton("Due Parole a Rimbalzo (Bounce Chunk)")
        self.rb_pop.setChecked(True)
        self.btn_grp_anim.addButton(self.rb_pop, 1)
        self.btn_grp_anim.addButton(self.rb_karaoke, 2)
        self.btn_grp_anim.addButton(self.rb_bounce, 3)
        self.btn_grp_anim.buttonClicked.connect(self._on_control_changed)

        l_anim.addWidget(self.rb_pop)
        l_anim.addWidget(self.rb_karaoke)
        l_anim.addWidget(self.rb_bounce)
        left_layout.addWidget(c_anim)

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
        self.sld_size.setRange(50, 85)
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

        left_layout.addWidget(c_font)

        # Card 3: Palette Colori & Personalizzazione
        c_col = QFrame()
        c_col.setObjectName("CardSurface")
        l_col = QVBoxLayout(c_col)
        lbl_col_t = QLabel("PALETTE COLORI & PERSONALIZZAZIONE:")
        lbl_col_t.setStyleSheet("font-size: 12px; font-weight: 700; color: #6B82A6;")
        l_col.addWidget(lbl_col_t)

        row_cbase = QHBoxLayout()
        lbl_cbase = QLabel("Colore del Font:")
        lbl_cbase.setFixedWidth(120)
        self.cmb_color_base = QComboBox()
        self.color_presets = [
            ("#FFFFFF", "Bianco Puro"),
            ("#FFFF00", "Giallo Viral"),
            ("#FFD700", "Oro Caldo"),
            ("#00FFCC", "Ciano Neon"),
            ("#00FF66", "Verde Lime"),
            ("#FF3366", "Rosso Corallo"),
            ("#FF9900", "Arancio Caldo"),
            ("#DCE0EA", "Perla Morbido"),
            ("#E0E3EA", "Cenere"),
            ("#BFA175", "Sabbia / Bronzo"),
        ]
        for hex_code, name in self.color_presets:
            self.cmb_color_base.addItem(f"{hex_code} ({name})", hex_code)

        self.cmb_color_base.currentIndexChanged.connect(self._on_color_combo_changed)

        self.lbl_color_preview = QLabel()
        self.lbl_color_preview.setFixedSize(26, 26)
        self.lbl_color_preview.setStyleSheet(f"background-color: {DEFAULT_TEXT_COLOR}; border: 1px solid #555E75; border-radius: 4px;")

        self.btn_pick_color = QPushButton("🎨 Scegli Colore...")
        self.btn_pick_color.setStyleSheet("padding: 4px 10px; font-size: 11px;")
        self.btn_pick_color.clicked.connect(self._on_pick_custom_color)

        row_cbase.addWidget(lbl_cbase)
        row_cbase.addWidget(self.cmb_color_base, stretch=1)
        row_cbase.addWidget(self.lbl_color_preview)
        row_cbase.addWidget(self.btn_pick_color)
        l_col.addLayout(row_cbase)

        self.cmb_color_high = QComboBox()
        self.cmb_color_high.addItem("#DCE0EA")

        row_edge = QHBoxLayout()
        lbl_edge = QLabel("Spessore Bordo:")
        lbl_edge.setFixedWidth(120)
        self.sld_edge = QSlider(Qt.Horizontal)
        self.sld_edge.setRange(2, 10)
        self.sld_edge.setValue(DEFAULT_OUTLINE_WIDTH)
        self.lbl_val_edge = QLabel(f"{DEFAULT_OUTLINE_WIDTH} px")
        self.lbl_val_edge.setFixedWidth(45)
        self.sld_edge.valueChanged.connect(lambda v: (self.lbl_val_edge.setText(f"{v} px"), self._on_control_changed()))
        row_edge.addWidget(lbl_edge)
        row_edge.addWidget(self.sld_edge)
        row_edge.addWidget(self.lbl_val_edge)
        l_col.addLayout(row_edge)

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

        left_layout.addWidget(c_col)

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
        self.sld_y.setRange(50, 2000)
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

        self.chk_banner = QCheckBox("Mostra Intro Title Banner (0.0s - 1.5s Centro)")
        self.chk_banner.setChecked(False)
        self.chk_banner.toggled.connect(self._on_toggle_banner)
        l_pos.addWidget(self.chk_banner)

        left_layout.addWidget(c_pos)

        left_scroll.setWidget(left_container)
        body_layout.addWidget(left_scroll, stretch=5)

        # COLONNA DESTRA: ANTEPRIMA VISIVA LIVE (9:16)
        right_panel = QFrame()
        right_panel.setObjectName("CardSurface")
        right_layout = QVBoxLayout(right_panel)
        right_layout.setContentsMargins(10, 8, 10, 8)
        right_layout.setSpacing(8)

        lbl_r_title = QLabel("ANTEPRIMA VISIVA LIVE (9:16)")
        lbl_r_title.setStyleSheet("font-size: 12px; font-weight: 700; color: #6B82A6;")
        right_layout.addWidget(lbl_r_title)

        # Canvas Monitor
        self.canvas = SubtitleCanvasWidget()
        right_layout.addWidget(self.canvas, alignment=Qt.AlignCenter)

        # Controls below canvas
        row_scrub = QHBoxLayout()
        self.lbl_scrub = QLabel("Scrub: 02.5s / 10.0s")
        self.lbl_scrub.setStyleSheet("color: #949CAE; font-size: 11px;")
        self.sld_scrub = QSlider(Qt.Horizontal)
        self.sld_scrub.setRange(0, 100)
        self.sld_scrub.setValue(25) # 2.5s
        self.sld_scrub.valueChanged.connect(self._on_scrub_changed)
        row_scrub.addWidget(self.lbl_scrub)
        row_scrub.addWidget(self.sld_scrub)
        right_layout.addLayout(row_scrub)

        btn_bg_row = QHBoxLayout()
        self.btn_change_bg = QPushButton("🖼️ Cambia Fotogramma / Video Sfondo...")
        self.btn_change_bg.setStyleSheet("font-size: 11px; padding: 5px 12px;")
        self.btn_change_bg.clicked.connect(self._on_choose_custom_background)
        btn_bg_row.addWidget(self.btn_change_bg)
        right_layout.addLayout(btn_bg_row)

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

    def _on_control_changed(self):
        style = self.get_settings()
        self.canvas.update_style(style)

    def _on_toggle_safe_zones(self, checked: bool):
        self.canvas.show_safe_zones = bool(checked)
        self.canvas.update()

    def _on_toggle_banner(self, checked: bool):
        self.canvas.show_intro_banner = bool(checked)
        self.canvas.update()

    def _on_scrub_changed(self, val: int):
        sec = val / 10.0
        self.lbl_scrub.setText(f"Scrub: {sec:04.1f}s / 10.0s")

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
            found = False
            for i in range(self.cmb_color_base.count()):
                if self.cmb_color_base.itemText(i).startswith(chosen_hex):
                    self.cmb_color_base.setCurrentIndex(i)
                    found = True
                    break
            if not found:
                self.cmb_color_base.addItem(f"{chosen_hex} (Personalizzato)", chosen_hex)
                self.cmb_color_base.setCurrentIndex(self.cmb_color_base.count() - 1)
            self._update_color_preview(chosen_hex)
            self._on_control_changed()

    def _auto_detect_video_frame(self):
        """Cerca un video disponibile nel pool o su disco ed estrae automaticamente un fotogramma per il canvas."""
        if self.temp_frame_path and os.path.exists(self.temp_frame_path):
            self.canvas.set_background_image(self.temp_frame_path)
            return

        video_file = None
        if self.video_pool_mgr:
            try:
                sources = self.video_pool_mgr.get_all_sources()
                for s in sources:
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

        if video_file:
            out_frame = CACHE_DIR / "temp_subtitle_preview_bg.jpg"
            ffmpeg = find_system_ffmpeg()
            if isinstance(ffmpeg, tuple):
                ffmpeg = ffmpeg[0]
            if ffmpeg and os.path.exists(ffmpeg):
                cmd = [
                    ffmpeg, "-y",
                    "-ss", "2.0",
                    "-i", str(video_file),
                    "-vframes", "1",
                    "-q:v", "2",
                    str(out_frame)
                ]
                try:
                    subprocess.run(cmd, capture_output=True, timeout=10)
                    if out_frame.exists() and out_frame.stat().st_size > 500:
                        self.temp_frame_path = str(out_frame)
                        self.canvas.set_background_image(str(out_frame))
                except Exception as e:
                    log.warning(f"Errore auto estrazione fotogramma video: {e}")

    def _on_choose_custom_background(self):
        f_path, _ = QFileDialog.getOpenFileName(
            self,
            "Seleziona Immagine o Video per Sfondo Anteprima",
            "",
            "Media Files (*.jpg *.jpeg *.png *.mp4 *.mkv *.mov);;Video Files (*.mp4 *.mkv *.mov);;Immagini (*.jpg *.jpeg *.png)"
        )
        if not f_path:
            return

        path = Path(f_path)
        if path.suffix.lower() in [".jpg", ".jpeg", ".png"]:
            self.temp_frame_path = str(path)
            self.canvas.set_background_image(str(path))
        elif path.suffix.lower() in [".mp4", ".mkv", ".mov"]:
            out_frame = CACHE_DIR / f"custom_bg_frame_{path.stem}.jpg"
            ffmpeg = find_system_ffmpeg()
            if isinstance(ffmpeg, tuple):
                ffmpeg = ffmpeg[0]
            if ffmpeg and os.path.exists(ffmpeg):
                scrub_sec = self.sld_scrub.value() / 10.0
                cmd = [
                    ffmpeg, "-y",
                    "-ss", f"{scrub_sec:.2f}",
                    "-i", str(path),
                    "-vframes", "1",
                    "-q:v", "2",
                    str(out_frame)
                ]
                try:
                    subprocess.run(cmd, capture_output=True, timeout=10)
                    if out_frame.exists():
                        self.temp_frame_path = str(out_frame)
                        self.canvas.set_background_image(str(out_frame))
                except Exception as e:
                    QMessageBox.warning(self, "Errore", f"Impossibile estrarre frame dal video: {e}")

    def _load_presets_combo(self):
        presets = self.preset_manager.get_subtitle_presets()
        self.cmb_presets.clear()
        self.cmb_presets.addItem("Default (Viral Gold Pop)")
        for p in presets:
            self.cmb_presets.addItem(p["preset_name"], p)

    def _on_preset_selected(self, index: int):
        data = self.cmb_presets.currentData()
        if data:
            self._apply_preset_data(data)

    def _apply_preset_data(self, data: dict):
        idx = self.cmb_font.findText(data.get("font_name", DEFAULT_FONT_NAME))
        if idx >= 0:
            self.cmb_font.setCurrentIndex(idx)
        self.sld_size.setValue(int(data.get("font_size", DEFAULT_FONT_SIZE)))
        self.cmb_case.setCurrentIndex(0 if data.get("is_all_caps", 1) else 1)
        self.sld_edge.setValue(int(data.get("outline_width", DEFAULT_OUTLINE_WIDTH)))
        self.sld_shadow.setValue(int(data.get("shadow_radius", DEFAULT_SHADOW_RADIUS)))
        self.sld_y.setValue(int(data.get("margin_v", DEFAULT_MARGIN_V)))

        col = str(data.get("primary_color_hex", DEFAULT_TEXT_COLOR)).upper()
        found = False
        for i in range(self.cmb_color_base.count()):
            if self.cmb_color_base.itemText(i).startswith(col):
                self.cmb_color_base.setCurrentIndex(i)
                found = True
                break
        if not found:
            self.cmb_color_base.addItem(f"{col} (Personalizzato)", col)
            self.cmb_color_base.setCurrentIndex(self.cmb_color_base.count() - 1)
        self._update_color_preview(col)
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
        self.chk_banner.setChecked(False)
        self.canvas.show_safe_zones = True
        self.canvas.show_intro_banner = False
        self._on_control_changed()

    def _apply_initial_settings(self):
        if "font_name" in self.current_settings:
            idx = self.cmb_font.findText(self.current_settings["font_name"])
            if idx >= 0:
                self.cmb_font.setCurrentIndex(idx)
        if "font_size" in self.current_settings:
            self.sld_size.setValue(int(self.current_settings["font_size"]))
        if "margin_v" in self.current_settings:
            self.sld_y.setValue(int(self.current_settings["margin_v"]))
        if "primary_color_hex" in self.current_settings:
            col = str(self.current_settings["primary_color_hex"]).upper()
            found = False
            for i in range(self.cmb_color_base.count()):
                if self.cmb_color_base.itemText(i).startswith(col):
                    self.cmb_color_base.setCurrentIndex(i)
                    found = True
                    break
            if not found:
                self.cmb_color_base.addItem(f"{col} (Personalizzato)", col)
                self.cmb_color_base.setCurrentIndex(self.cmb_color_base.count() - 1)
            self._update_color_preview(col)
        self._on_control_changed()

    def get_settings(self) -> dict:
        anim = "WORD_POP"
        if self.rb_karaoke.isChecked():
            anim = "KARAOKE"
        elif self.rb_bounce.isChecked():
            anim = "BOUNCE"

        curr_txt = self.cmb_color_base.currentText()
        col_base_txt = curr_txt.split(" ")[0] if curr_txt else DEFAULT_TEXT_COLOR

        return {
            "animation_style": anim,
            "font_name": self.cmb_font.currentText(),
            "font_size": self.sld_size.value(),
            "is_all_caps": 1 if self.cmb_case.currentIndex() == 0 else 0,
            "primary_color_hex": col_base_txt,
            "highlight_color_hex": col_base_txt,
            "outline_color_hex": DEFAULT_OUTLINE_COLOR,
            "outline_width": self.sld_edge.value(),
            "shadow_radius": self.sld_shadow.value(),
            "margin_v": self.sld_y.value()
        }

    def _on_apply_to_all(self):
        settings = self.get_settings()
        self.apply_to_all_requested.emit(settings)
        QMessageBox.information(self, "Applicato a Tutte", "Lo stile sottotitoli è stato propagato a tutte le storie in coda.")

    def closeEvent(self, event):
        settings = self.get_settings()
        self.settings_saved.emit(settings)
        super().closeEvent(event)

    def accept(self):
        settings = self.get_settings()
        self.settings_saved.emit(settings)
        super().accept()

    def _load_available_fonts(self):
        self.cmb_font.blockSignals(True)
        self.cmb_font.clear()
        base_fonts = ["Montserrat Black", "Anton", "The Bold Font", "Poppins"]
        for bf in base_fonts:
            self.cmb_font.addItem(bf)

        fonts_dir = Path(FONTS_DIR)
        if fonts_dir.exists():
            for ext in ("*.ttf", "*.otf", "*.TTF", "*.OTF"):
                for font_path in fonts_dir.glob(ext):
                    font_id = QFontDatabase.addApplicationFont(str(font_path.resolve()))
                    if font_id != -1:
                        fams = QFontDatabase.applicationFontFamilies(font_id)
                        for fam in fams:
                            if self.cmb_font.findText(fam) == -1:
                                self.cmb_font.addItem(fam)
                    else:
                        stem_name = font_path.stem.replace("-", " ")
                        if self.cmb_font.findText(stem_name) == -1:
                            self.cmb_font.addItem(stem_name)

        self.cmb_font.blockSignals(False)
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
                        if self.cmb_font.findText(fam) == -1:
                            self.cmb_font.addItem(fam)
                        imported_names.append(fam)
                else:
                    stem_name = src.stem.replace("-", " ")
                    if self.cmb_font.findText(stem_name) == -1:
                        self.cmb_font.addItem(stem_name)
                    imported_names.append(stem_name)
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

