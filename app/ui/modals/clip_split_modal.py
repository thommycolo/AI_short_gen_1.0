"""AI Short Generator 1.0 - Dynamic Clip Split & Temporal Parameters Modal with Interactive Text Transfer & Intro/Outro Customization"""

import re
from typing import Optional, Dict, Any, List
from PySide6.QtWidgets import (
    QDialog, QVBoxLayout, QHBoxLayout, QLabel, QPushButton, QFrame,
    QScrollArea, QWidget, QSlider, QDoubleSpinBox, QPlainTextEdit,
    QLineEdit, QSplitter, QApplication, QMessageBox
)
from PySide6.QtCore import Qt, Signal, QTimer

from app.config import (
    TARGET_VIDEO_MAX_SEC, ALLOWED_CHUNKING_DELTA_SEC, DEFAULT_WPS,
    PADDING_INTRO_SEC, PADDING_OUTRO_SEC, OUTRO_PAUSE_SEC, PADDING_TOTAL_SEC,
    DEFAULT_OUTRO_CTA_FINAL, DEFAULT_OUTRO_CTA_TEMPLATE
)
from app.core.discourse_chunker import DiscourseCoherenceChunker
from app.core.script_manager import ScriptRepository


class IntroOutroEditDialog(QDialog):
    """
    Finestrella di dialogo dedicata per modificare in modo granulare l'Intro o l'Outro di una clip:
    - Salva automaticamente per la singola clip senza dover premere nulla
    - Pulsanti per propagare a tutte le clip del progetto (rispettando intermedie vs finale)
    - Pulsante per impostare come default predefinito di sistema
    """

    save_single = Signal(dict)
    save_all_project = Signal(dict)
    save_default_global = Signal(dict)

    def __init__(
        self,
        clip_idx: int,
        total_clips: int,
        is_final: bool,
        intro_title: str,
        outro_spoken: str,
        outro_banner: str,
        parent: Optional[QWidget] = None
    ):
        super().__init__(parent)
        self.clip_idx = clip_idx
        self.total_clips = total_clips
        self.is_final = is_final
        self.setObjectName("ModalWindow")
        self.setWindowTitle(f"Modifica Intro & Outro — Clip #{clip_idx}")
        self.resize(540, 460)

        self._intro_title = intro_title
        self._outro_spoken = outro_spoken
        self._outro_banner = outro_banner

        self._init_ui()

    def _init_ui(self):
        layout = QVBoxLayout(self)
        layout.setContentsMargins(18, 16, 18, 16)
        layout.setSpacing(12)

        # Header con Badge di Tipologia Clip
        head_row = QHBoxLayout()
        lbl_head = QLabel(f"MODIFICA INTRO & OUTRO — CLIP #{self.clip_idx} DI {self.total_clips}")
        lbl_head.setObjectName("SectionHeader")

        type_text = "🔴 CLIP FINALE" if self.is_final else f"🟡 CLIP INTERMEDIA #{self.clip_idx}"
        type_style = (
            "background-color: #3D2525; color: #AA7373; border: 1px solid #5C3232; border-radius: 4px; padding: 2px 8px; font-weight: 700; font-size: 11px;"
            if self.is_final else
            "background-color: #3D3425; color: #C4A36B; border: 1px solid #5C4E32; border-radius: 4px; padding: 2px 8px; font-weight: 700; font-size: 11px;"
        )
        lbl_type = QLabel(type_text)
        lbl_type.setStyleSheet(type_style)

        head_row.addWidget(lbl_head)
        head_row.addStretch()
        head_row.addWidget(lbl_type)
        layout.addLayout(head_row)

        desc_text = (
            "Questa è la clip finale del video: la sua Outro chiude la serie. "
            "Se la imposti come predefinita o la applichi a tutto il progetto, NON toccherà le outro intermedie."
            if self.is_final else
            f"Questa è una clip intermedia (porta alla clip #{self.clip_idx + 1}). "
            "Se la applichi a tutto il progetto, aggiornerà solo le clip intermedie senza toccare quella finale."
        )
        lbl_desc = QLabel(desc_text)
        lbl_desc.setObjectName("HelperText")
        lbl_desc.setWordWrap(True)
        layout.addWidget(lbl_desc)

        # Sezione 1: Intro Titolo Banner
        intro_box = QFrame()
        intro_box.setObjectName("InnerCard")
        ib_layout = QVBoxLayout(intro_box)
        ib_layout.setContentsMargins(10, 8, 10, 8)
        ib_layout.setSpacing(4)

        ib_layout.addWidget(QLabel("TITOLO INTRO / BANNER A SCHERMO:"))
        self.txt_intro = QLineEdit(self._intro_title)
        self.txt_intro.textChanged.connect(self._on_fields_changed)
        ib_layout.addWidget(self.txt_intro)
        layout.addWidget(intro_box)

        # Sezione 2: Outro Spoken (TTS) e Outro Banner
        outro_box = QFrame()
        outro_box.setObjectName("InnerCard")
        ob_layout = QVBoxLayout(outro_box)
        ob_layout.setContentsMargins(10, 8, 10, 8)
        ob_layout.setSpacing(6)

        ob_layout.addWidget(QLabel("OUTRO PARLATO DAL TTS (Sintesi Vocale):"))
        self.txt_spoken = QLineEdit(self._outro_spoken)
        self.txt_spoken.textChanged.connect(self._on_fields_changed)
        ob_layout.addWidget(self.txt_spoken)

        ob_layout.addWidget(QLabel("OUTRO BANNER A SCHERMO (Grafica Overlay):"))
        self.txt_banner = QLineEdit(self._outro_banner)
        self.txt_banner.textChanged.connect(self._on_fields_changed)
        ob_layout.addWidget(self.txt_banner)

        hint = "{next_part} verrà sostituito con il numero della clip successiva" if not self.is_final else "Frase di chiusura finale della storia"
        lbl_hint = QLabel(f"💡 Suggerimento: {hint}")
        lbl_hint.setStyleSheet("color: #7E95BC; font-size: 11px;")
        ob_layout.addWidget(lbl_hint)

        layout.addWidget(outro_box)

        # Sezione 3: Pulsanti Azioni
        btn_box = QVBoxLayout()
        btn_box.setSpacing(6)

        # Pulsante 1: Applica a tutto il progetto
        scope_text = "a tutte le Finali" if self.is_final else "a TUTTE le Intermedie (Clip 1..N-1)"
        self.btn_apply_all = QPushButton(f"🔗 Applica {scope_text} del Progetto")
        self.btn_apply_all.setToolTip("Propaga questo formato a tutte le clip compatibili della serie senza toccare la tipologia opposta")
        self.btn_apply_all.clicked.connect(self._on_apply_all_clicked)
        btn_box.addWidget(self.btn_apply_all)

        # Pulsante 2: Imposta come Default Predefinito
        self.btn_make_default = QPushButton("⭐ Imposta come Default Predefinito Globale")
        self.btn_make_default.setToolTip("Salva questo testo come impostazione predefinita per le future generazioni")
        self.btn_make_default.clicked.connect(self._on_make_default_clicked)
        btn_box.addWidget(self.btn_make_default)

        # Pulsante 3: Chiudi / Salva solo per questa clip
        bottom_row = QHBoxLayout()
        lbl_auto_save = QLabel("✓ Modifiche salvate automaticamente per questa clip")
        lbl_auto_save.setStyleSheet("color: #729B84; font-size: 11px; font-weight: 600;")
        self.btn_close = QPushButton("Fatto / Chiudi")
        self.btn_close.setObjectName("PrimaryButton")
        self.btn_close.clicked.connect(self.accept)

        bottom_row.addWidget(lbl_auto_save)
        bottom_row.addStretch()
        bottom_row.addWidget(self.btn_close)
        btn_box.addLayout(bottom_row)

        layout.addLayout(btn_box)

    def _get_current_payload(self) -> dict:
        return {
            "clip_idx": self.clip_idx,
            "is_final": self.is_final,
            "intro": self.txt_intro.text().strip(),
            "spoken": self.txt_spoken.text().strip(),
            "banner": self.txt_banner.text().strip()
        }

    def _on_fields_changed(self):
        # Salva in tempo reale solo per questa clip senza dover premere nulla
        self.save_single.emit(self._get_current_payload())

    def _on_apply_all_clicked(self):
        payload = self._get_current_payload()
        self.save_all_project.emit(payload)
        self.accept()

    def _on_make_default_clicked(self):
        payload = self._get_current_payload()
        self.save_default_global.emit(payload)
        QMessageBox.information(
            self,
            "Predefinito Aggiornato",
            f"Il template {'Finale' if self.is_final else 'Intermedio'} è stato impostato come predefinito globale."
        )


