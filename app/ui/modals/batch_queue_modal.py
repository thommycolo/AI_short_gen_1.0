"""AI Short Generator 1.0 - Batch Queue Manager Modal with Audit & Zero-Waste Optimizer"""

from typing import Optional, Dict, Any, List
from PySide6.QtWidgets import (
    QDialog, QVBoxLayout, QHBoxLayout, QLabel, QPushButton, QTableWidget,
    QTableWidgetItem, QHeaderView, QCheckBox, QFrame, QScrollArea, QWidget,
    QMessageBox
)
from PySide6.QtCore import Qt, Signal
from app.config import DEFAULT_WPS
from app.core.script_manager import ScriptRepository
from app.core.continuous_video_manager import ContinuousVideoPoolManager
from app.core.batch_allocator import (
    StoryRequirement, VideoSourceCandidate, ContinuousBatchFeasibilitySolver,
    FeasibilityReport
)


class BatchQueueManagerModal(QDialog):
    """
    Finestra Modale Coda di Produzione Multi-Storia & Audit Preventivo:
    - Configurazione indipendente di voce, font e speed_rate per storia
    - Propagazione universale 'Applica a Tutte'
    - Solver CSP con Continuità per Categoria Tematica
    - Suggerimento euristico 'Zero Sprechi' (Regola 1m 30s +20s/-inf)
    - Auto-Save on Close
    """

    start_batch_requested = Signal(list) # List[StoryRequirement]

    def __init__(
        self,
        script_repo: ScriptRepository,
        video_mgr: ContinuousVideoPoolManager,
        parent: Optional[QWidget] = None
    ):
        super().__init__(parent)
        self.repo = script_repo
        self.video_mgr = video_mgr
        self.setWindowTitle("Coda di Produzione Batch & Audit Preventivo di Fattibilità")
        self.resize(960, 680)
        self.setObjectName("ModalWindow")

        self.available_scripts = self.repo.get_scripts(status="DISPONIBILE")
        self.queue_items: List[StoryRequirement] = []
        self._init_ui()
        self._load_initial_queue()
        self.run_feasibility_audit()

    def _init_ui(self):
        layout = QVBoxLayout(self)
        layout.setContentsMargins(18, 14, 18, 14)
        layout.setSpacing(10)

        # Header & Strumenti Rapidi
        top_bar = QHBoxLayout()
        header_lbl = QLabel("CODA DI PRODUZIONE BATCH & AUDIT PREVENTIVO")
        header_lbl.setObjectName("SectionHeader")

        self.btn_apply_voice_all = QPushButton("🔗 Applica Voce a Tutte")
        self.btn_apply_voice_all.clicked.connect(self._apply_first_voice_to_all)

        self.btn_apply_font_all = QPushButton("🔗 Applica Font a Tutte")
        self.btn_apply_font_all.clicked.connect(self._apply_first_font_to_all)

        btn_close = QPushButton("✕ Chiudi")
        btn_close.clicked.connect(self.close)

        top_bar.addWidget(header_lbl)
        top_bar.addStretch()
        top_bar.addWidget(self.btn_apply_voice_all)
        top_bar.addWidget(self.btn_apply_font_all)
        top_bar.addWidget(btn_close)
        layout.addLayout(top_bar)

        # Checklist selezione storie da includere
        select_box = QFrame()
        select_box.setObjectName("InnerCard")
        sb_layout = QVBoxLayout(select_box)
        sb_layout.setContentsMargins(8, 6, 8, 6)
        sb_layout.addWidget(QLabel("SELEZIONA LE STORIE DALL'ARCHIVIO DA INCLUDERE NELLA CODA:"))

        self.checkbox_container = QWidget()
        self.cb_vbox = QVBoxLayout(self.checkbox_container)
        self.cb_vbox.setSpacing(4)
        self.checkbox_map: Dict[int, QCheckBox] = {}

        for s in self.available_scripts:
            cb = QCheckBox(f"#{s['id']} \"{s['context_title']}\" ({s['word_count']} parole, ~{s['est_duration_sec']}s)")
            cb.setChecked(True)
            cb.stateChanged.connect(self._on_selection_changed)
            self.checkbox_map[s["id"]] = cb
            self.cb_vbox.addWidget(cb)

        cb_scroll = QScrollArea()
        cb_scroll.setFixedHeight(95)
        cb_scroll.setWidgetResizable(True)
        cb_scroll.setWidget(self.checkbox_container)
        sb_layout.addWidget(cb_scroll)
        layout.addWidget(select_box)

        # Tabella Dettagliata Coda
        layout.addWidget(QLabel("TABELLA DETTAGLIATA CODA: PREVISIONE DINAMICA, STILI & ASSEGNAZIONE:"))
        self.table = QTableWidget()
        self.table.setColumnCount(7)
        self.table.setHorizontalHeaderLabels([
            "#", "STORIA IN CODA", "VOCE & SPEED", "STILE FONT", "SECONDI", "VIDEO ASSEGNATO", "STATO"
        ])
        self.table.horizontalHeader().setSectionResizeMode(QHeaderView.Stretch)
        self.table.horizontalHeader().setSectionResizeMode(0, QHeaderView.ResizeToContents)
        self.table.horizontalHeader().setSectionResizeMode(4, QHeaderView.ResizeToContents)
        layout.addWidget(self.table, stretch=1)

        # Box Responso Audit Fattibilità
        self.audit_box = QFrame()
        self.audit_box.setObjectName("InnerCard")
        self.ab_layout = QVBoxLayout(self.audit_box)
        self.ab_layout.setContentsMargins(10, 8, 10, 8)
        self.lbl_audit_status = QLabel("")
        self.lbl_audit_status.setWordWrap(True)
        self.btn_apply_suggestion = QPushButton("💡 APPLICA SUGGERIMENTO OTTIMALE ZERO SPRECHI")
        self.btn_apply_suggestion.setObjectName("SuccessButton")
        self.btn_apply_suggestion.setVisible(False)
        self.btn_apply_suggestion.clicked.connect(self._on_apply_suggestion_clicked)

        self.ab_layout.addWidget(self.lbl_audit_status)
        self.ab_layout.addWidget(self.btn_apply_suggestion)
        layout.addWidget(self.audit_box)

        # Footer
        footer = QHBoxLayout()
        btn_cancel = QPushButton("Annulla / Chiudi (Auto-Saved)")
        btn_cancel.clicked.connect(self.close)

        self.btn_start = QPushButton("🚀 AVVIA PRODUZIONE BATCH")
        self.btn_start.setObjectName("PrimaryButton")
        self.btn_start.clicked.connect(self._on_start_clicked)

        footer.addWidget(btn_cancel)
        footer.addStretch()
        footer.addWidget(self.btn_start)
        layout.addLayout(footer)

    def _load_initial_queue(self):
        self.queue_items.clear()
        for s in self.available_scripts:
            req = StoryRequirement(
                script_id=s["id"],
                context_title=s["context_title"],
                num_parts=max(1, int(round(s["est_duration_sec"] / 40.0 + 0.49))),
                base_duration_sec=s["est_duration_sec"],
                speed_rate=1.00,
                category="General",
                text=s["raw_text"],
                voice_config={"speaker": "Ryan", "instruct": "Viral Hook"},
                subtitle_config={"font_name": "Montserrat Black", "font_size": 68}
            )
            self.queue_items.append(req)

    def _on_selection_changed(self):
        active_ids = {sid for sid, cb in self.checkbox_map.items() if cb.isChecked()}
        filtered = []
        for s in self.available_scripts:
            if s["id"] in active_ids:
                req = StoryRequirement(
                    script_id=s["id"],
                    context_title=s["context_title"],
                    num_parts=max(1, int(round(s["est_duration_sec"] / 40.0 + 0.49))),
                    base_duration_sec=s["est_duration_sec"],
                    speed_rate=1.00,
                    category="General",
                    text=s["raw_text"],
                    voice_config={"speaker": "Ryan", "instruct": "Viral Hook"},
                    subtitle_config={"font_name": "Montserrat Black", "font_size": 68}
                )
                filtered.append(req)
        self.queue_items = filtered
        self.run_feasibility_audit()

    def run_feasibility_audit(self):
        raw_pool = self.video_mgr.get_all_sources()
        candidates = [
            VideoSourceCandidate(
                source_id=r["id"],
                title=r["video_title"],
                category=r["category"],
                available_duration_sec=r["available_duration_sec"],
                current_playhead_sec=r["frontier_playhead_sec"],
                file_path=r["file_path"]
            ) for r in raw_pool
        ]

        report = ContinuousBatchFeasibilitySolver.solve(self.queue_items, candidates)
        self._populate_table(report)

        if report.is_feasible and self.queue_items:
            self.audit_box.setStyleSheet("background-color: #22382D; border: 1px solid #2D4C3C; border-radius: 6px;")
            self.lbl_audit_status.setText(
                f"🟢 CODA 100% FATTIBILE - MATERIALE CONTINUO COMPLETO\n"
                f"• Totale Storie in Coda: {report.total_stories} | "
                f"Tempo Continuo Richiesto: {report.total_seconds_needed:.1f}s | "
                f"Disponibili nel Pool: {report.total_seconds_available:.1f}s"
            )
            self.lbl_audit_status.setStyleSheet("color: #729B84; font-weight: 600;")
            self.btn_apply_suggestion.setVisible(False)
            self.btn_start.setEnabled(True)

        elif not self.queue_items:
            self.audit_box.setStyleSheet("background-color: #252933; border: 1px solid #343946; border-radius: 6px;")
            self.lbl_audit_status.setText("Nessuna storia selezionata nella coda.")
            self.lbl_audit_status.setStyleSheet("color: #949CAE;")
            self.btn_apply_suggestion.setVisible(False)
            self.btn_start.setEnabled(False)

        else:
            self.audit_box.setStyleSheet("background-color: #3D3425; border: 1px solid #54462E; border-radius: 6px;")
            suggestions = ContinuousBatchFeasibilitySolver.suggest_optimal_subqueue(self.queue_items, candidates)
            self.current_suggestions = suggestions

            if suggestions:
                best = suggestions[0]
                self.lbl_audit_status.setText(
                    f"🟡 AUDIT: MATERIALE ATTUALMENTE INSUFFICIENTE (Deficit: {report.deficit_seconds:.1f}s)\n"
                    f"💡 SUGGERIMENTO OTTIMIZZATORE 'ZERO SPRECHI':\n"
                    f"Produci {len(best.selected_stories)} storie su {len(self.queue_items)}. "
                    f"Scarti eliminati da Garbage Collector: {best.wasted_seconds_purged:.1f}s!"
                )
                self.btn_apply_suggestion.setVisible(True)
            else:
                self.lbl_audit_status.setText(
                    f"🔴 MATERIALE TOTALMENTE INSUFFICIENTE (Deficit: {report.deficit_seconds:.1f}s). "
                    f"Importa nuovi video nel Video Pool."
                )
                self.btn_apply_suggestion.setVisible(False)

            self.lbl_audit_status.setStyleSheet("color: #C4A36B; font-weight: 500;")
            self.btn_start.setEnabled(False)

    def _populate_table(self, report: FeasibilityReport):
        self.table.setRowCount(len(self.queue_items))
        plan_map = {p.story.script_id: p for p in report.plans}

        for idx, story in enumerate(self.queue_items):
            plan = plan_map.get(story.script_id)

            item_idx = QTableWidgetItem(str(idx + 1))
            item_idx.setTextAlignment(Qt.AlignCenter)

            item_title = QTableWidgetItem(story.context_title)
            item_voice = QTableWidgetItem(f"🎙️ {story.voice_config.get('speaker', 'Ryan')} ({story.speed_rate:.2f}x)")
            item_font = QTableWidgetItem(f"🔤 {story.subtitle_config.get('font_name', 'Montserrat')}")
            item_sec = QTableWidgetItem(f"{story.estimated_video_seconds:.1f}s")
            item_sec.setTextAlignment(Qt.AlignCenter)

            if plan:
                item_vid = QTableWidgetItem(f"{plan.source_title} [{plan.start_time_sec:.0f}-{plan.end_time_sec:.0f}s]")
                item_status = QTableWidgetItem("🟢 OK")
                item_status.setTextAlignment(Qt.AlignCenter)
            else:
                item_vid = QTableWidgetItem("Nessun video idoneo")
                item_status = QTableWidgetItem("🔴 Incompleto")
                item_status.setTextAlignment(Qt.AlignCenter)

            self.table.setItem(idx, 0, item_idx)
            self.table.setItem(idx, 1, item_title)
            self.table.setItem(idx, 2, item_voice)
            self.table.setItem(idx, 3, item_font)
            self.table.setItem(idx, 4, item_sec)
            self.table.setItem(idx, 5, item_vid)
            self.table.setItem(idx, 6, item_status)

    def _on_apply_suggestion_clicked(self):
        if hasattr(self, "current_suggestions") and self.current_suggestions:
            best = self.current_suggestions[0]
            selected_ids = {s.script_id for s in best.selected_stories}
            for sid, cb in self.checkbox_map.items():
                cb.setChecked(sid in selected_ids)
            QMessageBox.information(self, "Suggerimento Applicato", "Coda aggiornata alla configurazione ottimale a zero sprechi!")

    def _apply_first_voice_to_all(self):
        if not self.queue_items:
            return
        v_cfg = self.queue_items[0].voice_config
        speed = self.queue_items[0].speed_rate
        for item in self.queue_items:
            item.voice_config = dict(v_cfg)
            item.speed_rate = speed
        self.run_feasibility_audit()
        QMessageBox.information(self, "Propagazione Eseguita", "Voce e velocità applicate a tutti i testi in coda.")

    def _apply_first_font_to_all(self):
        if not self.queue_items:
            return
        s_cfg = self.queue_items[0].subtitle_config
        for item in self.queue_items:
            item.subtitle_config = dict(s_cfg)
        self.run_feasibility_audit()
        QMessageBox.information(self, "Propagazione Eseguita", "Stile font applicato a tutti i testi in coda.")

    def _on_start_clicked(self):
        self.start_batch_requested.emit(self.queue_items)
        self.accept()


# Alias per compatibilità
BatchQueueModal = BatchQueueManagerModal
