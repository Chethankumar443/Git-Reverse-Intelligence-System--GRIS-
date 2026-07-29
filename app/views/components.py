"""
Shared UI Components & State Management for Git Reverse.

Provides:
- classify_error: Error taxonomy classifier mapping exceptions to standardized categories.
- AsyncStateWidget: Visual state indicator widget for async operations (Idle, Loading, Success, Error).
- EmptyStateWidget: Reusable placeholder widget for empty lists/panels with call-to-action.
"""
import re
from typing import Optional, Callable
from PySide6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QLabel, QPushButton, QProgressBar, QFrame
)
from PySide6.QtCore import Qt, Signal


def classify_error(error: Exception | str) -> dict:
    """Classifies raw errors/exceptions into the standard Git Reverse Error Taxonomy.

    Taxonomy Categories:
    1. Network unreachable
    2. Resource not found
    3. Authentication failed
    4. Rate limited
    5. Invalid input
    6. Internal error

    Returns dict with:
      - category: str
      - message: str
      - can_retry: bool
    """
    err_str = str(error) if error else "Unknown error"
    err_lower = err_str.lower()

    # 1. Invalid input
    if "invalid github url" in err_lower or "invalid url" in err_lower or "is invalid" in err_lower or "malformed" in err_lower:
        return {
            "category": "Invalid input",
            "message": f"Input validation failed: {err_str}",
            "can_retry": False,
        }

    # 2. Authentication failed
    if "401" in err_str or "unauthorized" in err_lower or "api key" in err_lower or "token" in err_lower and "rejected" in err_lower:
        return {
            "category": "Authentication failed",
            "message": "Authentication failed — check your API key or token in Settings.",
            "can_retry": True,
        }

    # 3. Rate limited
    if "429" in err_str or "403" in err_str and "rate limit" in err_lower or "rate limit" in err_lower or "too many requests" in err_lower:
        return {
            "category": "Rate limited",
            "message": "Rate limit reached — wait before retrying or add an API key/token in Settings to raise your limit.",
            "can_retry": True,
        }

    # 4. Resource not found
    if "404" in err_str or "not found" in err_lower:
        return {
            "category": "Resource not found",
            "message": "Repository or resource not found — check the URL or confirm access permissions.",
            "can_retry": True,
        }

    # 5. Network unreachable
    if "connection" in err_lower or "network" in err_lower or "timeout" in err_lower or "unreachable" in err_lower or "dns" in err_lower or "socket" in err_lower:
        return {
            "category": "Network unreachable",
            "message": "Can't reach the target service — check your internet connection and Base URL settings.",
            "can_retry": True,
        }

    # 6. Internal error
    return {
        "category": "Internal error",
        "message": f"An internal operation error occurred: {err_str}",
        "can_retry": True,
    }