class ClipCardWidget(QFrame):
    """
    Card grafica per la visualizzazione della singola clip:
    - Almeno 6 righe di testo ben visibili e confortevoli
    - Testo editabile direttamente nella card con aggiornamento immediato delle statistiche
    - Pulsanti rapidi per spingere frasi su/giù tra le clip in autonomia
    - Badge Intro e Outro cliccabili per aprire il dialogo di modifica dedicato
    - Testo in rosso affianco al banner se vi è asimmetria nelle modifiche delle outro
    """

    text_edited = Signal(int, str)             # (part_idx, new_text)
    move_first_sentence_up = Signal(int)       # (part_idx)
    move_last_sentence_down = Signal(int)      # (part_idx)
    merge_with_next = Signal(int)              # (part_idx)
    delete_clip = Signal(int)                  # (part_idx)
    open_edit_dialog = Signal(int)             # (part_idx)

    def __init__(
        self,
        part_idx: int,
        total_parts: int,
        clip_text: str,
        intro_title: str,
        narr_dur: float,
        outro_dur: float,
        outro_pause: float,
        padding_intro: float,
        padding_outro: float,
        outro_spoken: str,
        outro_banner: str,
        is_in_range: bool,
        is_short: bool,
        show_red_warning: bool = False,
        red_warning_text: str = "",
        parent: Optional[QWidget] = None
    ):
        super().__init__(parent)
        self.setObjectName("InnerCard")
        self.part_idx = part_idx
        self.total_parts = total_parts
        self.clip_text = clip_text
        self.intro_title = intro_title
        self.outro_spoken = outro_spoken
        self.outro_banner = outro_banner
        self.is_final = (part_idx == total_parts)

        self._updating = False
        self._init_ui(
            narr_dur, outro_dur, outro_pause, padding_intro, padding_outro,
            is_in_range, is_short, show_red_warning, red_warning_text
        )

    def _init_ui(
        self,
        narr_dur: float,
        outro_dur: float,
        outro_pause: float,
        padding_intro: float,
        padding_outro: float,
        is_in_range: bool,
        is_short: bool,
        show_red_warning: bool,
        red_warning_text: str
    ):
        layout = QVBoxLayout(self)
        layout.setContentsMargins(12, 10, 12, 10)
        layout.setSpacing(6)

        total_video_dur = narr_dur + outro_pause + outro_dur + padding_intro + padding_outro
        words = len(self.clip_text.split())
        chars = len(self.clip_text)

        # 1. Header con Indice Clip, Badge di Stato e Intro Titolo Cliccabile
        header_row = QHBoxLayout()
        lbl_title = QLabel(f"🎬 CLIP #{self.part_idx} DI {self.total_parts}")
        lbl_title.setStyleSheet("font-weight: 700; font-size: 13px; color: #E2E6EF;")

        # Badge Durata Totale
        if is_in_range:
            badge_text = f"🟢 OTTIMALE: ~{total_video_dur:.1f}s"
            badge_style = "background-color: #22382D; color: #729B84; border: 1px solid #2D4C3C; border-radius: 4px; padding: 2px 8px; font-weight: 600; font-size: 11px;"
        elif is_short:
            badge_text = f"🟡 FINALE / BREVE: ~{total_video_dur:.1f}s"
            badge_style = "background-color: #3D3425; color: #C4A36B; border: 1px solid #5C4E32; border-radius: 4px; padding: 2px 8px; font-weight: 600; font-size: 11px;"
        else:
            badge_text = f"🔴 LUNGA: ~{total_video_dur:.1f}s"
            badge_style = "background-color: #3D2525; color: #AA7373; border: 1px solid #5C3232; border-radius: 4px; padding: 2px 8px; font-weight: 600; font-size: 11px;"

        lbl_badge = QLabel(badge_text)
        lbl_badge.setStyleSheet(badge_style)

        # Pulsante Cliccabile Intro Titolo
        self.btn_intro_edit = QPushButton(f'🏷️ Intro: "{self.intro_title}" ✏️')
        self.btn_intro_edit.setToolTip("Clicca per modificare l'Intro / Titolo banner di questa clip")
        self.btn_intro_edit.setStyleSheet(
            "font-size: 11px; padding: 2px 8px; background-color: #252933; border: 1px solid #3C4252; color: #DCE0EA;"
        )
        self.btn_intro_edit.clicked.connect(lambda: self.open_edit_dialog.emit(self.part_idx))

        header_row.addWidget(lbl_title)
        header_row.addWidget(lbl_badge)
        header_row.addStretch()
        header_row.addWidget(self.btn_intro_edit)
        layout.addLayout(header_row)

        # 2. Riga Metriche Dettagliate
        self.lbl_stats = QLabel(
            f"Voce: ~{narr_dur:.1f}s  |  Pausa: {outro_pause:.1f}s  |  Outro: ~{outro_dur:.1f}s  |  "
            f"Padding: +{padding_intro + padding_outro:.1f}s  |  {words} parole  |  {chars} caratteri"
        )
        self.lbl_stats.setObjectName("HelperText")
        self.lbl_stats.setStyleSheet("color: #949CAE; font-size: 11px;")
        layout.addWidget(self.lbl_stats)

        # 3. Box Testo della Clip (ALMENO 6 RIGHE VISIBILI E EDITABILE)
        self.txt_box = QPlainTextEdit()
        self.txt_box.setPlainText(self.clip_text)
        self.txt_box.setMinimumHeight(140)  # Garantisce almeno 6 righe di testo ampie e comode
        self.txt_box.setPlaceholderText("Testo della clip...")
        self.txt_box.setStyleSheet(
            "background-color: #181A20; color: #DCE0EA; border: 1px solid #2F3440; "
            "border-radius: 6px; padding: 8px; font-size: 12px; line-height: 1.45;"
        )
        self.txt_box.textChanged.connect(self._on_internal_text_changed)
        layout.addWidget(self.txt_box)

        # 4. Riga di Spostamento Autonomo del Testo tra le Clip
        nav_row = QHBoxLayout()
        nav_row.setSpacing(6)

        # Sposta su
        self.btn_move_up = QPushButton("⬆️ Frase su (alla precedente)")
        self.btn_move_up.setStyleSheet("font-size: 11px; padding: 3px 8px;")
        self.btn_move_up.setToolTip("Prende la prima frase di questa clip e la sposta in fondo alla clip precedente")
        self.btn_move_up.setEnabled(self.part_idx > 1)
        self.btn_move_up.clicked.connect(lambda: self.move_first_sentence_up.emit(self.part_idx))
        nav_row.addWidget(self.btn_move_up)

        # Sposta giù
        self.btn_move_down = QPushButton("⬇️ Frase giù (alla successiva)")
        self.btn_move_down.setStyleSheet("font-size: 11px; padding: 3px 8px;")
        self.btn_move_down.setToolTip("Prende l'ultima frase di questa clip e la sposta all'inizio della clip successiva")
        self.btn_move_down.setEnabled(self.part_idx < self.total_parts)
        self.btn_move_down.clicked.connect(lambda: self.move_last_sentence_down.emit(self.part_idx))
        nav_row.addWidget(self.btn_move_down)

        # Unisci con successiva
        if self.part_idx < self.total_parts:
            self.btn_merge = QPushButton("🔗 Unisci con successiva")
            self.btn_merge.setStyleSheet("font-size: 11px; padding: 3px 8px;")
            self.btn_merge.clicked.connect(lambda: self.merge_with_next.emit(self.part_idx))
            nav_row.addWidget(self.btn_merge)

        # Elimina clip
        if self.total_parts > 1:
            self.btn_del = QPushButton("🗑 Elimina clip")
            self.btn_del.setStyleSheet("font-size: 11px; padding: 3px 8px; color: #AA7373;")
            self.btn_del.clicked.connect(lambda: self.delete_clip.emit(self.part_idx))
            nav_row.addWidget(self.btn_del)

        nav_row.addStretch()

        btn_copy = QPushButton("📋 Copia")
        btn_copy.setStyleSheet("font-size: 11px; padding: 3px 8px;")
        btn_copy.clicked.connect(lambda: self._copy_text(btn_copy))
        nav_row.addWidget(btn_copy)

        layout.addLayout(nav_row)

        # 5. Riga Outro Cliccabile & Avviso Rosso di Coerenza
        outro_row = QHBoxLayout()
        outro_row.setSpacing(8)

        # Pulsante Cliccabile per Modificare l'Outro
        self.btn_outro_edit = QPushButton(
            f'🗣️ Outro Spoken: "{self.outro_spoken}"  |  Banner: "{self.outro_banner}" ✏️'
        )
        self.btn_outro_edit.setToolTip("Clicca per modificare l'Outro parlata o il banner a schermo di questa clip")
        self.btn_outro_edit.setStyleSheet(
            "font-size: 11px; padding: 4px 10px; background-color: #21242C; border: 1px solid #343946; color: #BFA175; text-align: left;"
        )
        self.btn_outro_edit.clicked.connect(lambda: self.open_edit_dialog.emit(self.part_idx))
        outro_row.addWidget(self.btn_outro_edit, stretch=1)

        # Testo in rosso di avviso se una tipologia di outro è modificata e l'altra no
        self.lbl_red_warning = QLabel(red_warning_text)
        self.lbl_red_warning.setStyleSheet("color: #FF5555; font-weight: 700; font-size: 11px;")
        self.lbl_red_warning.setVisible(show_red_warning)
        outro_row.addWidget(self.lbl_red_warning)

        layout.addLayout(outro_row)

    def _on_internal_text_changed(self):
        if self._updating:
            return
        new_txt = self.txt_box.toPlainText()
        self.clip_text = new_txt
        self.text_edited.emit(self.part_idx, new_txt)

    def set_clip_text_silent(self, new_text: str):
        self._updating = True
        self.clip_text = new_text
        self.txt_box.setPlainText(new_text)
        self._updating = False

    def update_outro_display(self, spoken: str, banner: str, show_red_warning: bool, red_warning_text: str):
        self.outro_spoken = spoken
        self.outro_banner = banner
        self.btn_outro_edit.setText(f'🗣️ Outro Spoken: "{spoken}"  |  Banner: "{banner}" ✏️')
        self.lbl_red_warning.setText(red_warning_text)
        self.lbl_red_warning.setVisible(show_red_warning)

    def update_intro_display(self, intro_title: str):
        self.intro_title = intro_title
        self.btn_intro_edit.setText(f'🏷️ Intro: "{intro_title}" ✏️')

    def _copy_text(self, btn: QPushButton):
        clipboard = QApplication.clipboard()
        if clipboard:
            clipboard.setText(self.txt_box.toPlainText())
            btn.setText("✓ Copiato!")
            QTimer.singleShot(1500, lambda: btn.setText("📋 Copia"))


