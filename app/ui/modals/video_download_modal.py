"""AI Short Generator 1.0 - Video Download & Ingestion Modal (YouTube Resilient & Local Drag & Drop)"""

import re
import threading
from pathlib import Path
from typing import Optional, List
from PySide6.QtWidgets import (
    QDialog, QVBoxLayout, QHBoxLayout, QLabel, QTextEdit, QComboBox,
    QPushButton, QFrame, QFileDialog, QListWidget, QListWidgetItem,
    QProgressBar, QMessageBox, QWidget
)
from PySide6.QtCore import Qt, Signal, QObject
from app.config import CATEGORIES
from app.core.continuous_video_manager import ContinuousVideoPoolManager


def _format_bytes(b: float) -> str:
    """Formatta dimensione in MiB, GiB o KiB."""
    if not b or b <= 0:
        return "0B"
    if b >= 1024 * 1024 * 1024:
        return f"{b / (1024**3):.2f}GiB"
    elif b >= 1024 * 1024:
        return f"{b / (1024**2):.2f}MiB"
    elif b >= 1024:
        return f"{b / 1024:.2f}KiB"
    return f"{int(b)}B"


def _format_seconds(s: Optional[float]) -> str:
    """Formatta secondi in HH:MM:SS o MM:SS."""
    if s is None or s < 0:
        return "--:--"
    tot = int(s)
    h, rem = divmod(tot, 3600)
    m, sec = divmod(rem, 60)
    if h > 0:
        return f"{h:02d}:{m:02d}:{sec:02d}"
    return f"{m:02d}:{sec:02d}"


class _WorkerSignals(QObject):
    progress_updated = Signal(float, str, str, str)  # percent, stats_text, eta_speed, title
    item_completed = Signal(str, str)                # title, info
    item_failed = Signal(str, str)                   # title, error
    all_finished = Signal()


