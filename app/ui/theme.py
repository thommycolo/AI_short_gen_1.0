"""AI Short Generator 1.0 - Design System Tokens & QSS Theme Stylesheet"""

class ThemeTokens:
    # Palette Scura Morbida (Zero Nero Puro #000000)
    BG_BASE = "#181A20"
    BG_SURFACE = "#21242C"
    BG_SURFACE_ELEVATED = "#2A2E38"
    BG_INTERACTIVE_HOVER = "#333845"

    BORDER_SUBTLE = "#343946"
    BORDER_FOCUS = "#4C5466"

    # Tipografia Morbida Non-Fluo
    TEXT_PRIMARY = "#DCE0EA"
    TEXT_SECONDARY = "#949CAE"
    TEXT_MUTED = "#666E7F"

    # Accenti Delicati
    ACCENT_INDIGO = "#6B82A6"
    ACCENT_INDIGO_HOVER = "#7E95BC"
    ACCENT_WARM_SAND = "#BFA175"  # Oro sabbia per parole attive

    # Colori Funzionali Non-Fluo
    STATUS_AVAILABLE = "#729B84"   # Salvia morbido
    STATUS_AVAILABLE_BG = "#22382D"
    STATUS_LOCKED_USED = "#8C94A6" # Ardesia
    STATUS_LOCKED_BG = "#282C37"
    STATUS_WARNING = "#C4A36B"     # Ambra morbido
    STATUS_WARNING_BG = "#3D3425"
    STATUS_ERROR = "#AA7373"       # Rosa antico
    STATUS_ERROR_BG = "#3D2525"