class ClipSplitAnalysisModal(QDialog):
    """
    Finestra Modale Analisi e Suddivisione Clip Avanzata:
    - Almeno 6 righe di testo per clip
    - Titolo del progetto/storia modificabile in tempo reale
    - Spostamento del testo autonomo tra le singole clip (pulsanti frase su/giù e editing live) con adattamento automatico delle statistiche
    - Finestrella di dialogo dedicata per Intro e Outro
    - Salvataggio automatico per singola clip ("senza dover premere nulla"), per tutto il progetto o di default
    - Distinzione rigida tra Outro Intermedie (1..N-1) e Outro Finale (N)
    - Avviso in testo rosso affianco al banner se vi è asimmetria nelle modifiche
    """

    timing_saved = Signal(dict)
    script_updated = Signal(dict)

    def __init__(
        self,
        script_data: Optional[Dict[str, Any]] = None,
        current_timing: Optional[Dict[str, Any]] = None,
        script_repo: Optional[ScriptRepository] = None,
        parent: Optional[QWidget] = None
    ):
        super().__init__(parent)
        self.script_data = script_data or {}
        self.repo = script_repo
        self.chunker = DiscourseCoherenceChunker()
        self.setObjectName("ModalWindow")
        self.setWindowTitle("Analisi & Suddivisione Clip — Parametri Temporali Dinamici")
        self.resize(1180, 800)

        # Parametri temporali correnti
        cur_t = current_timing or {}
        self.target_video_max: float = float(cur_t.get("target_video_max", TARGET_VIDEO_MAX_SEC))
        self.allowed_delta: float = float(cur_t.get("allowed_delta_sec", ALLOWED_CHUNKING_DELTA_SEC))
        self.wps: float = float(cur_t.get("wps", DEFAULT_WPS))
        self.padding_intro: float = float(cur_t.get("padding_intro_sec", PADDING_INTRO_SEC))
        self.padding_outro: float = float(cur_t.get("padding_outro_sec", PADDING_OUTRO_SEC))
        self.outro_pause: float = float(cur_t.get("outro_pause_sec", OUTRO_PAUSE_SEC))

        # Testo e titolo progetto
        raw = self.script_data.get("raw_text") or self.script_data.get("full_text") or ""
        self.full_text: str = raw.strip()
        self.context_title: str = self.script_data.get("context_title", "Nuova Storia")

        if not self.full_text:
            self.full_text = (
                "Deep in the vast expanse of the cosmos, supermassive black holes bend the very fabric of space and time. "
                "Their gravitational pull is so immense that nothing, not even light itself, can escape once past the event horizon. "
                "Scientists have observed stars orbiting these invisible behemoths at astonishing speeds. "
                "However, what happens inside a singularity remains one of the greatest unsolved mysteries of modern physics. "
                "Could black holes be portals to other dimensions, or do they simply hold the ultimate secrets of the universe? "
                "Future space telescopes might finally provide the answers we have sought for generations."
            )

        # Liste di dati per le singole clip
        self.clip_texts: List[str] = []
        self.clip_intros: List[str] = []
        self.clip_outros_spoken: List[str] = []
        self.clip_outros_banner: List[str] = []

        # Tracciamento modifiche outro (per la regola dell'avviso in rosso)
        self.intermediate_outro_modified: bool = False
        self.final_outro_modified: bool = False

        # Template globali correnti
        self.template_intermediate_spoken = "Follow for part {next_part}."
        self.template_intermediate_banner = "Follow for part.{next_part}"
        self.template_final_spoken = "Follow for more."
        self.template_final_banner = "Follow for more!"

        self._updating_controls = False
        self._manual_chunks_mode = False

        self._init_ui()
        self._initial_auto_chunk()

    def _init_ui(self):
        root_layout = QVBoxLayout(self)
        root_layout.setContentsMargins(18, 14, 18, 14)
        root_layout.setSpacing(10)

        # 1. Barra Superiore Header
        top_bar = QHBoxLayout()
        title_box = QVBoxLayout()
        title_lbl = QLabel("ANALISI & SUDDIVISIONE CLIP — EDITOR AVANZATO")
        title_lbl.setObjectName("SectionHeader")
        subtitle_lbl = QLabel(
            "Modifica il testo tra le clip, personalizza titoli, Intro e Outro con salvataggio per singola clip o globale."
        )
        subtitle_lbl.setObjectName("HelperText")
        title_box.addWidget(title_lbl)
        title_box.addWidget(subtitle_lbl)

        btn_reset = QPushButton("🔄 Reset Default")
        btn_reset.setToolTip("Ripristina le costanti temporali standard ottimali (45s, ±7s, 2.50 WPS, 1.0s/1.0s)")
        btn_reset.clicked.connect(self._reset_to_defaults)

        btn_close = QPushButton("✓ Salva & Chiudi")
        btn_close.setToolTip("Salva le modifiche apportate e aggiorna la schermata principale")
        btn_close.clicked.connect(self._on_save_applied)

        top_bar.addLayout(title_box)
        top_bar.addStretch()
        top_bar.addWidget(btn_reset)
        top_bar.addWidget(btn_close)
        root_layout.addLayout(top_bar)

        # 2. Splitter Orizzontale (Sinistra: Parametri & Statistiche, Destra: Titolo, Testo & Clip)
        main_splitter = QSplitter(Qt.Horizontal)

        # ==========================================
        # PANNELLO SINISTRO (PARAMETRI & STATISTICHE)
        # ==========================================
        left_container = QWidget()
        left_layout = QVBoxLayout(left_container)
        left_layout.setContentsMargins(0, 0, 8, 0)
        left_layout.setSpacing(10)

        # CARD 1: Parametri Temporali
        timing_card = QFrame()
        timing_card.setObjectName("InnerCard")
        tc_layout = QVBoxLayout(timing_card)
        tc_layout.setContentsMargins(12, 10, 12, 10)
        tc_layout.setSpacing(7)

        lbl_timing_head = QLabel("⚙️ PARAMETRI TEMPORALI DINAMICI")
        lbl_timing_head.setStyleSheet("font-weight: 700; font-size: 12px; color: #E2E6EF;")
        tc_layout.addWidget(lbl_timing_head)

        # Preset Rapidi
        preset_row = QHBoxLayout()
        btn_p45 = QPushButton("45s Standard")
        btn_p45.clicked.connect(lambda: self._apply_preset(45.0, 7.0, 2.50, 1.0, 1.0, 1.0))
        btn_p30 = QPushButton("30s Rapido")
        btn_p30.clicked.connect(lambda: self._apply_preset(30.0, 5.0, 2.65, 0.8, 0.8, 0.8))
        btn_p60 = QPushButton("60s Lungo")
        btn_p60.clicked.connect(lambda: self._apply_preset(60.0, 8.0, 2.40, 1.0, 1.2, 1.0))
        btn_p15 = QPushButton("15s Flash")
        btn_p15.clicked.connect(lambda: self._apply_preset(15.0, 3.0, 2.80, 0.5, 0.5, 0.5))

        for b in [btn_p45, btn_p30, btn_p60, btn_p15]:
            b.setStyleSheet("font-size: 10px; padding: 3px 6px;")
            preset_row.addWidget(b)
        tc_layout.addLayout(preset_row)

        self.slider_target, self.spin_target = self._create_slider_spin_pair(
            min_val=15.0, max_val=90.0, step=0.5, init_val=self.target_video_max, on_change=self._on_target_changed
        )
        tc_layout.addLayout(self._wrap_param_row("Durata Max Video (s):", self.slider_target, self.spin_target))

        self.slider_delta, self.spin_delta = self._create_slider_spin_pair(
            min_val=2.0, max_val=15.0, step=0.5, init_val=self.allowed_delta, on_change=self._on_delta_changed
        )
        tc_layout.addLayout(self._wrap_param_row("Tolleranza Taglio ±Δ (s):", self.slider_delta, self.spin_delta))

        self.slider_wps, self.spin_wps = self._create_slider_spin_pair(
            min_val=1.80, max_val=3.50, step=0.05, init_val=self.wps, on_change=self._on_wps_changed
        )
        self.lbl_wpm_hint = QLabel(f"~{int(self.wps * 60)} WPM")
        self.lbl_wpm_hint.setStyleSheet("color: #BFA175; font-size: 11px; font-weight: 600;")
        tc_layout.addLayout(self._wrap_param_row("Velocità Voce (WPS):", self.slider_wps, self.spin_wps, extra_widget=self.lbl_wpm_hint))

        self.slider_intro, self.spin_intro = self._create_slider_spin_pair(
            min_val=0.0, max_val=3.0, step=0.1, init_val=self.padding_intro, on_change=self._on_intro_changed
        )
        tc_layout.addLayout(self._wrap_param_row("Padding Intro Video (s):", self.slider_intro, self.spin_intro))

        self.slider_outro, self.spin_outro = self._create_slider_spin_pair(
            min_val=0.0, max_val=3.0, step=0.1, init_val=self.padding_outro, on_change=self._on_outro_changed
        )
        tc_layout.addLayout(self._wrap_param_row("Padding Outro Video (s):", self.slider_outro, self.spin_outro))

        self.slider_pause, self.spin_pause = self._create_slider_spin_pair(
            min_val=0.0, max_val=2.5, step=0.1, init_val=self.outro_pause, on_change=self._on_pause_changed
        )
        tc_layout.addLayout(self._wrap_param_row("Pausa Silenzio Outro (s):", self.slider_pause, self.spin_pause))

        self.banner_window = QLabel("")
        self.banner_window.setStyleSheet(
            "background-color: #181A20; border: 1px solid #343946; border-radius: 5px; "
            "padding: 5px 8px; color: #729B84; font-size: 11px; font-weight: 600;"
        )
        tc_layout.addWidget(self.banner_window)
        left_layout.addWidget(timing_card)

        # CARD 2: Statistiche Complessive
        stats_card = QFrame()
        stats_card.setObjectName("InnerCard")
        sc_layout = QVBoxLayout(stats_card)
        sc_layout.setContentsMargins(12, 10, 12, 10)
        sc_layout.setSpacing(5)

        lbl_stats_head = QLabel("📊 STATISTICHE GLOBALI SCRIPT")
        lbl_stats_head.setStyleSheet("font-weight: 700; font-size: 12px; color: #E2E6EF;")
        sc_layout.addWidget(lbl_stats_head)

        self.lbl_stat_clips = QLabel("Numero Clip Totali: 0")
        self.lbl_stat_tot_video = QLabel("Durata Totale Video: ~0.0 s")
        self.lbl_stat_tot_voice = QLabel("Durata Totale Voce: ~0.0 s")
        self.lbl_stat_avg_clip = QLabel("Durata Media per Clip: ~0.0 s")
        self.lbl_stat_words = QLabel("Parole / Caratteri Totali: 0 / 0")

        for lbl in [self.lbl_stat_clips, self.lbl_stat_tot_video, self.lbl_stat_tot_voice, self.lbl_stat_avg_clip, self.lbl_stat_words]:
            lbl.setStyleSheet("color: #DCE0EA; font-size: 11px;")
            sc_layout.addWidget(lbl)

        left_layout.addWidget(stats_card)

        self.btn_apply = QPushButton("💾 Salva & Applica alla Produzione")
        self.btn_apply.setObjectName("PrimaryButton")
        self.btn_apply.setStyleSheet("font-weight: 700; padding: 10px; font-size: 13px;")
        self.btn_apply.clicked.connect(self._on_save_applied)
        left_layout.addWidget(self.btn_apply)

        left_layout.addStretch()
        main_splitter.addWidget(left_container)

        # ==========================================
        # PANNELLO DESTRO (TITOLO, SORGENTE & CLIP)
        # ==========================================
        right_container = QWidget()
        right_layout = QVBoxLayout(right_container)
        right_layout.setContentsMargins(8, 0, 0, 0)
        right_layout.setSpacing(8)

        # Box Titolo Progetto & Contesto (MODIFICABILE DALL'UTENTE)
        title_card = QFrame()
        title_card.setObjectName("InnerCard")
        tc_box = QHBoxLayout(title_card)
        tc_box.setContentsMargins(10, 6, 10, 6)
        tc_box.setSpacing(8)

        lbl_t = QLabel("TITOLO PROGETTO / SHORT:")
        lbl_t.setStyleSheet("font-weight: 700; font-size: 11px; color: #BFA175;")
        self.txt_project_title = QLineEdit(self.context_title)
        self.txt_project_title.setStyleSheet("font-size: 12px; font-weight: 600; padding: 4px;")
        self.txt_project_title.textChanged.connect(self._on_project_title_changed)

        tc_box.addWidget(lbl_t)
        tc_box.addWidget(self.txt_project_title, stretch=1)
        right_layout.addWidget(title_card)

        # Barra Azioni Clip (Aggiungi clip, Ricalcola automatico)
        clip_bar = QHBoxLayout()
        self.lbl_clips_header = QLabel("SUDDIVISIONE CLIP IN TEMPO REALE")
        self.lbl_clips_header.setObjectName("SectionHeader")

        self.btn_add_clip = QPushButton("➕ Aggiungi Nuova Clip")
        self.btn_add_clip.setStyleSheet("font-size: 11px; padding: 3px 8px;")
        self.btn_add_clip.clicked.connect(self._add_new_empty_clip)

        self.btn_rechunk = QPushButton("🔄 Ricalcola Suddivisione Automatica")
        self.btn_rechunk.setStyleSheet("font-size: 11px; padding: 3px 8px;")
        self.btn_rechunk.clicked.connect(self._force_rechunk)

        clip_bar.addWidget(self.lbl_clips_header)
        clip_bar.addStretch()
        clip_bar.addWidget(self.btn_add_clip)
        clip_bar.addWidget(self.btn_rechunk)
        right_layout.addLayout(clip_bar)

        # ScrollArea con le Clip
        self.scroll_area = QScrollArea()
        self.scroll_area.setWidgetResizable(True)
        self.scroll_area.setObjectName("ClipsScrollArea")
        self.scroll_area.setStyleSheet("background-color: transparent; border: none;")

        self.clips_container = QWidget()
        self.clips_layout = QVBoxLayout(self.clips_container)
        self.clips_layout.setContentsMargins(0, 0, 4, 0)
        self.clips_layout.setSpacing(8)
        self.clips_layout.addStretch()

        self.scroll_area.setWidget(self.clips_container)
        right_layout.addWidget(self.scroll_area, stretch=1)

        main_splitter.addWidget(right_container)
        main_splitter.setStretchFactor(0, 38)
        main_splitter.setStretchFactor(1, 62)

        root_layout.addWidget(main_splitter, stretch=1)

    # --- CONTROLLI SLIDER/SPINBOX ---

    def _create_slider_spin_pair(self, min_val: float, max_val: float, step: float, init_val: float, on_change):
        spin = QDoubleSpinBox()
        spin.setRange(min_val, max_val)
        spin.setSingleStep(step)
        spin.setDecimals(2 if step < 0.1 else 1)
        spin.setValue(init_val)
        spin.setFixedWidth(68)
        spin.setStyleSheet("background-color: #181A20; color: #DCE0EA; border: 1px solid #343946; border-radius: 4px; padding: 2px;")

        slider = QSlider(Qt.Horizontal)
        steps_count = int(round((max_val - min_val) / step))
        slider.setRange(0, steps_count)
        cur_step = int(round((init_val - min_val) / step))
        slider.setValue(cur_step)

        def _on_slider(val):
            if self._updating_controls:
                return
            new_v = round(min_val + val * step, 2)
            self._updating_controls = True
            spin.setValue(new_v)
            self._updating_controls = False
            on_change(new_v)

        def _on_spin(new_v):
            if self._updating_controls:
                return
            new_step = int(round((new_v - min_val) / step))
            self._updating_controls = True
            slider.setValue(new_step)
            self._updating_controls = False
            on_change(new_v)

        slider.valueChanged.connect(_on_slider)
        spin.valueChanged.connect(_on_spin)
        return slider, spin

    def _wrap_param_row(self, title: str, slider: QSlider, spin: QDoubleSpinBox, extra_widget: Optional[QWidget] = None):
        row = QVBoxLayout()
        row.setSpacing(2)
        top = QHBoxLayout()
        lbl = QLabel(title)
        lbl.setStyleSheet("font-size: 11px; color: #DCE0EA;")
        top.addWidget(lbl)
        top.addStretch()
        if extra_widget:
            top.addWidget(extra_widget)
        top.addWidget(spin)
        row.addLayout(top)
        row.addWidget(slider)
        return row

    def _on_target_changed(self, val: float):
        self.target_video_max = val
        self._on_timing_param_changed()

    def _on_delta_changed(self, val: float):
        self.allowed_delta = val
        self._on_timing_param_changed()

    def _on_wps_changed(self, val: float):
        self.wps = val
        self.lbl_wpm_hint.setText(f"~{int(val * 60)} WPM")
        self._on_timing_param_changed()

    def _on_intro_changed(self, val: float):
        self.padding_intro = val
        self._on_timing_param_changed()

    def _on_outro_changed(self, val: float):
        self.padding_outro = val
        self._on_timing_param_changed()

    def _on_pause_changed(self, val: float):
        self.outro_pause = val
        self._on_timing_param_changed()

    def _on_project_title_changed(self, new_title: str):
        self.context_title = new_title.strip()
        # Aggiorna il titolo intro delle clip se usano il default
        total = len(self.clip_texts)
        for i in range(total):
            if i >= len(self.clip_intros) or not self.clip_intros[i] or "part." in self.clip_intros[i]:
                self.clip_intros[i] = f"{self.context_title} part.{i + 1}"
        self._refresh_clip_cards_display()

    def _apply_preset(self, target: float, delta: float, wps: float, intro: float, outro: float, pause: float):
        self._updating_controls = True
        self.target_video_max = target
        self.allowed_delta = delta
        self.wps = wps
        self.padding_intro = intro
        self.padding_outro = outro
        self.outro_pause = pause

        self.spin_target.setValue(target)
        self.spin_delta.setValue(delta)
        self.spin_wps.setValue(wps)
        self.spin_intro.setValue(intro)
        self.spin_outro.setValue(outro)
        self.spin_pause.setValue(pause)

        for sl, sp, v in [
            (self.slider_target, self.spin_target, target),
            (self.slider_delta, self.spin_delta, delta),
            (self.slider_wps, self.spin_wps, wps),
            (self.slider_intro, self.spin_intro, intro),
            (self.slider_outro, self.spin_outro, outro),
            (self.slider_pause, self.spin_pause, pause)
        ]:
            st = int(round((v - sp.minimum()) / sp.singleStep()))
            sl.setValue(st)

        self.lbl_wpm_hint.setText(f"~{int(wps * 60)} WPM")
        self._updating_controls = False
        self._on_timing_param_changed()

    def _reset_to_defaults(self):
        self._apply_preset(
            TARGET_VIDEO_MAX_SEC, ALLOWED_CHUNKING_DELTA_SEC, DEFAULT_WPS,
            PADDING_INTRO_SEC, PADDING_OUTRO_SEC, OUTRO_PAUSE_SEC
        )

    def _on_timing_param_changed(self):
        if not self._manual_chunks_mode:
            self._initial_auto_chunk()
        else:
            self._recalculate_existing_chunks()

    # --- LOGICA CHUNKING & MODIFICA CLIP ---

    def _initial_auto_chunk(self):
        """Esegue il chunking automatico basato sulle regole discorsive."""
        text = self.full_text.strip()
        total_padding = self.padding_intro + self.padding_outro
        chunks = self.chunker.chunk_story_coherently(
            text,
            target_video_max=self.target_video_max,
            allowed_delta_sec=self.allowed_delta,
            avg_wps=self.wps,
            total_padding_sec=total_padding
        )
        if not chunks:
            chunks = [text] if text else [""]

        self.clip_texts = chunks
        total = len(chunks)

        # Popola intro e outro con i template standard se non già personalizzati
        self.clip_intros = [f"{self.context_title} part.{i + 1}" for i in range(total)]
        self.clip_outros_spoken = []
        self.clip_outros_banner = []

        for i in range(total):
            part_num = i + 1
            if part_num < total:
                spk = self.template_intermediate_spoken.format(next_part=part_num + 1)
                bnr = self.template_intermediate_banner.format(next_part=part_num + 1)
            else:
                spk = self.template_final_spoken
                bnr = self.template_final_banner
            self.clip_outros_spoken.append(spk)
            self.clip_outros_banner.append(bnr)

        self._refresh_clip_cards_display()

    def _force_rechunk(self):
        self._manual_chunks_mode = False
        self._initial_auto_chunk()

    def _recalculate_existing_chunks(self):
        """Ricalcola le durate e metriche delle clip correnti senza distruggere i tagli manuali dell'utente."""
        total = len(self.clip_texts)
        # Assicura liste di intro e outro allineate
        while len(self.clip_intros) < total:
            self.clip_intros.append(f"{self.context_title} part.{len(self.clip_intros) + 1}")
        while len(self.clip_outros_spoken) < total:
            idx = len(self.clip_outros_spoken) + 1
            if idx < total:
                self.clip_outros_spoken.append(self.template_intermediate_spoken.format(next_part=idx + 1))
                self.clip_outros_banner.append(self.template_intermediate_banner.format(next_part=idx + 1))
            else:
                self.clip_outros_spoken.append(self.template_final_spoken)
                self.clip_outros_banner.append(self.template_final_banner)

        # Taglia eccedenze
        self.clip_intros = self.clip_intros[:total]
        self.clip_outros_spoken = self.clip_outros_spoken[:total]
        self.clip_outros_banner = self.clip_outros_banner[:total]

        self._refresh_clip_cards_display()

    # --- SPOSTAMENTO AUTONOMO DEL TESTO TRA CLIP ---

    def _on_clip_text_edited(self, part_idx: int, new_text: str):
        idx = part_idx - 1
        if 0 <= idx < len(self.clip_texts):
            self.clip_texts[idx] = new_text
            self._manual_chunks_mode = True
            self.full_text = " ".join([c.strip() for c in self.clip_texts if c.strip()])
            self._update_stats_only()

    def _move_first_sentence_up(self, part_idx: int):
        idx = part_idx - 1
        if idx <= 0:
            return
        curr_text = self.clip_texts[idx].strip()
        if not curr_text:
            return

        sentences = re.split(r'(?<=[.!?])\s+', curr_text)
        if not sentences:
            return

        first_sent = sentences[0]
        remaining = " ".join(sentences[1:])

        prev_idx = idx - 1
        self.clip_texts[prev_idx] = (self.clip_texts[prev_idx].strip() + " " + first_sent).strip()
        self.clip_texts[idx] = remaining
        self._manual_chunks_mode = True
        self._refresh_clip_cards_display()

    def _move_last_sentence_down(self, part_idx: int):
        idx = part_idx - 1
        if idx >= len(self.clip_texts) - 1:
            return
        curr_text = self.clip_texts[idx].strip()
        if not curr_text:
            return

        sentences = re.split(r'(?<=[.!?])\s+', curr_text)
        if not sentences:
            return

        last_sent = sentences[-1]
        remaining = " ".join(sentences[:-1])

        next_idx = idx + 1
        self.clip_texts[next_idx] = (last_sent + " " + self.clip_texts[next_idx].strip()).strip()
        self.clip_texts[idx] = remaining
        self._manual_chunks_mode = True
        self._refresh_clip_cards_display()

    def _merge_clip_with_next(self, part_idx: int):
        idx = part_idx - 1
        if idx >= len(self.clip_texts) - 1:
            return
        merged = (self.clip_texts[idx].strip() + " " + self.clip_texts[idx + 1].strip()).strip()
        self.clip_texts[idx] = merged
        self.clip_texts.pop(idx + 1)
        self.clip_intros.pop(idx + 1)
        self.clip_outros_spoken.pop(idx + 1)
        self.clip_outros_banner.pop(idx + 1)
        self._manual_chunks_mode = True
        self._recalculate_existing_chunks()

    def _delete_clip(self, part_idx: int):
        idx = part_idx - 1
        if 0 <= idx < len(self.clip_texts) and len(self.clip_texts) > 1:
            self.clip_texts.pop(idx)
            self.clip_intros.pop(idx)
            self.clip_outros_spoken.pop(idx)
            self.clip_outros_banner.pop(idx)
            self._manual_chunks_mode = True
            self._recalculate_existing_chunks()

    def _add_new_empty_clip(self):
        new_idx = len(self.clip_texts) + 1
        self.clip_texts.append("Nuovo testo clip...")
        self.clip_intros.append(f"{self.context_title} part.{new_idx}")
        self.clip_outros_spoken.append(self.template_final_spoken)
        self.clip_outros_banner.append(self.template_final_banner)
        self._manual_chunks_mode = True
        self._recalculate_existing_chunks()

    # --- MODIFICA INTRO & OUTRO CON DIALOGO DEDICATO ---

    def _open_edit_dialog_for_clip(self, part_idx: int):
        idx = part_idx - 1
        total = len(self.clip_texts)
        if not (0 <= idx < total):
            return

        is_final = (part_idx == total)
        dlg = IntroOutroEditDialog(
            clip_idx=part_idx,
            total_clips=total,
            is_final=is_final,
            intro_title=self.clip_intros[idx],
            outro_spoken=self.clip_outros_spoken[idx],
            outro_banner=self.clip_outros_banner[idx],
            parent=self
        )

        dlg.save_single.connect(lambda p: self._on_single_clip_updated(idx, p))
        dlg.save_all_project.connect(self._on_apply_all_project)
        dlg.save_default_global.connect(self._on_save_default_global)
        dlg.exec()

    def _on_single_clip_updated(self, idx: int, payload: dict):
        """Salva per quella clip senza dover premere nulla."""
        self.clip_intros[idx] = payload["intro"]
        self.clip_outros_spoken[idx] = payload["spoken"]
        self.clip_outros_banner[idx] = payload["banner"]

        # Tracciamento modifiche
        is_final = (idx == len(self.clip_texts) - 1)
        if is_final:
            self.final_outro_modified = True
        else:
            self.intermediate_outro_modified = True

        self._refresh_clip_cards_display()

    def _on_apply_all_project(self, payload: dict):
        """
        Propaga la modifica a tutto il progetto:
        - Se intermedia: modifica SOLO le intermedie (1..N-1) con numerazione progressiva, NON tocca la finale
        - Se finale: modifica SOLO la finale
        """
        is_final = payload["is_final"]
        total = len(self.clip_texts)

        if is_final:
            self.final_outro_modified = True
            # Applica all'ultima clip
            if total > 0:
                self.clip_outros_spoken[-1] = payload["spoken"]
                self.clip_outros_banner[-1] = payload["banner"]
                self.template_final_spoken = payload["spoken"]
                self.template_final_banner = payload["banner"]
        else:
            self.intermediate_outro_modified = True
            raw_spk = payload["spoken"]
            raw_bnr = payload["banner"]

            # Salva come template per le intermedie
            self.template_intermediate_spoken = raw_spk
            self.template_intermediate_banner = raw_bnr

            # Applica a tutte le clip intermedie (0 fino a total-2)
            for i in range(total - 1):
                next_p = i + 2
                spk = raw_spk.replace("{next_part}", str(next_p)) if "{next_part}" in raw_spk else raw_spk
                bnr = raw_bnr.replace("{next_part}", str(next_p)) if "{next_part}" in raw_bnr else raw_bnr
                self.clip_outros_spoken[i] = spk
                self.clip_outros_banner[i] = bnr

        self._refresh_clip_cards_display()

    def _on_save_default_global(self, payload: dict):
        """Salva come default globale rispettando la separazione tra intermedia e finale."""
        is_final = payload["is_final"]
        if is_final:
            self.final_outro_modified = True
            self.template_final_spoken = payload["spoken"]
            self.template_final_banner = payload["banner"]
        else:
            self.intermediate_outro_modified = True
            self.template_intermediate_spoken = payload["spoken"]
            self.template_intermediate_banner = payload["banner"]

        self._refresh_clip_cards_display()

    # --- AGGIORNAMENTO GRAFICO CARD & REGOLA AVVISO IN ROSSO ---

    def _refresh_clip_cards_display(self):
        # 1. Pulisce le card correnti
        while self.clips_layout.count() > 1:
            child = self.clips_layout.takeAt(0)
            if child.widget():
                child.widget().deleteLater()

        total = len(self.clip_texts)
        self.lbl_clips_header.setText(f"SUDDIVISIONE CLIP IN TEMPO REALE ({total} CLIP)")

        min_video = self.target_video_max - self.allowed_delta
        max_audio = max(5.0, self.target_video_max - (self.padding_intro + self.padding_outro))
        min_audio = max(3.0, max_audio - self.allowed_delta)

        self.banner_window.setText(
            f"🎯 Finestra Video Consentita: {min_video:.1f}s — {self.target_video_max:.1f}s\n"
            f"   (Audio Narrazione: da {min_audio:.1f}s a {max_audio:.1f}s max)"
        )

        # Calcolo logica avviso in rosso:
        # Se c'è asimmetria tra modifiche (una sola tipologia modificata e l'altra no):
        # - Caso A: modificate le intermedie ma la finale no -> mostra testo rosso sull'ultima clip
        # - Caso B: modificata la finale ma le intermedie no -> mostra testo rosso sulle clip intermedie
        show_warning_on_final = (self.intermediate_outro_modified and not self.final_outro_modified and total > 1)
        show_warning_on_intermediates = (not self.intermediate_outro_modified and self.final_outro_modified and total > 1)

        tot_video_time = 0.0
        tot_voice_time = 0.0
        tot_words = 0
        tot_chars = 0

        for i, text in enumerate(self.clip_texts):
            part_num = i + 1
            is_final = (part_num == total)
            words = len(text.split())
            chars = len(text)
            tot_words += words
            tot_chars += chars

            narr_dur = round(words / self.wps, 1)
            spk = self.clip_outros_spoken[i] if i < len(self.clip_outros_spoken) else (self.template_final_spoken if is_final else f"Follow for part {part_num + 1}.")
            bnr = self.clip_outros_banner[i] if i < len(self.clip_outros_banner) else (self.template_final_banner if is_final else f"Follow for part.{part_num + 1}")
            intro_t = self.clip_intros[i] if i < len(self.clip_intros) else f"{self.context_title} part.{part_num}"

            outro_dur = round(len(spk.split()) / self.wps, 1)
            clip_voice = narr_dur + self.outro_pause + outro_dur
            clip_video = clip_voice + self.padding_intro + self.padding_outro

            tot_voice_time += clip_voice
            tot_video_time += clip_video

            is_in_range = (clip_video >= min_video - 0.5 and clip_video <= self.target_video_max + 0.5)
            is_short = clip_video < (min_video - 0.5)

            # Determina testo rosso per questa specifica clip
            show_red = False
            red_text = ""
            if is_final and show_warning_on_final:
                show_red = True
                red_text = "⚠️ Outro finale standard non ancora personalizzata!"
            elif (not is_final) and show_warning_on_intermediates:
                show_red = True
                red_text = "⚠️ Outro intermedia non ancora personalizzata!"

            card = ClipCardWidget(
                part_idx=part_num,
                total_parts=total,
                clip_text=text,
                intro_title=intro_t,
                narr_dur=narr_dur,
                outro_dur=outro_dur,
                outro_pause=self.outro_pause,
                padding_intro=self.padding_intro,
                padding_outro=self.padding_outro,
                outro_spoken=spk,
                outro_banner=bnr,
                is_in_range=is_in_range,
                is_short=is_short,
                show_red_warning=show_red,
                red_warning_text=red_text
            )

            # Connessione segnali della card
            card.text_edited.connect(self._on_clip_text_edited)
            card.move_first_sentence_up.connect(self._move_first_sentence_up)
            card.move_last_sentence_down.connect(self._move_last_sentence_down)
            card.merge_with_next.connect(self._merge_clip_with_next)
            card.delete_clip.connect(self._delete_clip)
            card.open_edit_dialog.connect(self._open_edit_dialog_for_clip)

            self.clips_layout.insertWidget(self.clips_layout.count() - 1, card)

        self._update_global_stats_labels(total, tot_words, tot_chars, tot_video_time, tot_voice_time)

    def _update_stats_only(self):
        """Aggiorna solo le etichette statistiche globali (chiamata rapida durante la digitazione)."""
        total = len(self.clip_texts)
        tot_video_time = 0.0
        tot_voice_time = 0.0
        tot_words = 0
        tot_chars = 0

        for i, text in enumerate(self.clip_texts):
            words = len(text.split())
            chars = len(text)
            tot_words += words
            tot_chars += chars
            narr_dur = round(words / self.wps, 1)
            spk = self.clip_outros_spoken[i] if i < len(self.clip_outros_spoken) else ""
            outro_dur = round(len(spk.split()) / self.wps, 1)
            clip_voice = narr_dur + self.outro_pause + outro_dur
            clip_video = clip_voice + self.padding_intro + self.padding_outro
            tot_voice_time += clip_voice
            tot_video_time += clip_video

        self._update_global_stats_labels(total, tot_words, tot_chars, tot_video_time, tot_voice_time)

    def _update_global_stats_labels(self, count: int, words: int, chars: int, tot_vid: float, tot_voice: float):
        avg_dur = (tot_vid / count) if count > 0 else 0.0
        mins = int(tot_vid // 60)
        secs = int(tot_vid % 60)
        time_fmt = f"{mins}m {secs:02d}s" if mins > 0 else f"{tot_vid:.1f}s"

        self.lbl_stat_clips.setText(f"Numero Clip Totali: {count} Short")
        self.lbl_stat_tot_video.setText(f"Durata Totale Video: ~{tot_vid:.1f} s ({time_fmt})")
        self.lbl_stat_tot_voice.setText(f"Durata Totale Voce: ~{tot_voice:.1f} s")
        self.lbl_stat_avg_clip.setText(f"Durata Media per Clip: ~{avg_dur:.1f} s")
        self.lbl_stat_words.setText(f"Parole / Caratteri Totali: {words} / {chars}")

    # --- GETTERS & SALVATAGGIO ALLA PRODUZIONE ---

    def get_context_title(self) -> str:
        return self.context_title

    def get_custom_chunks(self) -> List[str]:
        return [c.strip() for c in self.clip_texts if c.strip()]

    def get_custom_intros(self) -> List[str]:
        return list(self.clip_intros)

    def get_custom_outros(self) -> List[Dict[str, str]]:
        out = []
        for spk, bnr in zip(self.clip_outros_spoken, self.clip_outros_banner):
            out.append({"spoken": spk, "banner": bnr})
        return out

    def get_summary_stats(self) -> Dict[str, Any]:
        """Restituisce le statistiche correnti calcolate nel modale per la sincronizzazione immediata."""
        total = len(self.clip_texts)
        tot_video_time = 0.0
        tot_voice_time = 0.0
        tot_words = 0
        tot_chars = 0
        for i, text in enumerate(self.clip_texts):
            words = len(text.split())
            chars = len(text)
            tot_words += words
            tot_chars += chars
            narr_dur = round(words / self.wps, 1)
            spk = self.clip_outros_spoken[i] if i < len(self.clip_outros_spoken) else ""
            outro_dur = round(len(spk.split()) / self.wps, 1)
            clip_voice = narr_dur + self.outro_pause + outro_dur
            clip_video = clip_voice + self.padding_intro + self.padding_outro
            tot_voice_time += clip_voice
            tot_video_time += clip_video
        return {
            "num_clips": total,
            "word_count": tot_words,
            "char_count": tot_chars,
            "tot_video_sec": round(tot_video_time, 1),
            "tot_voice_sec": round(tot_voice_time, 1),
            "avg_clip_sec": round(tot_video_time / max(1, total), 1),
            "context_title": self.context_title,
            "wps": self.wps,
            "custom_chunks": self.get_custom_chunks(),
            "custom_intros": self.get_custom_intros(),
            "custom_outros": self.get_custom_outros(),
        }

    def get_timing_config(self) -> Dict[str, Any]:
        stats = self.get_summary_stats()
        return {
            "target_video_max": self.target_video_max,
            "allowed_delta_sec": self.allowed_delta,
            "wps": self.wps,
            "padding_intro_sec": self.padding_intro,
            "padding_outro_sec": self.padding_outro,
            "outro_pause_sec": self.outro_pause,
            "custom_chunks": self.get_custom_chunks(),
            "custom_intros": self.get_custom_intros(),
            "custom_outros": self.get_custom_outros(),
            "total_video_duration_sec": stats["tot_video_sec"],
            "num_clips": stats["num_clips"]
        }

    def _on_save_applied(self):
        cfg = self.get_timing_config()
        stats = self.get_summary_stats()
        self.timing_saved.emit(cfg)
        self.script_updated.emit(stats)
        self.accept()

    def closeEvent(self, event):
        self._on_save_applied()
        super().closeEvent(event)
