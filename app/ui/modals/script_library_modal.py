"""AI Short Generator 1.0 - Script Library Modal (Available & Used History Tabs)"""

from typing import Optional, Dict, Any, List
from PySide6.QtWidgets import (
    QDialog, QVBoxLayout, QHBoxLayout, QLabel, QLineEdit, QPushButton,
    QTabWidget, QWidget, QScrollArea, QFrame, QMessageBox
)
from PySide6.QtCore import Qt, Signal
from app.core.script_manager import ScriptRepository
from app.config import DEFAULT_WPS


class ScriptLibraryModal(QDialog):
    """
    Finestra Modale Archivio Script & Storico Utilizzo:
    - Tab 1: Script DISPONIBILI pronti per la selezione
    - Tab 2: Script UTILIZZATI nello storico con pulsante [ 🔄 Crea Variante / Rigenera ]
    """

    script_selected = Signal(dict)

    def __init__(self, script_repo: ScriptRepository, parent: Optional[QWidget] = None):
        super().__init__(parent)
        self.repo = script_repo
        self.setWindowTitle("Archivio Script & Storico Utilizzo")
        self.resize(820, 600)
        self.selected_script: Optional[Dict[str, Any]] = None
        self._init_ui()
        self.refresh_data()

    def _init_ui(self):
        layout = QVBoxLayout(self)
        layout.setContentsMargins(18, 14, 18, 14)
        layout.setSpacing(10)

        # Header & Ricerca
        top_bar = QHBoxLayout()
        header_lbl = QLabel("ARCHIVIO SCRIPT & STORICO UTILIZZO")
        header_lbl.setObjectName("SectionHeader")
        top_bar.addWidget(header_lbl)
        top_bar.addStretch()

        btn_close = QPushButton("✕ Chiudi")
        btn_close.clicked.connect(self.close)
        top_bar.addWidget(btn_close)
        layout.addLayout(top_bar)

        # Search bar
        search_row = QHBoxLayout()
        search_row.addWidget(QLabel("Cerca per titolo o parole chiave:"))
        self.txt_search = QLineEdit()
        self.txt_search.setPlaceholderText("Es. black holes, history, caesar...")
        self.txt_search.textChanged.connect(self.refresh_data)
        search_row.addWidget(self.txt_search, stretch=1)
        layout.addLayout(search_row)

        # Tab Widget
        self.tabs = QTabWidget()
        self.tab_avail = QWidget()
        self.tab_used = QWidget()

        self.layout_avail = QVBoxLayout(self.tab_avail)
        self.layout_used = QVBoxLayout(self.tab_used)

        self.scroll_avail = QScrollArea()
        self.scroll_avail.setWidgetResizable(True)
        self.container_avail = QWidget()
        self.vbox_avail = QVBoxLayout(self.container_avail)
        self.scroll_avail.setWidget(self.container_avail)
        self.layout_avail.addWidget(self.scroll_avail)

        self.scroll_used = QScrollArea()
        self.scroll_used.setWidgetResizable(True)
        self.container_used = QWidget()
        self.vbox_used = QVBoxLayout(self.container_used)
        self.scroll_used.setWidget(self.container_used)
        self.layout_used.addWidget(self.scroll_used)

        self.tabs.addTab(self.tab_avail, "TAB: DISPONIBILI (0 Pronti)")
        self.tabs.addTab(self.tab_used, "TAB: UTILIZZATI / STORICO (0 Passati)")
        layout.addWidget(self.tabs, stretch=1)

    def refresh_data(self):
        query = self.txt_search.text().strip() or None
        avail_scripts = self.repo.get_scripts(status="DISPONIBILE", search_query=query)
        used_scripts = self.repo.get_scripts(status="UTILIZZATO", search_query=query)

        self.tabs.setTabText(0, f"TAB: DISPONIBILI ({len(avail_scripts)} Pronti)")
        self.tabs.setTabText(1, f"TAB: UTILIZZATI / STORICO ({len(used_scripts)} Passati)")

        # Pulisci layout
        self._clear_layout(self.vbox_avail)
        self._clear_layout(self.vbox_used)

        # Popola disponibili
        if not avail_scripts:
            lbl_empty = QLabel("Nessuno script disponibile trovato. Inserisci nuovi testi con '➕ Nuovo Script'.")
            lbl_empty.setObjectName("HelperText")
            self.vbox_avail.addWidget(lbl_empty)
        else:
            for s in avail_scripts:
                self.vbox_avail.addWidget(self._create_script_card(s, is_used=False))

        # Popola usati
        if not used_scripts:
            lbl_empty = QLabel("Nessuno script utilizzato nello storico.")
            lbl_empty.setObjectName("HelperText")
            self.vbox_used.addWidget(lbl_empty)
        else:
            for s in used_scripts:
                self.vbox_used.addWidget(self._create_script_card(s, is_used=True))

        self.vbox_avail.addStretch()
        self.vbox_used.addStretch()

    def _clear_layout(self, layout: QVBoxLayout):
        while layout.count():
            item = layout.takeAt(0)
            w = item.widget()
            if w:
                w.deleteLater()

    def _create_script_card(self, s: Dict[str, Any], is_used: bool) -> QFrame:
        card = QFrame()
        card.setObjectName("InnerCard")
        cl = QVBoxLayout(card)
        cl.setContentsMargins(10, 8, 10, 8)
        cl.setSpacing(4)

        # Riga 1: Titolo e Azione
        r1 = QHBoxLayout()
        title_lbl = QLabel(f"TITOLO: {s['context_title']}")
        title_lbl.setStyleSheet("font-weight: 600; font-size: 13px; color: #DCE0EA;")
        r1.addWidget(title_lbl)
        r1.addStretch()

        if is_used:
            b_used = QLabel("🔒 UTILIZZATO")
            b_used.setObjectName("BadgeUsedLock")
            r1.addWidget(b_used)

            btn_variant = QPushButton("🔄 Crea Variante / Rigenera")
            btn_variant.clicked.connect(lambda _, sid=s["id"]: self._on_create_variant(sid))
            r1.addWidget(btn_variant)
        else:
            btn_select = QPushButton("SELEZIONA QUESTO")
            btn_select.setObjectName("PrimaryButton")
            btn_select.clicked.connect(lambda _, s_data=s: self._on_select(s_data))
            r1.addWidget(btn_select)

        cl.addLayout(r1)

        # Riga 2: Metadati
        words = s.get("word_count", 0)
        dur = s.get("est_duration_sec", round(words / DEFAULT_WPS, 1))
        meta_lbl = QLabel(f"Parole: {words}  |  Stima Voce: ~{dur:.1f} s  |  Data: {s.get('created_at', '')}")
        meta_lbl.setObjectName("HelperText")
        cl.addWidget(meta_lbl)

        # Riga 3: Anteprima snippet testo
        raw = s.get("raw_text", "")
        snippet = (raw[:140] + "...") if len(raw) > 140 else raw
        snippet_lbl = QLabel(f'Anteprima: "{snippet}"')
        snippet_lbl.setStyleSheet("color: #949CAE; font-size: 12px;")
        snippet_lbl.setWordWrap(True)
        cl.addWidget(snippet_lbl)

        return card

    def _on_select(self, script_data: Dict[str, Any]):
        self.selected_script = script_data
        self.script_selected.emit(script_data)
        self.accept()

    def get_selected_script(self) -> Optional[Dict[str, Any]]:
        return self.selected_script

    def _on_create_variant(self, parent_id: int):
        ok, msg, new_id = self.repo.create_variant(parent_id, variant_label="New Variant")
        if ok:
            QMessageBox.information(self, "Variante Creata", f"{msg}\nPuoi ora selezionarla nella scheda DISPONIBILI.")
            self.refresh_data()
            self.tabs.setCurrentIndex(0)
        else:
            QMessageBox.warning(self, "Errore", msg)

