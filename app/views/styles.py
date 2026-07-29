# Vercel Geist & Enterprise Design System — PySide6 Qt6 QSS
# IMPORTANT: Qt QSS uses property selectors [class="x"], NOT CSS dot-notation ".x"

_BASE = """
/* ════════════════ Global Reset & Typography ════════════════ */
QWidget {{
    color: {text};
    background-color: {bg};
    font-family: 'Geist', 'Outfit', 'Inter', 'Segoe UI', -apple-system, BlinkMacSystemFont, sans-serif;
    font-size: 13px;
    border: none;
    outline: none;
}}

QMainWindow {{
    background-color: {bg};
}}

QDialog {{
    background-color: {bg};
    color: {text};
}}

/* ════════════════ Title Header Bar ════════════════ */
QFrame#titlebar {{
    background-color: {surface};
    border-bottom: 1px solid {border};
}}

QLabel#title_heading {{
    font-size: 15px;
    font-weight: 700;
    color: {text};
    letter-spacing: -0.3px;
}}

QLabel#ver_badge {{
    font-family: 'Geist Mono', 'Consolas', monospace;
    font-size: 11px;
    font-weight: 600;
    color: {muted};
    background-color: {hover};
    border: 1px solid {border};
    border-radius: 6px;
    padding: 2px 8px;
}}

/* ════════════════ Sidebar ════════════════ */
QFrame#sidebar {{
    background-color: {surface};
    border-right: 1px solid {border};
}}

/* Sidebar nav buttons */
QFrame#sidebar > QPushButton {{
    text-align: left;
    padding: 10px 14px;
    border-radius: 8px;
    border: 1px solid transparent;
    background-color: transparent;
    color: {nav_muted};
    font-size: 13px;
    font-weight: 500;
}}
QFrame#sidebar > QPushButton:hover {{
    background-color: {hover};
    color: {text};
    border-color: {border};
}}
QFrame#sidebar > QPushButton:checked {{
    background-color: {card};
    border: 1px solid {border_strong};
    color: {text};
    font-weight: 600;
}}

/* ════════════════ Pane Cards & Bento (g-pane) ════════════════ */
QFrame[class="g-pane"] {{
    background-color: {card};
    border: 1px solid {border};
    border-radius: 12px;
}}

QFrame[class="g-bento-card"] {{
    background-color: {card};
    border: 1px solid {border};
    border-radius: 12px;
    padding: 14px;
}}
QFrame[class="g-bento-card"]:hover {{
    border-color: {border_strong};
}}

/* ════════════════ Group Boxes ════════════════ */
QGroupBox {{
    background-color: {card};
    border: 1px solid {border};
    border-radius: 10px;
    margin-top: 16px;
    padding-top: 20px;
    font-weight: 600;
    color: {text};
}}
QGroupBox::title {{
    subcontrol-origin: margin;
    subcontrol-position: top left;
    left: 14px;
    top: -1px;
    padding: 3px 12px;
    background-color: {card};
    color: {text};
    border: 1px solid {border};
    border-radius: 6px;
    font-size: 11px;
    font-weight: 700;
    letter-spacing: 0.5px;
    text-transform: uppercase;
}}

/* ════════════════ Base Buttons & Pills ════════════════ */
QPushButton {{
    color: {text};
    background-color: {card};
    border: 1px solid {border};
    border-radius: 8px;
    padding: 8px 16px;
    font-weight: 500;
    font-size: 13px;
}}
QPushButton:hover {{
    background-color: {hover};
    border-color: {border_strong};
}}
QPushButton:pressed {{
    background-color: {pressed};
}}
QPushButton:disabled {{
    color: {muted};
    background-color: {surface};
    border-color: {border};
}}

/* Solid / Primary button */
QPushButton[class="g-btn-solid"] {{
    background-color: {ink};
    color: {ink_text};
    font-weight: 600;
    border: 1px solid {ink};
    border-radius: 8px;
    padding: 8px 18px;
}}
QPushButton[class="g-btn-solid"]:hover {{
    background-color: {ink_hover};
    border-color: {ink_hover};
}}
QPushButton[class="g-btn-solid"]:pressed {{
    background-color: {ink_pressed};
}}
QPushButton[class="g-btn-solid"]:disabled {{
    background-color: {muted};
    border-color: {muted};
    color: {surface};
}}

/* Ghost button */
QPushButton[class="g-btn-ghost"] {{
    background-color: transparent;
    color: {text};
    font-weight: 500;
    border: 1px solid {border};
    border-radius: 8px;
    padding: 8px 16px;
}}
QPushButton[class="g-btn-ghost"]:hover {{
    background-color: {hover};
    border-color: {border_strong};
}}

/* Chip / Pill button */
QPushButton[class="g-btn-chip"] {{
    background-color: {chip_bg};
    color: {chip_text};
    font-size: 12px;
    font-weight: 500;
    border-radius: 16px;
    padding: 5px 14px;
    border: 1px solid {border};
}}
QPushButton[class="g-btn-chip"]:hover {{
    background-color: {ink};
    color: {ink_text};
    border-color: {ink};
}}

/* ════════════════ Text Inputs ════════════════ */
QLineEdit {{
    background-color: {input_bg};
    color: {text};
    border: 1px solid {border};
    border-radius: 8px;
    padding: 8px 14px;
    font-size: 13px;
    selection-background-color: {sel_bg};
    selection-color: {sel_text};
}}
QLineEdit:focus {{
    border-color: {ink};
}}
QLineEdit:read-only {{
    color: {muted};
    background-color: {surface};
}}

QPlainTextEdit, QTextEdit {{
    background-color: {input_bg};
    color: {text};
    border: 1px solid {border};
    border-radius: 8px;
    padding: 10px 14px;
    font-size: 13px;
    selection-background-color: {sel_bg};
    selection-color: {sel_text};
}}
QPlainTextEdit:focus, QTextEdit:focus {{
    border-color: {ink};
}}

/* ════════════════ ComboBox ════════════════ */
QComboBox {{
    background-color: {input_bg};
    color: {text};
    border: 1px solid {border};
    border-radius: 8px;
    padding: 6px 14px;
    font-size: 13px;
    min-height: 30px;
}}
QComboBox:hover {{
    border-color: {border_strong};
}}
QComboBox:focus {{
    border-color: {ink};
}}
QComboBox::drop-down {{
    subcontrol-origin: padding;
    subcontrol-position: right center;
    width: 24px;
    border: none;
}}
QComboBox QAbstractItemView {{
    background-color: {card};
    color: {text};
    border: 1px solid {border_strong};
    border-radius: 8px;
    padding: 4px;
    selection-background-color: {ink};
    selection-color: {ink_text};
    outline: none;
}}
QComboBox QAbstractItemView::item {{
    min-height: 32px;
    padding: 4px 12px;
    border-radius: 6px;
    color: {text};
    background-color: {card};
}}
QComboBox QAbstractItemView::item:hover {{
    background-color: {hover};
    color: {text};
}}
QComboBox QAbstractItemView::item:selected {{
    background-color: {ink};
    color: {ink_text};
}}

/* ════════════════ Tab Widget ════════════════ */
QTabWidget::pane {{
    border: 1px solid {border};
    border-radius: 10px;
    background-color: {card};
    top: -1px;
}}
QTabBar::tab {{
    background-color: {surface};
    color: {muted};
    border: 1px solid {border};
    border-bottom: none;
    border-top-left-radius: 8px;
    border-top-right-radius: 8px;
    padding: 9px 18px;
    font-size: 12px;
    font-weight: 500;
    margin-right: 4px;
}}
QTabBar::tab:hover {{
    background-color: {hover};
    color: {text};
}}
QTabBar::tab:selected {{
    background-color: {card};
    color: {text};
    font-weight: 600;
    border-bottom: 2px solid {ink};
}}

/* ════════════════ List & Tree Widgets ════════════════ */
QListWidget, QTreeWidget, QTableView {{
    background-color: {card};
    color: {text};
    border: 1px solid {border};
    border-radius: 8px;
    padding: 4px;
    outline: none;
}}
QListWidget::item, QTreeWidget::item {{
    padding: 8px 12px;
    border-radius: 6px;
    color: {text};
    background-color: transparent;
    font-size: 13px;
}}
QListWidget::item:hover, QTreeWidget::item:hover {{
    background-color: {hover};
    color: {text};
}}
QListWidget::item:selected, QTreeWidget::item:selected {{
    background-color: {item_sel_bg};
    color: {item_sel_text};
    font-weight: 600;
}}

/* ════════════════ Progress Bar ════════════════ */
QProgressBar {{
    background-color: {border};
    border: none;
    border-radius: 4px;
    height: 6px;
    max-height: 6px;
    text-align: center;
    color: transparent;
}}
QProgressBar::chunk {{
    background-color: {ink};
    border-radius: 4px;
}}

/* ════════════════ Splitter ════════════════ */
QSplitter::handle {{
    background-color: {border};
}}
QSplitter::handle:horizontal {{
    width: 2px;
}}
QSplitter::handle:vertical {{
    height: 2px;
}}
QSplitter::handle:hover {{
    background-color: {ink};
}}

/* ════════════════ Check Box ════════════════ */
QCheckBox {{
    color: {text};
    spacing: 8px;
    font-size: 13px;
    background-color: transparent;
}}
QCheckBox::indicator {{
    width: 18px;
    height: 18px;
    border-radius: 5px;
    border: 1.5px solid {border_strong};
    background-color: {input_bg};
}}
QCheckBox::indicator:hover {{
    border-color: {ink};
}}
QCheckBox::indicator:checked {{
    background-color: {ink};
    border-color: {ink};
}}

/* ════════════════ Scroll Bars ════════════════ */
QScrollBar:vertical {{
    background: transparent;
    width: 8px;
    margin: 0;
    border: none;
}}
QScrollBar::handle:vertical {{
    background: {scrollbar};
    min-height: 28px;
    border-radius: 4px;
}}
QScrollBar::handle:vertical:hover {{
    background: {border_strong};
}}
QScrollBar::add-line:vertical, QScrollBar::sub-line:vertical,
QScrollBar::add-page:vertical, QScrollBar::sub-page:vertical {{
    background: none;
    height: 0px;
}}
QScrollBar:horizontal {{
    background: transparent;
    height: 8px;
    border: none;
}}
QScrollBar::handle:horizontal {{
    background: {scrollbar};
    min-width: 28px;
    border-radius: 4px;
}}
QScrollBar::handle:horizontal:hover {{
    background: {border_strong};
}}
QScrollBar::add-line:horizontal, QScrollBar::sub-line:horizontal,
QScrollBar::add-page:horizontal, QScrollBar::sub-page:horizontal {{
    background: none;
    width: 0px;
}}

/* ════════════════ Labels & Typography ════════════════ */
QLabel {{
    color: {text};
    background-color: transparent;
}}

/* Eyebrow label */
QLabel[class="g-eyebrow"] {{
    font-family: 'Geist', 'Segoe UI', sans-serif;
    font-size: 11px;
    font-weight: 700;
    color: {muted};
    letter-spacing: 0.8px;
    text-transform: uppercase;
    background-color: transparent;
}}

/* Form layout row labels */
QFormLayout > QLabel {{
    color: {text};
    font-weight: 500;
    font-size: 13px;
    background-color: transparent;
}}

/* ════════════════ Tooltip ════════════════ */
QToolTip {{
    background-color: {tooltip_bg};
    color: {tooltip_text};
    border: 1px solid {border_strong};
    border-radius: 6px;
    padding: 5px 10px;
    font-size: 12px;
}}

/* ════════════════ Status Bar ════════════════ */
QStatusBar {{
    background-color: {surface};
    color: {muted};
    border-top: 1px solid {border};
    font-size: 12px;
}}

/* ════════════════ Sidebar footer frame ════════════════ */
QFrame#sidebar_footer {{
    background-color: {hover};
    border: 1px solid {border};
    border-radius: 8px;
}}

/* ════════════════ Chat Message Cards ════════════════ */
QFrame[class="g-chat-user"] {{
    background-color: {hover};
    border: 1px solid {border};
    border-radius: 12px;
    padding: 12px 16px;
}}

QFrame[class="g-chat-assistant"] {{
    background-color: {card};
    border: 1px solid {border};
    border-radius: 12px;
    padding: 14px 18px;
}}

QFrame[class="g-evidence-card"] {{
    background-color: {surface};
    border: 1px solid {border};
    border-radius: 8px;
    padding: 10px 14px;
}}
"""