class VideoDownloadModal(QDialog):
    """
    Finestra Modale Download Multi-Video YouTube & Importazione Locale Zero-Recode:
    - Autenticazione Cookie anti-bot (Firefox, Chrome, Edge, cookies.txt)
    - Monitor di download in tempo reale integrato nella GUI (non in console)
    - Auto-categorizzazione tematica
    - Ingestion a Ricodifica Zero (< 3s per video)
    """

    video_imported = Signal(int)

    def __init__(
        self,
        video_mgr: ContinuousVideoPoolManager,
        default_category: Optional[str] = None,
        parent: Optional[QWidget] = None
    ):
        super().__init__(parent)
        self.video_mgr = video_mgr
        self.default_category = default_category
        self.has_imported = False
        self.setWindowTitle("Download Multi-Video YouTube & Creazione Pool Continuo")
        self.resize(780, 620)
        self.setObjectName("ModalWindow")

        self.signals = _WorkerSignals()
        self.signals.progress_updated.connect(self._on_progress_updated)
        self.signals.item_completed.connect(self._on_item_completed)
        self.signals.item_failed.connect(self._on_item_failed)
        self.signals.all_finished.connect(self._on_all_finished)
        self._init_ui()

    def _init_ui(self):
        layout = QVBoxLayout(self)
        layout.setContentsMargins(18, 14, 18, 14)
        layout.setSpacing(10)

        # Header
        top_bar = QHBoxLayout()
        header_lbl = QLabel("DOWNLOAD MULTI-VIDEO YOUTUBE & CREAZIONE POOL CONTINUO")
        header_lbl.setObjectName("SectionHeader")
        top_bar.addWidget(header_lbl)
        top_bar.addStretch()

        btn_close = QPushButton("✕ Chiudi")
        btn_close.clicked.connect(self.close)
        top_bar.addWidget(btn_close)
        layout.addLayout(top_bar)

        # Cookie anti-bot
        cookie_box = QFrame()
        cookie_box.setObjectName("InnerCard")
        cb_layout = QHBoxLayout(cookie_box)
        cb_layout.setContentsMargins(8, 6, 8, 6)
        cb_layout.addWidget(QLabel("Sorgente Cookie Anti-Bot:"))
        self.combo_browser = QComboBox()
        self.combo_browser.addItems(["firefox (Consigliato)", "chrome", "edge", "brave", "cookies.txt"])
        cb_layout.addWidget(self.combo_browser)

        self.btn_browse_cookies = QPushButton("📁 Importa cookies.txt")
        self.btn_browse_cookies.clicked.connect(self._browse_cookies_file)
        cb_layout.addWidget(self.btn_browse_cookies)
        cb_layout.addStretch()
        layout.addWidget(cookie_box)

        # URLs text edit
        layout.addWidget(QLabel("Incolla uno o più link di YouTube (uno per riga):"))
        self.txt_urls = QTextEdit()
        self.txt_urls.setPlaceholderText("https://www.youtube.com/watch?v=...\nhttps://www.youtube.com/watch?v=...")
        self.txt_urls.setFixedHeight(80)
        layout.addWidget(self.txt_urls)

        # Categoria & Azioni di Aggiunta
        act_row = QHBoxLayout()
        act_row.addWidget(QLabel("Categoria:"))
        self.combo_cat = QComboBox()
        self.combo_cat.addItem("🤖 Auto-Rileva Categoria")
        self.combo_cat.addItems(CATEGORIES)
        if self.default_category and self.default_category in CATEGORIES:
            self.combo_cat.setCurrentText(self.default_category)
        act_row.addWidget(self.combo_cat, stretch=1)

        self.btn_add_urls = QPushButton("+ Scarica da YouTube")
        self.btn_add_urls.setObjectName("PrimaryButton")
        self.btn_add_urls.clicked.connect(self._start_download_urls)
        act_row.addWidget(self.btn_add_urls)

        self.btn_local_file = QPushButton("📁 Importa File Locale")
        self.btn_local_file.clicked.connect(self._import_local_files)
        act_row.addWidget(self.btn_local_file)
        layout.addLayout(act_row)

        self.txt_urls.setFocus()

        # Monitor Download & Avanzamento in Tempo Reale (Soft Dark UI)
        self.monitor_card = QFrame()
        self.monitor_card.setObjectName("InnerCard")
        mon_layout = QVBoxLayout(self.monitor_card)
        mon_layout.setContentsMargins(12, 10, 12, 10)
        mon_layout.setSpacing(6)

        # Titolo corrente / Pill percentuale
        title_row = QHBoxLayout()
        self.lbl_current_title = QLabel("Stato: Pronto al download")
        self.lbl_current_title.setStyleSheet("font-weight: 600; color: #DCE0EA; font-size: 13px;")
        title_row.addWidget(self.lbl_current_title, stretch=1)

        self.lbl_percent_pill = QLabel("0%")
        self.lbl_percent_pill.setStyleSheet("""
            background-color: #2D323E;
            color: #6B82A6;
            padding: 2px 8px;
            border-radius: 4px;
            font-weight: 600;
            font-size: 11px;
        """)
        title_row.addWidget(self.lbl_percent_pill)
        mon_layout.addLayout(title_row)

        # Barra di progresso sottile moderna
        self.progress_bar = QProgressBar()
        self.progress_bar.setRange(0, 100)
        self.progress_bar.setValue(0)
        self.progress_bar.setTextVisible(False)
        self.progress_bar.setFixedHeight(8)
        self.progress_bar.setStyleSheet("""
            QProgressBar {
                background-color: #181A20;
                border: 1px solid #343946;
                border-radius: 4px;
            }
            QProgressBar::chunk {
                background-color: #6B82A6;
                border-radius: 3px;
            }
        """)
        mon_layout.addWidget(self.progress_bar)

        # Riga Dettagli Metriche [download] 100% of 2.25MiB at 3.53MiB/s
        stats_row = QHBoxLayout()
        self.lbl_download_stats = QLabel("[download] In attesa di avvio...")
        self.lbl_download_stats.setStyleSheet("""
            font-family: 'Consolas', 'Courier New', monospace;
            color: #949CAE;
            font-size: 11px;
        """)
        stats_row.addWidget(self.lbl_download_stats, stretch=1)

        self.lbl_eta_speed = QLabel("")
        self.lbl_eta_speed.setStyleSheet("""
            font-family: 'Consolas', 'Courier New', monospace;
            color: #6B82A6;
            font-size: 11px;
        """)
        stats_row.addWidget(self.lbl_eta_speed)
        mon_layout.addLayout(stats_row)

        layout.addWidget(self.monitor_card)

        # Storico Ingestion
        layout.addWidget(QLabel("STORICO OPERAZIONI POOL CONTINUO:"))
        self.list_queue = QListWidget()
        layout.addWidget(self.list_queue, stretch=1)

        # Banner regole tecniche
        rule_box = QFrame()
        rule_box.setObjectName("InnerCard")
        rb_layout = QVBoxLayout(rule_box)
        rb_layout.setContentsMargins(8, 6, 8, 6)
        r1 = QLabel("✓ Zero-Recode Ingestion: Il master rimane intatto su disco; l'import impiega < 3 secondi.")
        r1.setObjectName("HelperText")
        r2 = QLabel("✓ Continuità per Categoria: Lo Short può combinare più video della stessa categoria tematica.")
        r2.setObjectName("HelperText")
        rb_layout.addWidget(r1)
        rb_layout.addWidget(r2)
        layout.addWidget(rule_box)

    def _browse_cookies_file(self):
        f, _ = QFileDialog.getOpenFileName(self, "Seleziona file cookies.txt", "", "Text Files (*.txt);;All Files (*)")
        if f:
            self.cookies_file_path = f
            self.combo_browser.setCurrentText("cookies.txt")
            QMessageBox.information(self, "Cookie Impostati", f"File cookie selezionato: {f}")

    def _import_local_files(self):
        files, _ = QFileDialog.getOpenFileNames(
            self, "Seleziona Video Locali", "", "Video Files (*.mp4 *.mkv *.mov *.webm);;All Files (*)"
        )
        if not files:
            return

        cat_choice = self.combo_cat.currentText()
        cat_override = None if "Auto" in cat_choice else cat_choice

        for f_path in files:
            try:
                src_id = self.video_mgr.import_local_video(f_path, category_override=cat_override)
                p = Path(f_path)
                item = QListWidgetItem(f"🟢 Ingestion Completata (< 3s): {p.stem} (ID: #{src_id})")
                self.has_imported = True
                self.list_queue.addItem(item)
                self.video_imported.emit(src_id)
            except Exception as e:
                item = QListWidgetItem(f"❌ Errore Import {Path(f_path).name}: {e}")
                self.list_queue.addItem(item)

    def _start_download_urls(self):
        urls = [u.strip() for u in self.txt_urls.toPlainText().splitlines() if u.strip()]
        if not urls:
            QMessageBox.warning(self, "Attenzione", "Incolla almeno un link YouTube valido.")
            return

        browser_choice = self.combo_browser.currentText().split(" ")[0]
        cat_choice = self.combo_cat.currentText()
        cat_override = None if "Auto" in cat_choice else cat_choice
        cookies_file = getattr(self, "cookies_file_path", None)

        self.btn_add_urls.setEnabled(False)
        self.btn_local_file.setEnabled(False)

        # Reset Monitor UI
        self.progress_bar.setValue(0)
        self.lbl_percent_pill.setText("0%")
        self.lbl_percent_pill.setStyleSheet("""
            background-color: #2D323E;
            color: #6B82A6;
            padding: 2px 8px;
            border-radius: 4px;
            font-weight: 600;
            font-size: 11px;
        """)
        self.lbl_current_title.setText("⏳ Connessione a YouTube in corso...")
        self.lbl_download_stats.setText("[download] Inizializzazione stream video...")
        self.lbl_eta_speed.setText("")

        def _worker():
            for u in urls:
                current_title = ["Download in corso..."]

                def _on_yt_dlp_progress(d: dict):
                    status = d.get('status', '')
                    if status == 'downloading':
                        downloaded = d.get('downloaded_bytes', 0)
                        total = d.get('total_bytes') or d.get('total_bytes_estimate') or 0
                        speed = d.get('speed') or 0.0
                        eta = d.get('eta')
                        elapsed = d.get('elapsed') or 0.0

                        percent = (downloaded / total * 100.0) if total > 0 else 0.0
                        if d.get('_percent_str'):
                            clean_pct = re.sub(r'\x1b\[[0-9;]*m', '', str(d.get('_percent_str'))).strip().replace('%', '')
                            try:
                                percent = float(clean_pct)
                            except ValueError:
                                pass

                        title = d.get('info_dict', {}).get('title')
                        if title:
                            current_title[0] = title

                        total_str = d.get('_total_bytes_str')
                        if not total_str or '\x1b' in total_str:
                            total_str = _format_bytes(total) if total > 0 else "N/A"
                        else:
                            total_str = re.sub(r'\x1b\[[0-9;]*m', '', total_str).strip()

                        speed_str = d.get('_speed_str')
                        if not speed_str or '\x1b' in speed_str:
                            speed_str = f"{_format_bytes(speed)}/s" if speed > 0 else "N/A"
                        else:
                            speed_str = re.sub(r'\x1b\[[0-9;]*m', '', speed_str).strip()

                        eta_str = d.get('_eta_str')
                        if not eta_str or '\x1b' in eta_str:
                            eta_str = _format_seconds(eta) if (eta is not None and eta >= 0) else "--:--"
                        else:
                            eta_str = re.sub(r'\x1b\[[0-9;]*m', '', eta_str).strip()

                        stats_text = f"[download] {percent:5.1f}% of {total_str} at {speed_str} (ETA: {eta_str})"
                        eta_speed = f"{speed_str} | ETA: {eta_str}"
                        self.signals.progress_updated.emit(percent, stats_text, eta_speed, current_title[0])

                    elif status == 'finished':
                        total = d.get('total_bytes') or d.get('downloaded_bytes') or 0
                        elapsed = d.get('elapsed') or 0.0
                        elapsed_str = _format_seconds(elapsed)
                        total_str = _format_bytes(total)
                        speed = d.get('speed') or 0.0
                        speed_str = f"{_format_bytes(speed)}/s" if speed > 0 else ""

                        stats_text = f"[download] 100% of {total_str} in {elapsed_str}" + (f" at {speed_str}" if speed_str else "")
                        self.signals.progress_updated.emit(100.0, stats_text, "100%", current_title[0])

                    elif status == 'postprocessing':
                        msg = d.get('msg', 'Muxing MP4 (Zero-Recode)...')
                        self.signals.progress_updated.emit(100.0, f"[postprocessing] {msg}", "Zero-Recode", current_title[0])

                    elif status == 'ingestion':
                        msg = d.get('msg', 'Rilevamento confini di scena e catalogazione...')
                        self.signals.progress_updated.emit(100.0, f"[ingestion] {msg}", "Analisi", current_title[0])

                try:
                    src_id = self.video_mgr.download_youtube_video(
                        youtube_url=u,
                        preferred_browser=browser_choice,
                        cookies_file=cookies_file,
                        category_override=cat_override,
                        progress_callback=_on_yt_dlp_progress
                    )
                    self.signals.item_completed.emit(u, f"Master Intatto (ID: #{src_id})")
                except Exception as e:
                    self.signals.item_failed.emit(u, str(e))
            self.signals.all_finished.emit()

        threading.Thread(target=_worker, daemon=True).start()

    def _on_progress_updated(self, percent: float, stats_text: str, eta_speed_text: str, title: str):
        val = int(min(max(percent, 0.0), 100.0))
        self.progress_bar.setValue(val)
        self.lbl_percent_pill.setText(f"{val}%")
        self.lbl_download_stats.setText(stats_text)
        if eta_speed_text:
            self.lbl_eta_speed.setText(eta_speed_text)
        if title:
            clean_t = title.strip()
            if len(clean_t) > 60:
                clean_t = clean_t[:57] + "..."
            self.lbl_current_title.setText(f"📹 {clean_t}")

    def _on_item_completed(self, url: str, info: str):
        self.has_imported = True
        self.progress_bar.setValue(100)
        self.lbl_percent_pill.setText("100%")
        self.lbl_percent_pill.setStyleSheet("""
            background-color: #22382D;
            color: #729B84;
            padding: 2px 8px;
            border-radius: 4px;
            font-weight: 600;
            font-size: 11px;
        """)
        self.lbl_current_title.setText(f"✓ Completato: {info}")
        self.lbl_download_stats.setText("[completato] Master acquisito a ricodifica zero nel Pool Continuo.")
        self.lbl_eta_speed.setText("Pronto")
        self.list_queue.addItem(QListWidgetItem(f"🟢 {info}: {url}"))

    def _on_item_failed(self, url: str, err: str):
        self.progress_bar.setValue(0)
        self.lbl_percent_pill.setText("ERR")
        self.lbl_percent_pill.setStyleSheet("""
            background-color: #3D2525;
            color: #AA7373;
            padding: 2px 8px;
            border-radius: 4px;
            font-weight: 600;
            font-size: 11px;
        """)
        self.lbl_current_title.setText("❌ Download non riuscito")
        short_err = err.split("\n")[-1]
        if len(short_err) > 80:
            short_err = short_err[:77] + "..."
        self.lbl_download_stats.setText(f"[errore] {short_err}")
        self.lbl_eta_speed.setText("")
        self.list_queue.addItem(QListWidgetItem(f"❌ Fallito ({url}): {err}"))

    def _on_all_finished(self):
        self.btn_add_urls.setEnabled(True)
        self.btn_local_file.setEnabled(True)
        self.txt_urls.clear()
        QMessageBox.information(self, "Elaborazione Conclusa", "Download e catalogazione video completati nel Pool.")

    def close(self):
        if self.has_imported:
            self.accept()
        else:
            super().close()
