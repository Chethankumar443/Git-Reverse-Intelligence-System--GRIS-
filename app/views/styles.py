# Vercel Geist & Enterprise Design System — PySide6 Qt6 QSS
# IMPORTANT: Qt QSS uses property selectors [class="x"], NOT CSS dot-notation ".x"

_BASE = """
/* ════════════════ Global Reset ════════════════ */
QWidget {{
    color: {text};
    background-color: {bg};
    font-family: 'Segoe UI', -apple-system, BlinkMacSystemFont, 'Inter', sans-serif;
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

/* ════════════════ Title Header ════════════════ */
QFrame#titlebar {{
    background-color: {surface};
    border-bottom: 1px solid {border};
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
    border-radius: 6px;
    border: 1px solid transparent;
    background-color: transparent;
    color: {nav_muted};
    font-size: 13px;
    font-weight: 500;
}}
QFrame#sidebar > QPushButton:hover {{
    background-color: {hover};
    color: {text};
    border-color: transparent;
}}
QFrame#sidebar > QPushButton:checked {{
    background-color: {card};
    border: 1px solid {border};
    color: {text};
    font-weight: 600;
}}

/* ════════════════ Pane Cards (g-pane) ════════════════ */
QFrame[class="g-pane"] {{
    background-color: {card};
    border: 1px solid {border};
    border-radius: 8px;
}}

/* ════════════════ Group Boxes ════════════════ */
QGroupBox {{
    background-color: {card};
    border: 1px solid {border};
    border-radius: 8px;
    margin-top: 16px;
    padding-top: 20px;
    font-weight: 600;
    color: {text};
}}
QGroupBox::title {{
    subcontrol-origin: margin;
    subcontrol-position: top left;
    left: 12px;
    top: -1px;
    padding: 2px 10px;
    background-color: {card};
    color: {text};
    border: 1px solid {border};
    border-radius: 4px;
    font-size: 12px;
    font-weight: 700;
}}

/* ════════════════ Base Buttons ════════════════ */
QPushButton {{
    color: {text};
    background-color: {card};
    border: 1px solid {border};
    border-radius: 6px;
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
    border-radius: 6px;
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
    border-radius: 6px;
    padding: 8px 16px;
}}
QPushButton[class="g-btn-ghost"]:hover {{
    background-color: {hover};
    border-color: {border_strong};
}}

/* Chip button */
QPushButton[class="g-btn-chip"] {{
    background-color: {chip_bg};
    color: {chip_text};
    font-size: 11px;
    font-weight: 500;
    border-radius: 12px;
    padding: 4px 12px;
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
    border-radius: 6px;
    padding: 8px 12px;
    font-size: 13px;
    selection-background-color: {sel_bg};
    selection-color: {sel_text};
}}
QLineEdit:focus {{
    border-color: {ink_dim};
}}
QLineEdit:read-only {{
    color: {muted};
    background-color: {surface};
}}

QPlainTextEdit, QTextEdit {{
    background-color: {input_bg};
    color: {text};
    border: 1px solid {border};
    border-radius: 6px;
    padding: 8px 12px;
    font-size: 13px;
    selection-background-color: {sel_bg};
    selection-color: {sel_text};
}}
QPlainTextEdit:focus, QTextEdit:focus {{
    border-color: {ink_dim};
}}

/* ════════════════ ComboBox ════════════════ */
QComboBox {{
    background-color: {input_bg};
    color: {text};
    border: 1px solid {border};
    border-radius: 6px;
    padding: 6px 12px;
    font-size: 13px;
    min-height: 28px;
}}
QComboBox:hover {{
    border-color: {border_strong};
}}
QComboBox:focus {{
    border-color: {ink_dim};
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
    border-radius: 6px;
    padding: 4px;
    selection-background-color: {ink};
    selection-color: {ink_text};
    outline: none;
}}
QComboBox QAbstractItemView::item {{
    min-height: 30px;
    padding: 4px 10px;
    border-radius: 4px;
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
    border-radius: 8px;
    background-color: {card};
    top: -1px;
}}
QTabBar::tab {{
    background-color: {surface};
    color: {muted};
    border: 1px solid {border};
    border-bottom: none;
    border-top-left-radius: 6px;
    border-top-right-radius: 6px;
    padding: 8px 16px;
    font-size: 12px;
    font-weight: 500;
    margin-right: 3px;
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

/* ════════════════ List Widget ════════════════ */
QListWidget {{
    background-color: {card};
    color: {text};
    border: 1px solid {border};
    border-radius: 6px;
    padding: 4px;
    outline: none;
}}
QListWidget::item {{
    padding: 8px 10px;
    border-radius: 4px;
    color: {text};
    background-color: transparent;
    font-size: 12px;
}}
QListWidget::item:alternate {{
    background-color: {surface};
}}
QListWidget::item:hover {{
    background-color: {hover};
    color: {text};
}}
QListWidget::item:selected {{
    background-color: {item_sel_bg};
    color: {item_sel_text};
    font-weight: 600;
}}

/* ════════════════ Progress Bar ════════════════ */
QProgressBar {{
    background-color: {border};
    border: none;
    border-radius: 2px;
    height: 4px;
    max-height: 4px;
    text-align: center;
    color: transparent;
}}
QProgressBar::chunk {{
    background-color: {ink};
    border-radius: 2px;
}}

/* ════════════════ Splitter ════════════════ */
QSplitter::handle {{
    background-color: {border};
}}
QSplitter::handle:horizontal {{
    width: 1px;
}}
QSplitter::handle:vertical {{
    height: 1px;
}}
QSplitter::handle:hover {{
    background-color: {border_strong};
}}

/* ════════════════ Check Box ════════════════ */
QCheckBox {{
    color: {text};
    spacing: 8px;
    font-size: 12px;
    background-color: transparent;
}}
QCheckBox::indicator {{
    width: 16px;
    height: 16px;
    border-radius: 4px;
    border: 1.5px solid {border_strong};
    background-color: {input_bg};
}}
QCheckBox::indicator:hover {{
    border-color: {ink_dim};
}}
QCheckBox::indicator:checked {{
    background-color: {ink};
    border-color: {ink};
}}

/* ════════════════ Scroll Bars ════════════════ */
QScrollBar:vertical {{
    background: transparent;
    width: 6px;
    margin: 0;
    border: none;
}}
QScrollBar::handle:vertical {{
    background: {scrollbar};
    min-height: 24px;
    border-radius: 3px;
}}
QScrollBar::handle:vertical:hover {{
    background: {border_strong};
}}
QScrollBar::add-line:vertical,
QScrollBar::sub-line:vertical,
QScrollBar::add-page:vertical,
QScrollBar::sub-page:vertical {{
    background: none;
    height: 0px;
}}
QScrollBar:horizontal {{
    background: transparent;
    height: 6px;
    border: none;
}}
QScrollBar::handle:horizontal {{
    background: {scrollbar};
    min-width: 24px;
    border-radius: 3px;
}}
QScrollBar::handle:horizontal:hover {{
    background: {border_strong};
}}
QScrollBar::add-line:horizontal,
QScrollBar::sub-line:horizontal,
QScrollBar::add-page:horizontal,
QScrollBar::sub-page:horizontal {{
    background: none;
    width: 0px;
}}

/* ════════════════ Labels ════════════════ */
QLabel {{
    color: {text};
    background-color: transparent;
}}

/* Eyebrow label */
QLabel[class="g-eyebrow"] {{
    font-family: 'Segoe UI', sans-serif;
    font-size: 10px;
    font-weight: 700;
    color: {muted};
    letter-spacing: 1px;
    background-color: transparent;
}}

/* Form layout row labels */
QFormLayout > QLabel {{
    color: {text};
    font-weight: 500;
    font-size: 12px;
    background-color: transparent;
}}

/* ════════════════ Tooltip ════════════════ */
QToolTip {{
    background-color: {tooltip_bg};
    color: {tooltip_text};
    border: 1px solid {border_strong};
    border-radius: 4px;
    padding: 4px 8px;
    font-size: 11px;
}}

/* ════════════════ Status Bar ════════════════ */
QStatusBar {{
    background-color: {surface};
    color: {muted};
    border-top: 1px solid {border};
    font-size: 11px;
}}

/* ════════════════ Sidebar footer frame ════════════════ */
QFrame#sidebar_footer {{
    background-color: {hover};
    border: 1px solid {border};
    border-radius: 6px;
}}
"""