# ── Light Palette (Clean, Eco-Minimalist Brand Palette) ───────────────────────
_LIGHT = dict(
    bg="#faf9f5",
    surface="#ffffff",
    card="#ffffff",
    text="#141413",
    muted="#788c5d",
    nav_muted="#52524e",
    border="#e8e6dc",
    border_strong="#b0aea5",
    hover="#f4f3ed",
    pressed="#e8e6dc",
    chip_bg="#f4f3ed",
    chip_text="#141413",
    ink="#d97757",
    ink_text="#faf9f5",
    ink_hover="#c46344",
    ink_pressed="#b35336",
    ink_dim="#b0aea5",
    input_bg="#ffffff",
    scrollbar="#e8e6dc",
    sel_bg="#e8f0e6",
    sel_text="#788c5d",
    item_sel_bg="#d97757",
    item_sel_text="#ffffff",
    tooltip_bg="#141413",
    tooltip_text="#faf9f5",
)

# ── Dark Palette (Editorial Dark Tech Palette) ─────────────────────────────────
_DARK = dict(
    bg="#141413",
    surface="#1a1a19",
    card="#1f1f1d",
    text="#faf9f5",
    muted="#b0aea5",
    nav_muted="#e8e6dc",
    border="#2e2e2b",
    border_strong="#b0aea5",
    hover="#2b2b28",
    pressed="#383834",
    chip_bg="#2b2b28",
    chip_text="#faf9f5",
    ink="#d97757",
    ink_text="#faf9f5",
    ink_hover="#c46344",
    ink_pressed="#b35336",
    ink_dim="#b0aea5",
    input_bg="#1f1f1d",
    scrollbar="#2e2e2b",
    sel_bg="#2a3828",
    sel_text="#788c5d",
    item_sel_bg="#d97757",
    item_sel_text="#ffffff",
    tooltip_bg="#faf9f5",
    tooltip_text="#141413",
)

GEIST_LIGHT_QSS: str = _BASE.format(**_LIGHT)
GEIST_DARK_QSS: str = _BASE.format(**_DARK)
