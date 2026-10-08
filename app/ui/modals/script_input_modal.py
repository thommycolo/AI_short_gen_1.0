"""AI Short Generator 1.0 - Script Input Modal with Fast Normalization & Variant Unlocking"""

from typing import Optional, Dict, Any
from PySide6.QtWidgets import (
    QDialog, QVBoxLayout, QHBoxLayout, QLabel, QTextEdit, QLineEdit,
    QPushButton, QFrame, QMessageBox, QWidget
)
from PySide6.QtCore import Qt, Signal
from app.config import DEFAULT_WPS, AUDIO_MAX_SEC
from app.core.script_manager import ScriptRepository
from app.core.fast_normalizer import FastDeterministicNormalizer


class ScriptInputModal(QDialog):
    """
    Finestra Modale Inserimento Nuovo Script & Verifica Storico:
    - Normalizzazione slang deterministica (<0.2ms CPU)
    - Deduplica True O(1) con MIH 6-blocchi SimHash
    - Rilevamento duplicati e sblocco deadlock 'Crea Nuova Variante'
    - Auto-Clearing e riposizionamento cursore a riga 1
    - Auto-Save on Close
    """

    script_saved = Signal(int)

    def __init__(self, script_repo: ScriptRepository, parent: Optional[QWidget] = None):
        super().__init__(parent)
        self.repo = script_repo
        self.setWindowTitle("Inserimento Nuovo Script & Verifica Storico")
        self.resize(760, 580)
        self.setObjectName("ModalWindow")
        self.last_duplicate_info: Optional[Dict[str, Any]] = None
        self.last_saved_script_id: Optional[int] = None
        self._init_ui()

    def _init_ui(self):
        layout = QVBoxLayout(self)
        layout.setContentsMargins(20, 16, 20, 16)
        layout.setSpacing(12)

        # Barra superiore
        top_bar = QHBoxLayout()
        title_lbl = QLabel("INSERIMENTO NUOVO SCRIPT & VERIFICA STORICO")
        title_lbl.setObjectName("SectionHeader")

        self.lbl_norm_badge = QLabel("Fast Norm: ON 🟢")
        self.lbl_norm_badge.setObjectName("BadgeAvailable")

        top_bar.addWidget(title_lbl)
        top_bar.addStretch()
        top_bar.addWidget(self.lbl_norm_badge)
        layout.addLayout(top_bar)

        layout.addWidget(QLabel("Incolla o digita il testo dello Short:"))

        # Area di testo principale
        self.text_edit = QTextEdit()
        self.text_edit.setPlaceholderText("Paste or type your short narrative text in English here...")
        self.text_edit.textChanged.connect(self._on_text_changed)
        layout.addWidget(self.text_edit, stretch=1)

        # Metriche in tempo reale: solo parole, durata voce e numero stimato clip
        self.lbl_metrics = QLabel("Numero di parole: 0  |  Stima durata voce: ~0.0 s  |  Numero stimato di clip video: 0")
        self.lbl_metrics.setObjectName("HelperText")
        layout.addWidget(self.lbl_metrics)

        # Box Titolo di Contesto Semantico
        title_box = QFrame()
        title_box.setObjectName("InnerCard")
        tb_layout = QVBoxLayout(title_box)
        tb_layout.setContentsMargins(10, 8, 10, 8)
        tb_layout.setSpacing(4)

        tb_layout.addWidget(QLabel("CATALOGAZIONE SEMANTICA:"))
        self.txt_title = QLineEdit()
        self.txt_title.setPlaceholderText("Nome di Contesto Proposto (es. Space_BlackHoles_EventHorizon)")
        tb_layout.addWidget(self.txt_title)
        layout.addWidget(title_box)

        # Banner di notifica / avviso duplicato
        self.feedback_banner = QFrame()
        self.feedback_banner.setVisible(False)
        self.fb_layout = QVBoxLayout(self.feedback_banner)
        self.fb_layout.setContentsMargins(10, 8, 10, 8)
        self.lbl_fb_text = QLabel("")
        self.lbl_fb_text.setWordWrap(True)
        self.btn_create_variant = QPushButton("🔄 Crea Nuova Variante (Nuovo Stile)")
        self.btn_create_variant.setVisible(False)
        self.btn_create_variant.clicked.connect(self._on_create_variant_clicked)
        self.fb_layout.addWidget(self.lbl_fb_text)
        self.fb_layout.addWidget(self.btn_create_variant)
        layout.addWidget(self.feedback_banner)

        # Barra bottoni
        btn_bar = QHBoxLayout()
        self.btn_cancel = QPushButton("Annulla / Chiudi")
        self.btn_cancel.clicked.connect(self.close)

        self.btn_save = QPushButton("Salva & Pulisci per Prossimo (Ctrl+Enter)")
        self.btn_save.setObjectName("PrimaryButton")
        self.btn_save.clicked.connect(self._on_save_clicked)

        btn_bar.addWidget(self.btn_cancel)
        btn_bar.addStretch()
        btn_bar.addWidget(self.btn_save)
        layout.addLayout(btn_bar)

    def _on_text_changed(self):
        text = self.text_edit.toPlainText().strip()
        words = text.split()
        word_count = len(words)
        est_sec = round(word_count / DEFAULT_WPS, 1)
        num_clips = max(1, int(round(est_sec / 40.0 + 0.49))) if word_count > 0 else 0

        warning_color = "#AA7373" if est_sec > AUDIO_MAX_SEC else "#949CAE"
        self.lbl_metrics.setText(
            f"Numero di parole: {word_count}  |  "
            f"Stima durata voce: ~{est_sec:.1f} s  |  "
            f"Numero stimato di clip video: {num_clips}"
        )
        self.lbl_metrics.setStyleSheet(f"color: {warning_color};")

        # Proposta titolo semantico automatica se non modificata manualmente
        if not self.txt_title.text() or self.txt_title.property("auto_generated"):
            proposed = self.repo.generate_context_title(text)
            self.txt_title.setText(proposed)
            self.txt_title.setProperty("auto_generated", True)

    def _on_save_clicked(self):
        raw_text = self.text_edit.toPlainText().strip()
        if not raw_text:
            QMessageBox.warning(self, "Attenzione", "Inserisci il testo dello script prima di salvare.")
            return

        custom_title = self.txt_title.text().strip() or None
        success, message, new_id, dup_info = self.repo.save_new_script(raw_text, custom_title=custom_title)

        if success:
            self.last_duplicate_info = None
            self.feedback_banner.setVisible(True)
            self.feedback_banner.setStyleSheet("background-color: #22382D; border: 1px solid #2D4C3C; border-radius: 6px;")
            self.lbl_fb_text.setText(f"✓ SCRIPT CORRETTO, SANITIZZATO E SALVATO (ID: #{new_id})\n{message}")
            self.lbl_fb_text.setStyleSheet("color: #729B84; font-weight: 600;")
            self.btn_create_variant.setVisible(False)

            self.last_saved_script_id = new_id
            self.text_edit.clear()
            self.txt_title.clear()
            self.text_edit.setFocus()
            self.script_saved.emit(new_id)

        else:
            self.last_duplicate_info = dup_info
            self.feedback_banner.setVisible(True)
            self.feedback_banner.setStyleSheet("background-color: #3D2525; border: 1px solid #5C3232; border-radius: 6px;")
            self.lbl_fb_text.setText(f"⚠ ATTENZIONE: TESTO GIÀ PRESENTE NELLO STORICO\n{message}")
            self.lbl_fb_text.setStyleSheet("color: #AA7373; font-weight: 500;")

            # Se lo script era già UTILIZZATO, mostra il tasto di sblocco varianti
            if dup_info and dup_info.get("status") == "UTILIZZATO":
                self.btn_create_variant.setVisible(True)
                self.lbl_fb_text.setText(
                    f"⚠ TESTO GIÀ PRODOTTO IN PASSATO (ID: #{dup_info.get('id')})\n"
                    f"Vuoi creare una nuova variante con stile o speaker differente?"
                )
            else:
                self.btn_create_variant.setVisible(False)

    def _on_create_variant_clicked(self):
        if not self.last_duplicate_info:
            return
        parent_id = self.last_duplicate_info["id"]
        ok, msg, new_id = self.repo.create_variant(parent_id, variant_label="New Style Variant")
        if ok:
            self.last_saved_script_id = new_id
            self.feedback_banner.setStyleSheet("background-color: #22382D; border: 1px solid #2D4C3C; border-radius: 6px;")
            self.lbl_fb_text.setText(f"✓ VARIANTE CREATA CON SUCCESSO (Nuovo ID: #{new_id}, Stato: DISPONIBILE)\n{msg}")
            self.lbl_fb_text.setStyleSheet("color: #729B84; font-weight: 600;")
            self.btn_create_variant.setVisible(False)
            self.text_edit.clear()
            self.txt_title.clear()
            self.script_saved.emit(new_id)

    def get_saved_script(self) -> Optional[Dict[str, Any]]:
        """Restituisce il record dell'ultimo script salvato/variante generata."""
        if self.last_saved_script_id:
            return self.repo.get_script_by_id(self.last_saved_script_id)
        return None

    def closeEvent(self, event):
        # Auto-Save on Close: se c'è testo digitato, salvalo prima di congedare la finestra
        raw_text = self.text_edit.toPlainText().strip()
        if raw_text and len(raw_text.split()) >= 3:
            custom_title = self.txt_title.text().strip() or None
            ok, msg, new_id, _ = self.repo.save_new_script(raw_text, custom_title=custom_title)
            if ok:
                self.last_saved_script_id = new_id
        super().closeEvent(event)