# ── Light Palette ──────────────────────────────────────────────────────────────
_LIGHT = dict(
    bg="#f4f4f5",
    surface="#ffffff",
    card="#ffffff",
    text="#09090b",
    muted="#71717a",
    nav_muted="#52525b",
    border="#e4e4e7",
    border_strong="#a1a1aa",
    hover="#f4f4f5",
    pressed="#e4e4e7",
    chip_bg="#f4f4f5",
    chip_text="#3f3f46",
    ink="#09090b",
    ink_text="#ffffff",
    ink_hover="#27272a",
    ink_pressed="#3f3f46",
    ink_dim="#71717a",
    input_bg="#ffffff",
    scrollbar="#d4d4d8",
    sel_bg="#dbeafe",
    sel_text="#1d4ed8",
    item_sel_bg="#2563eb",
    item_sel_text="#ffffff",
    tooltip_bg="#09090b",
    tooltip_text="#ffffff",
)

# ── Dark Palette ───────────────────────────────────────────────────────────────
_DARK = dict(
    bg="#09090b",
    surface="#141417",
    card="#18181b",
    text="#f4f4f5",
    muted="#a1a1aa",
    nav_muted="#d4d4d8",
    border="#27272a",
    border_strong="#52525b",
    hover="#27272a",
    pressed="#3f3f46",
    chip_bg="#27272a",
    chip_text="#d4d4d8",
    ink="#f4f4f5",
    ink_text="#09090b",
    ink_hover="#e4e4e7",
    ink_pressed="#d4d4d8",
    ink_dim="#a1a1aa",
    input_bg="#18181b",
    scrollbar="#3f3f46",
    sel_bg="#1e3a5f",
    sel_text="#93c5fd",
    item_sel_bg="#2563eb",
    item_sel_text="#ffffff",
    tooltip_bg="#f4f4f5",
    tooltip_text="#09090b",
)

GEIST_LIGHT_QSS: str = _BASE.format(**_LIGHT)
GEIST_DARK_QSS: str = _BASE.format(**_DARK)
