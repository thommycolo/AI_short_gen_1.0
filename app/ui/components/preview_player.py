"""AI Short Generator 1.0 - 9:16 Preview Player Component with Safe-Zones Overlay"""

from typing import Optional
from pathlib import Path
from PySide6.QtWidgets import (
    QFrame, QVBoxLayout, QHBoxLayout, QLabel, QPushButton, QSlider, QCheckBox, QWidget
)
from PySide6.QtCore import Qt, QTimer
from PySide6.QtGui import QPainter, QColor, QPen, QBrush, QPixmap, QFont


class PreviewPlayerWidget(QFrame):
    """Monitor 9:16 con overlay interattivo delle Safe-Zones per TikTok, Reels e Shorts."""

    def __init__(self, parent: Optional[QWidget] = None):
        super().__init__(parent)
        self.setObjectName("CardSurface")
        self.preview_pixmap: Optional[QPixmap] = None
        self.show_safe_zones: bool = True
        self.current_time_sec: float = 0.600
        self.total_duration_sec: float = 39.4
        self.is_playing: bool = False
        self._init_ui()

    def _init_ui(self):
        layout = QVBoxLayout(self)
        layout.setContentsMargins(12, 10, 12, 10)
        layout.setSpacing(6)

        # Header con toggle safe zones
        top_row = QHBoxLayout()
        header_lbl = QLabel("MONITOR ANTEPRIMA (1080x1920)")
        header_lbl.setObjectName("SectionHeader")

        self.cb_safe_zones = QCheckBox("Safe-Zone: ON")
        self.cb_safe_zones.setChecked(True)
        self.cb_safe_zones.toggled.connect(self._toggle_safe_zones)

        top_row.addWidget(header_lbl)
        top_row.addStretch()
        top_row.addWidget(self.cb_safe_zones)
        layout.addLayout(top_row)

        # Canvas 9:16 proporzionale (270x480)
        self.screen_frame = _VideoCanvas(self)
        layout.addWidget(self.screen_frame, alignment=Qt.AlignCenter)

        # Controlli player
        ctrl_row = QHBoxLayout()
        self.btn_play = QPushButton("▶ Play")
        self.btn_play.setFixedWidth(70)
        self.btn_play.clicked.connect(self._toggle_playback)

        self.slider = QSlider(Qt.Horizontal)
        self.slider.setRange(0, int(self.total_duration_sec * 10))
        self.slider.setValue(int(self.current_time_sec * 10))
        self.slider.valueChanged.connect(self._on_slider_changed)

        self.lbl_time = QLabel("00:00.6 / 00:39.4")
        self.lbl_time.setObjectName("HelperText")

        ctrl_row.addWidget(self.btn_play)
        ctrl_row.addWidget(self.slider, stretch=1)
        ctrl_row.addWidget(self.lbl_time)
        layout.addLayout(ctrl_row)

    def _toggle_safe_zones(self, checked: bool):
        self.show_safe_zones = checked
        self.screen_frame.update()

    def _toggle_playback(self):
        self.is_playing = not self.is_playing
        self.btn_play.setText("■ Stop" if self.is_playing else "▶ Play")

    def _on_slider_changed(self, val: int):
        self.current_time_sec = val / 10.0
        self.lbl_time.setText(f"00:{self.current_time_sec:04.1f} / 00:{self.total_duration_sec:04.1f}")
        self.screen_frame.update()

    def load_preview_image(self, image_path: str):
        if Path(image_path).exists():
            pix = QPixmap(image_path)
            if not pix.isNull():
                self.preview_pixmap = pix.scaled(270, 480, Qt.KeepAspectRatioByExpanding, Qt.SmoothTransformation)
                self.screen_frame.update()

    def set_duration(self, duration_sec: float):
        self.total_duration_sec = duration_sec
        self.slider.setRange(0, int(duration_sec * 10))
        self.lbl_time.setText(f"00:{self.current_time_sec:04.1f} / 00:{self.total_duration_sec:04.1f}")


class _VideoCanvas(QFrame):
    """Canvas interno 9:16 per il rendering del frame e delle guide."""

    def __init__(self, parent_player: PreviewPlayerWidget):
        super().__init__()
        self.parent_player = parent_player
        self.setFixedSize(270, 480)
        self.setStyleSheet("background-color: #121418; border-radius: 8px; border: 1px solid #343946;")

    def paintEvent(self, event):
        super().paintEvent(event)
        painter = QPainter(self)
        painter.setRenderHint(QPainter.Antialiasing)

        # 1. Immagine di sfondo (se presente)
        if self.parent_player.preview_pixmap:
            painter.drawPixmap(0, 0, self.parent_player.preview_pixmap)
        else:
            # Sfondo gradiente neutro con demo text
            painter.setBrush(QColor("#1A1C22"))
            painter.setPen(Qt.NoPen)
            painter.drawRoundedRect(0, 0, 270, 480, 8, 8)

        # 2. Intro Banner (se t <= 1.5s)
        if self.parent_player.current_time_sec <= 1.5:
            painter.setFont(QFont("Montserrat Black", 12, QFont.Bold))
            painter.setPen(QColor("#FFFFFF"))
            painter.drawText(0, 180, 270, 30, Qt.AlignCenter, "STORY DEMO part.1")

        # 3. Sottotitoli Safe Zone (testo uniforme, nessuna parola evidenziata)
        if self.parent_player.current_time_sec >= 0.5:
            painter.setFont(QFont("Montserrat Black", 11, QFont.Bold))
            painter.setPen(QColor("#DCE0EA"))
            painter.drawText(0, 350, 270, 26, Qt.AlignCenter, "DISCOVER THIS STORY")

        # 4. Safe Zones Guides Overlay (TikTok / Reels / Shorts)
        if self.parent_player.show_safe_zones:
            pen = QPen(QColor(107, 130, 166, 120), 1, Qt.DashLine)
            painter.setPen(pen)
            # Top safe line (~140px out of 1920 -> 35px)
            painter.drawLine(0, 35, 270, 35)
            # Bottom safe line (social UI ~360px out of 1920 -> 90px from bottom -> 390px)
            painter.drawLine(0, 390, 270, 390)
            # Left & Right safe margins (100px on 1080 -> 25px)
            painter.drawLine(25, 35, 25, 390)
            painter.drawLine(245, 35, 245, 390)

            # Badge overlay
            painter.setFont(QFont("Segoe UI", 8))
            painter.setPen(QColor(148, 156, 174, 180))
            painter.drawText(30, 48, "SAFE AREA (9:16)")
            painter.drawText(30, 420, "TIKTOK / REELS UI")

