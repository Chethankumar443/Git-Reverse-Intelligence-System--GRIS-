# Vercel Geist & Enterprise Design System — PySide6 Qt6 QSS
# IMPORTANT: Qt QSS uses property selectors [class="x"], NOT CSS dot-notation ".x"

_BASE = """
/* ════════════════ Global Reset & Typography ════════════════ */
QWidget {{
    color: {text};
    background-color: {bg};
    font-family: 'Grcafon', 'Orbitron', 'Space Grotesk', 'Cabinet Grotesk', -apple-system, BlinkMacSystemFont, "Segoe UI", "Inter", sans-serif;
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

/* ════════════════ Info Callout Cards ════════════════ */
QFrame[class="g-info-card"] {{
    background-color: {card};
    border: 1px solid {border};
    border-radius: 10px;
    padding: 16px;
}}
QFrame[class="g-info-card"]:hover {{
    border-color: {border_strong};
}}

/* ════════════════ Title Header Bar ════════════════ */
QFrame#titlebar {{
    background-color: {surface};
    border-bottom: 1px solid {border};
}}

QLabel#title_heading {{
    font-family: 'Grcafon', 'Orbitron', 'Space Grotesk', 'Cabinet Grotesk', sans-serif;
    font-size: 15px;
    font-weight: 700;
    color: {text};
    letter-spacing: 0.5px;
}}

QLabel#ver_badge {{
    font-family: 'Geist Mono', 'Consolas', monospace;
    font-size: 11px;
    font-weight: 600;
    color: {badge_text};
    background-color: {badge_bg};
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
    padding: 16px;
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
    font-family: 'Grcafon', 'Orbitron', 'Space Grotesk', sans-serif;
    font-size: 11px;
    font-weight: 700;
    letter-spacing: 0.8px;
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
    color: {disabled_text};
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
    background-color: {border};
    border-color: {border};
    color: {disabled_text};
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
    background-color: {hover};
    color: {text};
    border-color: {border_strong};
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
    border-color: {border_strong};
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
    border-color: {border_strong};
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
    border-color: {border_strong};
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
    selection-background-color: {item_sel_bg};
    selection-color: {item_sel_text};
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
    background-color: {item_sel_bg};
    color: {item_sel_text};
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
    font-family: 'Grcafon', 'Orbitron', 'Space Grotesk', 'Cabinet Grotesk', sans-serif;
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

# ── Light Palette (Clean, High-Contrast Modern Enterprise Palette) ─────────────
_LIGHT = dict(
    bg="#fcfcfc",
    surface="#ffffff",
    card="#ffffff",
    text="#18181b",
    muted="#64748b",
    nav_muted="#475569",
    border="#e4e4e7",
    border_strong="#a1a1aa",
    hover="#f4f4f5",
    pressed="#e4e4e7",
    chip_bg="#f4f4f5",
    chip_text="#18181b",
    badge_bg="#f4f4f5",
    badge_text="#475569",
    disabled_text="#a1a1aa",
    ink="#18181b",
    ink_text="#ffffff",
    ink_hover="#27272a",
    ink_pressed="#09090b",
    ink_dim="#a1a1aa",
    input_bg="#ffffff",
    scrollbar="#d4d4d8",
    sel_bg="#e4e4e7",
    sel_text="#18181b",
    item_sel_bg="#18181b",
    item_sel_text="#ffffff",
    tooltip_bg="#18181b",
    tooltip_text="#ffffff",
)

# ── Dark Palette (Editorial Dark Tech Palette) ─────────────────────────────────
_DARK = dict(
    bg="#09090b",
    surface="#121215",
    card="#18181b",
    text="#f4f4f5",
    muted="#a1a1aa",
    nav_muted="#d4d4d8",
    border="#27272a",
    border_strong="#52525b",
    hover="#27272a",
    pressed="#3f3f46",
    chip_bg="#27272a",
    chip_text="#f4f4f5",
    badge_bg="#27272a",
    badge_text="#a1a1aa",
    disabled_text="#52525b",
    ink="#f4f4f5",
    ink_text="#09090b",
    ink_hover="#e4e4e7",
    ink_pressed="#d4d4d8",
    ink_dim="#52525b",
    input_bg="#18181b",
    scrollbar="#3f3f46",
    sel_bg="#27272a",
    sel_text="#f4f4f5",
    item_sel_bg="#3f3f46",
    item_sel_text="#ffffff",
    tooltip_bg="#f4f4f5",
    tooltip_text="#09090b",
)

GEIST_LIGHT_QSS: str = _BASE.format(**_LIGHT)
GEIST_DARK_QSS: str = _BASE.format(**_DARK)