QSS_STYLESHEET = """
/* ====================================================================
   AI SHORT GENERATOR 1.0 - THEME STYLESHEET (PySide6 / Qt)
   Palette scura riposante, zero nero puro (#000000), zero colori fluo
   ==================================================================== */

QWidget {
    color: #DCE0EA;
    font-family: "Segoe UI Variable", "Segoe UI", "Inter", sans-serif;
    font-size: 10pt;
    selection-background-color: #6B82A6;
    selection-color: #FFFFFF;
    border: none;
}

QMainWindow, QWidget#CentralWidget {
    background-color: #181A20;
}

/* CARD SUPERFICIALI */
QFrame#CardSurface {
    background-color: #21242C;
    border: 1px solid #343946;
    border-radius: 8px;
    padding: 12px;
}

QFrame#InnerCard {
    background-color: #1E2128;
    border: 1px solid #2F3440;
    border-radius: 6px;
    padding: 8px;
}

/* FINESTRE MODALI & CASSETTI */
QDialog#ModalWindow, QDialog {
    background-color: #252933;
    color: #DCE0EA;
    border: 1px solid #3C4252;
}

QFrame#SideDrawer {
    background-color: #252933;
    border-left: 1px solid #3C4252;
}

/* ETICHETTE */
QLabel {
    background-color: transparent;
}

QLabel#SectionHeader {
    font-size: 14px;
    font-weight: 600;
    color: #E2E6EF;
}

QLabel#HelperText {
    font-size: 11px;
    color: #949CAE;
}

QLabel#MetricValue {
    font-size: 15px;
    font-weight: 600;
    color: #BFA175;
}

/* BADGE DI STATO DEGLI SCRIPT */
QLabel#BadgeAvailable {
    background-color: #22382D;
    color: #729B84;
    border: 1px solid #2D4C3C;
    border-radius: 4px;
    padding: 3px 8px;
    font-size: 11px;
    font-weight: 600;
}

QLabel#BadgeUsedLock {
    background-color: #282C37;
    color: #8C94A6;
    border: 1px solid #383E4E;
    border-radius: 4px;
    padding: 3px 8px;
    font-size: 11px;
    font-weight: 600;
}

QLabel#BadgeWarning {
    background-color: #3D3425;
    color: #C4A36B;
    border: 1px solid #54462E;
    border-radius: 4px;
    padding: 3px 8px;
    font-size: 11px;
    font-weight: 600;
}

/* CAMPI INPUT E TEXT EDIT */
QTextEdit, QLineEdit, QPlainTextEdit {
    background-color: #1A1C22;
    color: #DCE0EA;
    border: 1px solid #343946;
    border-radius: 6px;
    padding: 8px;
}

QTextEdit:focus, QLineEdit:focus, QPlainTextEdit:focus {
    border: 1px solid #6B82A6;
    background-color: #1D2027;
}

/* COMBO BOX */
QComboBox {
    background-color: #21242C;
    color: #DCE0EA;
    border: 1px solid #343946;
    border-radius: 6px;
    padding: 6px 12px;
    min-height: 20px;
}

QComboBox:hover {
    border-color: #4C5466;
    background-color: #282C37;
}

QComboBox::drop-down {
    border: none;
    width: 20px;
}

QComboBox QAbstractItemView {
    background-color: #252933;
    color: #DCE0EA;
    border: 1px solid #3C4252;
    selection-background-color: #6B82A6;
    selection-color: #FFFFFF;
}

/* PULSANTI */
QPushButton {
    background-color: #2B303C;
    color: #DCE0EA;
    border: 1px solid #3A4150;
    border-radius: 6px;
    padding: 7px 14px;
    font-weight: 500;
}

QPushButton:hover {
    background-color: #353B4A;
    border-color: #4C5568;
}

QPushButton:pressed {
    background-color: #222630;
}

QPushButton:disabled {
    background-color: #22252D;
    color: #5A6273;
    border-color: #2D323E;
}

QPushButton#PrimaryButton {
    background-color: #4B5E7D;
    color: #FFFFFF;
    border: 1px solid #5C7296;
    font-weight: 600;
}

QPushButton#PrimaryButton:hover {
    background-color: #566C8F;
    border-color: #6B84AE;
}

QPushButton#SuccessButton {
    background-color: #2F543F;
    color: #D8F2E2;
    border: 1px solid #3D6B51;
    font-weight: 600;
}

QPushButton#SuccessButton:hover {
    background-color: #38634B;
}

QPushButton#DangerButton {
    background-color: #5E3232;
    color: #FAD4D4;
    border: 1px solid #754040;
    font-weight: 600;
}

QPushButton#DangerButton:hover {
    background-color: #6E3B3B;
}

/* TAB BAR */
QTabWidget::pane {
    border: 1px solid #343946;
    border-radius: 6px;
    background-color: #21242C;
    top: -1px;
}

QTabBar::tab {
    background-color: #1E2129;
    color: #949CAE;
    padding: 8px 16px;
    border-top-left-radius: 6px;
    border-top-right-radius: 6px;
    margin-right: 2px;
}

QTabBar::tab:selected {
    background-color: #21242C;
    color: #DCE0EA;
    border: 1px solid #343946;
    border-bottom: 1px solid #21242C;
}

QTabBar::tab:hover:!selected {
    background-color: #2A2E38;
}

/* SLIDERS E PROGRESS BAR */
QSlider::groove:horizontal {
    height: 4px;
    background: #2D323E;
    border-radius: 2px;
}

QSlider::sub-page:horizontal {
    background: #6B82A6;
    border-radius: 2px;
}

QSlider::handle:horizontal {
    background: #B4BCCB;
    border: 1px solid #4C5568;
    width: 14px;
    margin-top: -5px;
    margin-bottom: -5px;
    border-radius: 7px;
}

QProgressBar {
    background-color: #1E2128;
    border: 1px solid #343946;
    border-radius: 4px;
    text-align: center;
    color: #DCE0EA;
    font-size: 11px;
    min-height: 14px;
}

QProgressBar::chunk {
    background-color: #6B82A6;
    border-radius: 3px;
}

/* SCROLL AREA */
QScrollArea {
    background-color: transparent;
    border: none;
}

QScrollArea > QWidget > QWidget {
    background-color: transparent;
}

/* SCROLL BARS */
QScrollBar:vertical {
    border: none;
    background: #181A20;
    width: 8px;
    margin: 0px;
}

QScrollBar::handle:vertical {
    background: #343946;
    min-height: 20px;
    border-radius: 4px;
}

QScrollBar::handle:vertical:hover {
    background: #4C5466;
}

QScrollBar::add-line:vertical, QScrollBar::sub-line:vertical {
    height: 0px;
}

/* TABLE WIDGET & LIST WIDGET */
QTableWidget, QListWidget {
    background-color: #1A1C22;
    border: 1px solid #343946;
    border-radius: 6px;
    gridline-color: #2B303C;
}

QHeaderView::section {
    background-color: #21242C;
    color: #949CAE;
    border: none;
    border-bottom: 1px solid #343946;
    padding: 6px;
    font-weight: 600;
    font-size: 12px;
}

QTableWidget::item, QListWidget::item {
    padding: 6px;
}

QTableWidget::item:selected, QListWidget::item:selected {
    background-color: #2D3342;
    color: #FFFFFF;
}

/* CHECKBOX */
QCheckBox {
    spacing: 8px;
    color: #DCE0EA;
    background-color: transparent;
}

QCheckBox::indicator {
    width: 16px;
    height: 16px;
    border-radius: 3px;
    border: 1px solid #4C5466;
    background-color: #1E2128;
}

QCheckBox::indicator:checked {
    background-color: #6B82A6;
    border-color: #7E95BC;
    image: url("assets/icons/check.png");
}

/* RADIO BUTTON CON ICONA A SPUNTA (NON CERCHIO) */
QRadioButton {
    spacing: 10px;
    color: #DCE0EA;
    font-size: 12px;
    background-color: transparent;
}

QRadioButton::indicator {
    width: 18px;
    height: 18px;
    border-radius: 4px;
    border: 1px solid #4C5466;
    background-color: #1E2128;
}

QRadioButton::indicator:hover {
    border-color: #6B82A6;
    background-color: #232731;
}

QRadioButton::indicator:checked {
    background-color: #2F543F;
    border: 1px solid #528A68;
    image: url("assets/icons/check.png");
}
"""

