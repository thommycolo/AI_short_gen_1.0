"""AI Short Generator 1.0 - Thematic Category Continuity Warning Dialog (Section 5.5)"""

from typing import Optional
from PySide6.QtWidgets import (
    QDialog, QVBoxLayout, QHBoxLayout, QLabel, QPushButton, QFrame, QWidget
)
from PySide6.QtCore import Qt


class CategoryContinuityWarningDialog(QDialog):
    """
    Dialog di Avviso: Risoluzione Continuità Tematica per Categoria/Gioco.
    Conforme al 100% a DESIGN_APP.md (Sezione 5.5):
    - Mostrato se l'utente tenta di produrre uno Short in una categoria priva di girato sufficiente.
    - Spiega la regola di continuità tematica.
    - Offre 3 opzioni: Cambia Categoria, Importa Locale, Scarica da YouTube.
    """

    ACTION_CHANGE_CATEGORY = "CHANGE_CATEGORY"
    ACTION_IMPORT_LOCAL = "IMPORT_LOCAL"
    ACTION_DOWNLOAD_YT = "DOWNLOAD_YT"

    def __init__(
        self,
        category: str,
        required_duration_sec: float,
        available_duration_sec: float,
        parent: Optional[QWidget] = None
    ):
        super().__init__(parent)
        self.category = category
        self.required_duration_sec = required_duration_sec
        self.available_duration_sec = available_duration_sec
        self.chosen_action: Optional[str] = None

        self.setWindowTitle("⚠️ Attenzione: Materiale Insufficiente per Categoria")
        self.resize(640, 360)
        self.setObjectName("ModalWindow")
        self._init_ui()

    def _init_ui(self):
        layout = QVBoxLayout(self)
        layout.setContentsMargins(20, 18, 20, 18)
        layout.setSpacing(12)

        header = QLabel("⚠️ ATTENZIONE: MATERIALE INSUFFICIENTE NELLA CATEGORIA SELEZIONATA")
        header.setStyleSheet("color: #C4A36B; font-weight: 700; font-size: 13px;")
        layout.addWidget(header)

        # Ripartizione durate
        req_m, req_s = divmod(int(self.required_duration_sec), 60)
        avail_m, avail_s = divmod(int(self.available_duration_sec), 60)

        info_box = QFrame()
        info_box.setObjectName("InnerCard")
        ib_layout = QVBoxLayout(info_box)
        ib_layout.setContentsMargins(12, 10, 12, 10)
        ib_layout.setSpacing(8)

        lbl_dur = QLabel(
            f"La storia richiede ~{req_m:02d}m {req_s:02d}s di girato continuo nella categoria \"{self.category}\", "
            f"ma nel pool sono presenti solo {avail_m:02d}m {avail_s:02d}s continui per questa specifica categoria."
        )
        lbl_dur.setWordWrap(True)
        lbl_dur.setStyleSheet("font-size: 12px; color: #DCE0EA;")
        ib_layout.addWidget(lbl_dur)

        rule_box = QLabel(
            "REGOLA DI CONTINUITÀ TEMATICA:\n"
            "I video di una storia possono provenire da più file master purché condividano la STESSA "
            "categoria tematica (es. due gameplay di Minecraft o Subway Surfers)."
        )
        rule_box.setStyleSheet("color: #949CAE; font-size: 11px;")
        rule_box.setWordWrap(True)
        ib_layout.addWidget(rule_box)
        layout.addWidget(info_box)

        lbl_opts = QLabel(
            "OPZIONI DISPONIBILI:\n"
            f"1. Aggiungi un nuovo video alla categoria \"{self.category}\" (Drag & Drop o YouTube).\n"
            "2. Assegna la storia a una categoria differente (es. \"Subway Surfers\", \"GTA V\" o \"General\")."
        )
        lbl_opts.setStyleSheet("color: #666E7F; font-size: 11px;")
        lbl_opts.setWordWrap(True)
        layout.addWidget(lbl_opts)

        # Bottoni di Azione
        btn_bar = QHBoxLayout()
        btn_bar.setSpacing(8)

        btn_change = QPushButton("🔄 Cambia Categoria")
        btn_change.clicked.connect(self._on_change_category)
        btn_bar.addWidget(btn_change)

        btn_bar.addStretch()

        btn_local = QPushButton("📁 Importa Locale")
        btn_local.clicked.connect(self._on_import_local)
        btn_bar.addWidget(btn_local)

        btn_yt = QPushButton("⬇️ Scarica da YouTube")
        btn_yt.setObjectName("PrimaryButton")
        btn_yt.clicked.connect(self._on_download_yt)
        btn_bar.addWidget(btn_yt)

        layout.addLayout(btn_bar)

    def _on_change_category(self):
        self.chosen_action = self.ACTION_CHANGE_CATEGORY
        self.accept()

    def _on_import_local(self):
        self.chosen_action = self.ACTION_IMPORT_LOCAL
        self.accept()

    def _on_download_yt(self):
        self.chosen_action = self.ACTION_DOWNLOAD_YT
        self.accept()
