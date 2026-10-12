"""AI Short Generator 1.0 - Dedicated Video Playback Modal with QMediaPlayer & External Fallback"""

import os
import sys
import subprocess
from pathlib import Path
from typing import Optional

from PySide6.QtWidgets import (
    QDialog, QVBoxLayout, QHBoxLayout, QLabel, QPushButton,
    QSlider, QFrame, QWidget, QMessageBox
)
from PySide6.QtCore import Qt, QUrl
from PySide6.QtMultimedia import QMediaPlayer, QAudioOutput
from PySide6.QtMultimediaWidgets import QVideoWidget


def _format_time_ms(ms: int) -> str:
    tot_sec = max(0, int(ms // 1000))
    m, s = divmod(tot_sec, 60)
    h, m = divmod(m, 60)
    if h > 0:
        return f"{h:02d}:{m:02d}:{s:02d}"
    return f"{m:02d}:{s:02d}"


class VideoPlaybackModal(QDialog):
    """
    Finestra Modale di Riproduzione Video Background Pool:
    - Player video hardware integrato nativo PySide6 (QMediaPlayer + QVideoWidget)
    - Barra temporale di scrub / seek e controlli Play/Pausa/Stop
    - Fallback immediato su player di sistema (es. Windows Media Player, VLC)
    """

    def __init__(self, video_path: str, video_title: str = "Video Preview", parent: Optional[QWidget] = None):
        super().__init__(parent)
        self.video_path = str(Path(video_path).resolve())
        self.video_title = video_title

        self.setWindowTitle(f"Riproduzione Video — {self.video_title}")
        self.resize(760, 560)
        self.setObjectName("ModalWindow")

        self._is_seeking = False
        self._init_player()
        self._init_ui()

        # Carica il file video
        if os.path.exists(self.video_path):
            self.player.setSource(QUrl.fromLocalFile(self.video_path))
            self.player.play()
        else:
            QMessageBox.warning(self, "File non trovato", f"File video non trovato:\n{self.video_path}")

    def _init_player(self):
        self.player = QMediaPlayer(self)
        self.audio_output = QAudioOutput(self)
        self.player.setAudioOutput(self.audio_output)
        self.video_widget = QVideoWidget(self)
        self.player.setVideoOutput(self.video_widget)

        self.player.positionChanged.connect(self._on_position_changed)
        self.player.durationChanged.connect(self._on_duration_changed)
        self.player.playbackStateChanged.connect(self._on_playback_state_changed)
        self.player.errorOccurred.connect(self._on_player_error)

    def _init_ui(self):
        layout = QVBoxLayout(self)
        layout.setContentsMargins(16, 12, 16, 12)
        layout.setSpacing(8)

        # Header
        top_bar = QHBoxLayout()
        header_lbl = QLabel(f'🎬 RIPRODUZIONE: "{self.video_title}"')
        header_lbl.setObjectName("SectionHeader")
        top_bar.addWidget(header_lbl, stretch=1)

        btn_close = QPushButton("✕ Chiudi")
        btn_close.clicked.connect(self.close)
        top_bar.addWidget(btn_close)
        layout.addLayout(top_bar)

        # Video Frame Canvas
        canvas_box = QFrame()
        canvas_box.setObjectName("InnerCard")
        canvas_box.setStyleSheet("background-color: #0E1014; border-radius: 6px;")
        cb_layout = QVBoxLayout(canvas_box)
        cb_layout.setContentsMargins(4, 4, 4, 4)
        cb_layout.addWidget(self.video_widget)
        layout.addWidget(canvas_box, stretch=1)

        # Controlli di Riproduzione
        ctrl_card = QFrame()
        ctrl_card.setObjectName("InnerCard")
        ctrl_layout = QVBoxLayout(ctrl_card)
        ctrl_layout.setContentsMargins(10, 8, 10, 8)
        ctrl_layout.setSpacing(6)

        # Barra di scorrimento (Seek Slider)
        slider_row = QHBoxLayout()
        self.slider_pos = QSlider(Qt.Horizontal)
        self.slider_pos.setRange(0, 1000)
        self.slider_pos.sliderPressed.connect(self._on_slider_pressed)
        self.slider_pos.sliderReleased.connect(self._on_slider_released)
        self.slider_pos.sliderMoved.connect(self._on_slider_moved)

        self.lbl_time = QLabel("00:00 / 00:00")
        self.lbl_time.setObjectName("HelperText")
        self.lbl_time.setFixedWidth(110)
        self.lbl_time.setAlignment(Qt.AlignRight | Qt.AlignVCenter)

        slider_row.addWidget(self.slider_pos, stretch=1)
        slider_row.addWidget(self.lbl_time)
        ctrl_layout.addLayout(slider_row)

        # Pulsanti Play / Pausa / Volume / Player Esterno
        btn_row = QHBoxLayout()
        btn_row.setSpacing(8)

        self.btn_play = QPushButton("⏸ Pausa")
        self.btn_play.setFixedWidth(90)
        self.btn_play.setObjectName("PrimaryButton")
        self.btn_play.clicked.connect(self._toggle_play)
        btn_row.addWidget(self.btn_play)

        self.btn_stop = QPushButton("⏹ Stop")
        self.btn_stop.setFixedWidth(70)
        self.btn_stop.clicked.connect(self._stop_playback)
        btn_row.addWidget(self.btn_stop)

        # Volume
        btn_row.addSpacing(12)
        lbl_vol = QLabel("🔊")
        lbl_vol.setStyleSheet("font-size: 13px;")
        btn_row.addWidget(lbl_vol)

        self.slider_vol = QSlider(Qt.Horizontal)
        self.slider_vol.setRange(0, 100)
        self.slider_vol.setValue(70)
        self.slider_vol.setFixedWidth(90)
        self.audio_output.setVolume(0.70)
        self.slider_vol.valueChanged.connect(lambda v: self.audio_output.setVolume(v / 100.0))
        btn_row.addWidget(self.slider_vol)

        btn_row.addStretch()

        self.btn_external = QPushButton("🖥️ Apri con Player di Sistema")
        self.btn_external.setToolTip("Apre il file nel player multimediale predefinito di Windows/OS")
        self.btn_external.clicked.connect(self._open_external_player)
        btn_row.addWidget(self.btn_external)

        ctrl_layout.addLayout(btn_row)
        layout.addWidget(ctrl_card)

    def _toggle_play(self):
        state = self.player.playbackState()
        if state == QMediaPlayer.PlayingState:
            self.player.pause()
        else:
            self.player.play()

    def _stop_playback(self):
        self.player.stop()
        self.slider_pos.setValue(0)
        self.btn_play.setText("▶ Play")

    def _on_playback_state_changed(self, state):
        if state == QMediaPlayer.PlayingState:
            self.btn_play.setText("⏸ Pausa")
        else:
            self.btn_play.setText("▶ Play")

    def _on_position_changed(self, pos_ms: int):
        if not self._is_seeking:
            dur = self.player.duration()
            if dur > 0:
                val = int((pos_ms / dur) * 1000)
                self.slider_pos.setValue(val)
            self._update_time_label(pos_ms, dur)

    def _on_duration_changed(self, dur_ms: int):
        self._update_time_label(self.player.position(), dur_ms)

    def _update_time_label(self, pos_ms: int, dur_ms: int):
        self.lbl_time.setText(f"{_format_time_ms(pos_ms)} / {_format_time_ms(dur_ms)}")

    def _on_slider_pressed(self):
        self._is_seeking = True

    def _on_slider_released(self):
        self._is_seeking = False
        dur = self.player.duration()
        if dur > 0:
            pos = int((self.slider_pos.value() / 1000.0) * dur)
            self.player.setPosition(pos)

    def _on_slider_moved(self, val: int):
        dur = self.player.duration()
        if dur > 0:
            preview_pos = int((val / 1000.0) * dur)
            self._update_time_label(preview_pos, dur)

    def _open_external_player(self):
        if os.path.exists(self.video_path):
            if sys.platform == "win32":
                os.startfile(self.video_path)
            elif sys.platform == "darwin":
                subprocess.run(["open", self.video_path])
            else:
                subprocess.run(["xdg-open", self.video_path])

    def _on_player_error(self, error, error_string):
        if error != QMediaPlayer.NoError:
            # Fallback non bloccante: suggerisce player di sistema
            pass

    def closeEvent(self, event):
        self.player.stop()
        super().closeEvent(event)

    def keyPressEvent(self, event):
        if event.key() == Qt.Key_Space:
            self._toggle_play()
            event.accept()
        elif event.key() == Qt.Key_Escape:
            self.close()
            event.accept()
        else:
            super().keyPressEvent(event)