class AsyncStateWidget(QFrame):
    """Reusable state-indicator widget implementing the UI State Contract.

    Supports: Idle, Loading, Success, Error (with retry action).
    """

    retry_requested = Signal()

    def __init__(self, parent=None):
        super().__init__(parent)
        self.setObjectName("AsyncStateWidget")
        self.setStyleSheet("""
            #AsyncStateWidget {
                border-radius: 6px;
                padding: 6px 12px;
            }
        """)
        self._init_ui()
        self.set_idle("Ready")

    def _init_ui(self):
        layout = QHBoxLayout(self)
        layout.setContentsMargins(8, 6, 8, 6)
        layout.setSpacing(10)

        self.lbl_status = QLabel("Ready")
        self.lbl_status.setStyleSheet("font-size: 11px; font-weight: 500;")

        self.progress_bar = QProgressBar()
        self.progress_bar.setFixedHeight(4)
        self.progress_bar.setTextVisible(False)
        self.progress_bar.setRange(0, 0)
        self.progress_bar.hide()

        self.btn_retry = QPushButton("Retry")
        self.btn_retry.setProperty("class", "g-btn-ghost")
        self.btn_retry.setFixedHeight(26)
        self.btn_retry.setStyleSheet("font-size: 10px; padding: 2px 10px;")
        self.btn_retry.clicked.connect(self.retry_requested.emit)
        self.btn_retry.hide()

        layout.addWidget(self.lbl_status)
        layout.addWidget(self.progress_bar, 1)
        layout.addWidget(self.btn_retry)

    def set_idle(self, text: str = "Ready"):
        self.lbl_status.setText(text)
        self.lbl_status.setStyleSheet("font-size: 11px; font-weight: 500; color: #71717a;")
        self.setStyleSheet("#AsyncStateWidget { background: transparent; border: none; }")
        self.progress_bar.hide()
        self.btn_retry.hide()

    def set_loading(self, text: str = "Processing...", progress: Optional[int] = None, total: Optional[int] = None):
        if progress is not None and total is not None and total > 0:
            self.progress_bar.setRange(0, total)
            self.progress_bar.setValue(progress)
            pct = int((progress / total) * 100)
            self.lbl_status.setText(f"⏳ {text} ({pct}%)")
        else:
            self.progress_bar.setRange(0, 0)
            self.lbl_status.setText(f"⏳ {text}")

        self.lbl_status.setStyleSheet("font-size: 11px; font-weight: 600; color: #2563eb;")
        self.setStyleSheet("""
            #AsyncStateWidget {
                background: rgba(37, 99, 235, 0.08);
                border: 1px solid rgba(37, 99, 235, 0.25);
            }
        """)
        self.progress_bar.show()
        self.btn_retry.hide()

    def set_success(self, text: str = "Operation complete"):
        self.lbl_status.setText(f"✓ {text}")
        self.lbl_status.setStyleSheet("font-size: 11px; font-weight: 600; color: #166534;")
        self.setStyleSheet("""
            #AsyncStateWidget {
                background: #dcfce7;
                border: 1px solid #86efac;
            }
        """)
        self.progress_bar.hide()
        self.btn_retry.hide()

    def set_error(self, error: Exception | str, override_msg: Optional[str] = None):
        info = classify_error(error)
        msg = override_msg or info["message"]
        cat = info["category"]

        self.lbl_status.setText(f"✗ [{cat}] {msg}")
        self.lbl_status.setStyleSheet("font-size: 11px; font-weight: 600; color: #991b1b;")
        self.setStyleSheet("""
            #AsyncStateWidget {
                background: #fee2e2;
                border: 1px solid #fca5a5;
            }
        """)
        self.progress_bar.hide()

        if info["can_retry"]:
            self.btn_retry.show()
        else:
            self.btn_retry.hide()


class EmptyStateWidget(QFrame):
    """Reusable empty state panel with title, message, and optional call-to-action button."""

    action_clicked = Signal()

    def __init__(self, title: str, description: str, action_text: Optional[str] = None, parent=None):
        super().__init__(parent)
        self.setObjectName("EmptyStateWidget")
        self.setStyleSheet("""
            #EmptyStateWidget {
                background: palette(alternate-base);
                border: 1px dashed palette(mid);
                border-radius: 8px;
                padding: 24px;
            }
        """)
        layout = QVBoxLayout(self)
        layout.setAlignment(Qt.AlignCenter)
        layout.setSpacing(10)

        title_lbl = QLabel(title)
        title_lbl.setStyleSheet("font-size: 14px; font-weight: 700; color: #3f3f46;")
        title_lbl.setAlignment(Qt.AlignCenter)

        desc_lbl = QLabel(description)
        desc_lbl.setStyleSheet("font-size: 12px; color: #71717a;")
        desc_lbl.setWordWrap(True)
        desc_lbl.setAlignment(Qt.AlignCenter)

        layout.addWidget(title_lbl)
        layout.addWidget(desc_lbl)

        if action_text:
            btn = QPushButton(action_text)
            btn.setProperty("class", "g-btn-solid")
            btn.setFixedWidth(160)
            btn.clicked.connect(self.action_clicked.emit)
            layout.addWidget(btn, 0, Qt.AlignCenter)
