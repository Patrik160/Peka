# ============================================================
#  P.E.K.A UI – v2.0 · Polished, Seamless, Error-Free
#  + Automatic new session on startup
#  + Thread‑safe mute integration with PekaLive
# ============================================================

import sys
import threading
import re
import json
import time
import platform
import math
from pathlib import Path
from datetime import datetime
from typing import Optional, List, Dict

from PyQt6.QtWidgets import (
    QApplication, QMainWindow, QWidget, QVBoxLayout, QHBoxLayout,
    QLabel, QPushButton, QTextEdit, QScrollArea, QFrame,
    QSizePolicy, QStackedWidget, QGraphicsOpacityEffect,
    QMenu, QFileDialog, QInputDialog,
    QMessageBox, QLineEdit, QSplitter
)
from PyQt6.QtCore import (
    Qt, QSize, QTimer, pyqtSignal, QPoint, QPropertyAnimation,
    QEasingCurve, QRect, pyqtSlot, QEvent, QSequentialAnimationGroup,
    QParallelAnimationGroup, QAbstractAnimation
)
from PyQt6.QtGui import (
    QColor, QPainter, QPainterPath,
    QFont, QBrush, QKeyEvent, QCursor,
    QLinearGradient, QKeySequence, QAction, QShortcut, QPen,
    QPalette, QDragEnterEvent, QDropEvent, QRadialGradient
)

# ── Constants & paths ────────────────────────────────────────────────────────
BASE_DIR     = Path(__file__).resolve().parent
CONFIG_DIR   = BASE_DIR / "config"
API_FILE     = CONFIG_DIR / "api_keys.json"
HISTORY_FILE = BASE_DIR / "chat_history.json"
THEME_FILE   = BASE_DIR / "config" / "theme.json"

# ── Design tokens ─────────────────────────────────────────────────────────────
THEMES: Dict[str, Dict[str, str]] = {
    "dark": {
        "BG_PRIMARY":    "#17161a",
        "BG_SIDEBAR":    "#111014",
        "BG_SURFACE":    "#212025",
        "BG_INPUT":      "#2a2930",
        "BG_MSG_USER":   "#2d2c34",
        "BG_MSG_AI":     "transparent",
        "TXT_PRIMARY":   "#ede9f0",
        "TXT_SECONDARY": "#948fa0",
        "TXT_MUTED":     "#514d5c",
        "ACCENT":        "#b87bff",
        "ACCENT_ALT":    "#7b8fff",
        "ACCENT_SOFT":   "#9b62e8",
        "ACCENT_GLOW":   "#b87bff28",
        "BORDER":        "#2e2c38",
        "BORDER_SOFT":   "#232230",
        "BORDER_FOCUS":  "#b87bff60",
        "SIDEBAR_ACTIVE":"#2a2834",
        "SUCCESS":       "#6fbe8a",
        "ERROR":         "#ff6b7a",
        "CODE_BG":       "#1a1920",
        "SHADOW":        "rgba(0,0,0,0.5)",
        "GRADIENT_A":    "#b87bff15",
        "GRADIENT_B":    "#7b8fff10",
        "TYPING_DOT":    "#b87bff",
    },
    "light": {
        "BG_PRIMARY":    "#f8f7fc",
        "BG_SIDEBAR":    "#eeedf5",
        "BG_SURFACE":    "#ffffff",
        "BG_INPUT":      "#f0eef8",
        "BG_MSG_USER":   "#e8e5f5",
        "BG_MSG_AI":     "transparent",
        "TXT_PRIMARY":   "#1a1825",
        "TXT_SECONDARY": "#6b647a",
        "TXT_MUTED":     "#a49db5",
        "ACCENT":        "#7c4dff",
        "ACCENT_ALT":    "#4d6bff",
        "ACCENT_SOFT":   "#6b3de0",
        "ACCENT_GLOW":   "#7c4dff20",
        "BORDER":        "#e0dcea",
        "BORDER_SOFT":   "#ece9f5",
        "BORDER_FOCUS":  "#7c4dff50",
        "SIDEBAR_ACTIVE":"#e4e0f2",
        "SUCCESS":       "#3d9e5f",
        "ERROR":         "#e0404f",
        "CODE_BG":       "#f0eef8",
        "SHADOW":        "rgba(100,80,140,0.10)",
        "GRADIENT_A":    "#7c4dff0a",
        "GRADIENT_B":    "#4d6bff08",
        "TYPING_DOT":    "#7c4dff",
    },
}

_current_theme = "dark"


def T(key: str) -> str:
    return THEMES[_current_theme].get(key, "#ff00ff")  # magenta = missing token bug


def apply_theme(name: str):
    global _current_theme
    if name in THEMES:
        _current_theme = name
        try:
            THEME_FILE.parent.mkdir(exist_ok=True)
            THEME_FILE.write_text(json.dumps({"theme": name}))
        except Exception:
            pass


def load_theme():
    try:
        if THEME_FILE.exists():
            d = json.loads(THEME_FILE.read_text())
            if d.get("theme") in THEMES:
                apply_theme(d["theme"])
    except Exception:
        pass


MODELS = [
    ("gemini-2.5-flash",     "Gemini 2.5 Flash"),
    ("gemini-2.0-flash-exp", "Gemini 2.0 Flash"),
    ("gemini-1.5-pro",       "Gemini 1.5 Pro"),
]

SIDEBAR_W     = 252
CONTENT_MAX_W = 760


# ── Easing helpers ────────────────────────────────────────────────────────────
def make_fade_in(widget: QWidget, duration: int = 220) -> QPropertyAnimation:
    """Return a ready-to-start opacity fade-in animation."""
    eff = QGraphicsOpacityEffect(widget)
    eff.setOpacity(0.0)
    widget.setGraphicsEffect(eff)
    anim = QPropertyAnimation(eff, b"opacity", widget)
    anim.setDuration(duration)
    anim.setStartValue(0.0)
    anim.setEndValue(1.0)
    anim.setEasingCurve(QEasingCurve.Type.OutCubic)
    return anim


# ── Chat History Manager ──────────────────────────────────────────────────────
class ChatHistoryManager:
    def __init__(self):
        self.sessions: Dict[str, List[Dict]] = {}
        self.current_session_id: Optional[str] = None
        self._max_messages = 1000
        # Timer created once; safe from race condition
        self._save_timer = QTimer()
        self._save_timer.setSingleShot(True)
        self._save_timer.timeout.connect(self._do_save)
        self._pending_save = False
        self.load()

    def load(self):
        if HISTORY_FILE.exists():
            try:
                data = json.loads(HISTORY_FILE.read_text(encoding="utf-8"))
                self.sessions = data.get("sessions", {})
                # Always start a fresh session, but keep history for sidebar
            except Exception:
                self.sessions = {}
        self.new_session()   # <-- always create new session on startup

    def _schedule_save(self):
        self._pending_save = True
        if not self._save_timer.isActive():
            self._save_timer.start(600)

    def _do_save(self):
        if not self._pending_save:
            return
        try:
            HISTORY_FILE.write_text(
                json.dumps(
                    {"sessions": self.sessions, "current": self.current_session_id},
                    indent=2, ensure_ascii=False,
                ),
                encoding="utf-8",
            )
            self._pending_save = False
        except IOError:
            pass

    def save(self):
        self._do_save()

    def new_session(self) -> str:
        sid = datetime.now().strftime("%Y%m%d_%H%M%S_%f")
        self.sessions[sid] = []
        self.current_session_id = sid
        self.save()
        return sid

    def add_message(self, role: str, content: str):
        if not self.current_session_id:
            self.new_session()
        msgs = self.sessions[self.current_session_id]
        if len(msgs) >= self._max_messages:
            msgs.pop(0)
        msgs.append({"role": role, "content": content, "timestamp": time.time()})
        self._schedule_save()

    def get_session_titles(self) -> Dict[str, str]:
        out = {}
        for sid, msgs in self.sessions.items():
            raw = msgs[0]["content"] if msgs else "New conversation"
            out[sid] = (raw[:40] + "…") if len(raw) > 40 else raw
        return out

    def load_session(self, sid: str) -> List[Dict]:
        self.current_session_id = sid
        self.save()
        return self.sessions.get(sid, [])

    def delete_session(self, sid: str):
        if sid not in self.sessions:
            return
        del self.sessions[sid]
        if self.current_session_id == sid:
            self.current_session_id = (
                next(iter(self.sessions)) if self.sessions else None
            )
            if not self.current_session_id:
                self.new_session()
        self.save()


# ── Logo Mark (animated asterisk) ─────────────────────────────────────────────
class PekaLogoMark(QWidget):
    def __init__(self, size: int = 32, animated: bool = True, parent=None):
        super().__init__(parent)
        self.setFixedSize(size, size)
        self._sz          = size
        self._animated    = animated
        self._angle       = 0.0
        self._pulse       = 0.0
        self._pulse_dir   = 1
        self._glow        = 0.0
        self._glow_dir    = 1
        self._is_thinking = False
        self._cleaned     = False
        self._timer: Optional[QTimer] = None
        if animated:
            self._start_timer()

    def _start_timer(self):
        if self._timer is None:
            self._timer = QTimer(self)
            self._timer.timeout.connect(self._tick)
        if not self._timer.isActive():
            self._timer.start(33)  # ~30fps

    def start_animation(self):
        if not self._animated or self._cleaned:
            return
        self._start_timer()

    def stop_animation(self):
        if self._timer and self._timer.isActive():
            self._timer.stop()

    def set_thinking(self, v: bool):
        self._is_thinking = v
        if v:
            self._start_timer()

    def _tick(self):
        if self._cleaned:
            return
        if self._is_thinking:
            self._angle = (self._angle + 3.5) % 360
        self._pulse += 0.04 * self._pulse_dir
        if self._pulse >= 1.0 or self._pulse <= 0.0:
            self._pulse_dir *= -1
        self._glow += 0.03 * self._glow_dir
        if self._glow >= 1.0 or self._glow <= 0.0:
            self._glow_dir *= -1
        self.update()

    def cleanup(self):
        if self._cleaned:
            return
        self._cleaned = True
        if self._timer:
            self._timer.stop()
            self._timer.deleteLater()
            self._timer = None

    def paintEvent(self, _):
        p = QPainter(self)
        p.setRenderHint(QPainter.RenderHint.Antialiasing)
        s  = self._sz
        cx = cy = s / 2
        accent = QColor(T("ACCENT"))
        alt    = QColor(T("ACCENT_ALT"))

        n_arms  = 8
        arm_len = s * 0.43
        arm_w   = s * 0.10
        inner_r = s * 0.07

        for i in range(n_arms):
            base_angle = (360 / n_arms) * i + (self._angle if self._is_thinking else 0)
            rad = math.radians(base_angle)

            # Blend accent colors around the wheel
            t = (math.sin(rad + self._pulse * math.pi) + 1) / 2
            c = QColor(
                int(accent.red()   * t + alt.red()   * (1 - t)),
                int(accent.green() * t + alt.green() * (1 - t)),
                int(accent.blue()  * t + alt.blue()  * (1 - t)),
            )
            # Alpha wave
            alpha = int(180 + 75 * math.sin(rad * 2 + self._pulse * math.pi * 2))
            if self._is_thinking:
                alpha = int(alpha * (0.7 + 0.3 * self._glow))
            c.setAlpha(min(255, alpha))

            p.save()
            p.translate(cx, cy)
            p.rotate(base_angle)

            path = QPainterPath()
            path.moveTo(-arm_w * 0.4, inner_r)
            path.lineTo(-arm_w * 0.5, arm_len * 0.45)
            path.quadTo(-arm_w * 0.3, arm_len * 0.95, 0, arm_len)
            path.quadTo(arm_w * 0.3, arm_len * 0.95, arm_w * 0.5, arm_len * 0.45)
            path.lineTo(arm_w * 0.4, inner_r)
            path.closeSubpath()

            p.setBrush(QBrush(c))
            p.setPen(Qt.PenStyle.NoPen)
            p.drawPath(path)
            p.restore()

        # Center dot glow when thinking
        if self._is_thinking:
            glow_c = QColor(T("ACCENT"))
            glow_c.setAlpha(int(60 * self._glow))
            r = s * 0.14
            p.setBrush(glow_c)
            p.setPen(Qt.PenStyle.NoPen)
            p.drawEllipse(int(cx - r), int(cy - r), int(r * 2), int(r * 2))


# ── Sidebar ───────────────────────────────────────────────────────────────────
class SidebarHeader(QWidget):
    new_chat_clicked = pyqtSignal()

    def __init__(self, parent=None):
        super().__init__(parent)
        self.setFixedHeight(60)
        lay = QHBoxLayout(self)
        lay.setContentsMargins(16, 0, 12, 0)
        lay.setSpacing(9)

        self._logo = PekaLogoMark(size=20, animated=False)
        lay.addWidget(self._logo)

        name = QLabel("Peka")
        name.setStyleSheet(
            f"color:{T('TXT_PRIMARY')};font-size:15px;font-weight:700;"
            "letter-spacing:-0.4px;background:transparent;"
            "font-family:'Segoe UI Variable','Segoe UI',sans-serif;"
        )
        lay.addWidget(name)
        lay.addStretch()

        self._new_btn = QPushButton()
        self._new_btn.setFixedSize(32, 32)
        self._new_btn.setCursor(QCursor(Qt.CursorShape.PointingHandCursor))
        self._new_btn.setToolTip("New conversation  (Ctrl+N)")
        self._new_btn.clicked.connect(self.new_chat_clicked)
        self._new_btn.setText("✦")
        self._style_new_btn()
        lay.addWidget(self._new_btn)

    def _style_new_btn(self):
        self._new_btn.setStyleSheet(f"""
            QPushButton {{
                background:transparent;color:{T('TXT_MUTED')};
                border:none;border-radius:8px;font-size:13px;
            }}
            QPushButton:hover {{
                background:{T('BG_SURFACE')};color:{T('ACCENT')};
            }}
            QPushButton:pressed {{
                background:{T('BORDER')};
            }}
        """)

    def refresh_styles(self):
        self._style_new_btn()

    def paintEvent(self, _):
        QPainter(self).fillRect(self.rect(), QColor(T("BG_SIDEBAR")))


class HistoryItem(QWidget):
    clicked        = pyqtSignal(str)
    delete_clicked = pyqtSignal(str)

    def __init__(self, sid: str, title: str, active: bool = False, parent=None):
        super().__init__(parent)
        self.sid      = sid
        self._active  = active
        self._hovered = False
        self.setFixedHeight(42)
        self.setCursor(QCursor(Qt.CursorShape.PointingHandCursor))
        self.setToolTip(title)

        lay = QHBoxLayout(self)
        lay.setContentsMargins(10, 0, 8, 0)
        lay.setSpacing(6)

        self._lbl = QLabel(title)
        self._lbl.setStyleSheet(self._lbl_style())
        lay.addWidget(self._lbl, 1)

        self._del = QPushButton("✕")
        self._del.setFixedSize(22, 22)
        self._del.setCursor(QCursor(Qt.CursorShape.PointingHandCursor))
        self._del.setVisible(False)
        self._del.setToolTip("Delete conversation")
        self._del.clicked.connect(lambda: self.delete_clicked.emit(self.sid))
        self._del.setStyleSheet(f"""
            QPushButton {{
                background:transparent;color:{T('TXT_MUTED')};
                border:none;border-radius:5px;font-size:10px;
            }}
            QPushButton:hover {{
                background:{T('BG_INPUT')};color:{T('ERROR')};
            }}
        """)
        lay.addWidget(self._del)

    def _lbl_style(self) -> str:
        col    = T("TXT_PRIMARY") if self._active else T("TXT_SECONDARY")
        weight = "600" if self._active else "400"
        return (
            f"color:{col};font-size:13px;font-weight:{weight};"
            "background:transparent;"
            "font-family:'Segoe UI Variable','Segoe UI',sans-serif;"
        )

    def set_active(self, v: bool):
        self._active = v
        self._lbl.setStyleSheet(self._lbl_style())
        self.update()

    def enterEvent(self, _):
        self._hovered = True
        self._del.setVisible(True)
        self.update()

    def leaveEvent(self, _):
        self._hovered = False
        self._del.setVisible(False)
        self.update()

    def mousePressEvent(self, e):
        if e.button() == Qt.MouseButton.LeftButton:
            self.clicked.emit(self.sid)

    def paintEvent(self, _):
        p = QPainter(self)
        p.setRenderHint(QPainter.RenderHint.Antialiasing)
        r = self.rect().adjusted(4, 2, -4, -2)
        if self._active:
            accent_line = r.adjusted(0, 0, r.width() - r.width(), 0)
            p.setBrush(QColor(T("SIDEBAR_ACTIVE")))
            p.setPen(Qt.PenStyle.NoPen)
            p.drawRoundedRect(r, 8, 8)
            bar = QRect(r.left(), r.top() + 6, 3, r.height() - 12)
            p.setBrush(QColor(T("ACCENT")))
            p.drawRoundedRect(bar, 2, 2)
        elif self._hovered:
            c = QColor(T("BG_SURFACE"))
            c.setAlpha(180)
            p.setBrush(c)
            p.setPen(Qt.PenStyle.NoPen)
            p.drawRoundedRect(r, 8, 8)


class Sidebar(QWidget):
    new_chat_clicked = pyqtSignal()
    session_selected = pyqtSignal(str)
    session_deleted  = pyqtSignal(str)

    def __init__(self, parent=None):
        super().__init__(parent)
        self.setFixedWidth(SIDEBAR_W)
        self._items: Dict[str, HistoryItem] = {}
        self._build()

    def _build(self):
        lay = QVBoxLayout(self)
        lay.setContentsMargins(0, 0, 0, 0)
        lay.setSpacing(0)

        self.header = SidebarHeader()
        self.header.new_chat_clicked.connect(self.new_chat_clicked)
        lay.addWidget(self.header)

        div = QFrame()
        div.setFixedHeight(1)
        div.setStyleSheet(f"background:{T('BORDER')};")
        lay.addWidget(div)

        sec = QLabel("Recent")
        sec.setContentsMargins(16, 14, 16, 6)
        sec.setStyleSheet(
            f"color:{T('TXT_MUTED')};font-size:10px;font-weight:700;"
            "letter-spacing:1.2px;text-transform:uppercase;background:transparent;"
        )
        lay.addWidget(sec)

        scroll = QScrollArea()
        scroll.setWidgetResizable(True)
        scroll.setHorizontalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAlwaysOff)
        scroll.setVerticalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAsNeeded)
        scroll.setFrameShape(QFrame.Shape.NoFrame)
        scroll.setStyleSheet(f"""
            QScrollArea {{background:transparent;border:none;}}
            QScrollBar:vertical {{width:3px;background:transparent;}}
            QScrollBar::handle:vertical {{background:{T('BORDER')};border-radius:2px;min-height:24px;}}
            QScrollBar::add-line:vertical,QScrollBar::sub-line:vertical {{height:0;}}
        """)
        self._scroll = scroll

        self._list_container = QWidget()
        self._list_container.setStyleSheet("background:transparent;")
        self._list_layout = QVBoxLayout(self._list_container)
        self._list_layout.setContentsMargins(6, 0, 6, 16)
        self._list_layout.setSpacing(1)
        self._list_layout.addStretch()
        scroll.setWidget(self._list_container)
        lay.addWidget(scroll, 1)

        # Bottom strip
        bdiv = QFrame()
        bdiv.setFixedHeight(1)
        bdiv.setStyleSheet(f"background:{T('BORDER')};")
        lay.addWidget(bdiv)

        bottom = QWidget()
        bottom.setFixedHeight(56)
        bottom.setStyleSheet("background:transparent;")
        bl = QHBoxLayout(bottom)
        bl.setContentsMargins(14, 0, 14, 0)
        bl.setSpacing(10)

        avatar = QWidget()
        avatar.setFixedSize(30, 30)
        avatar.setStyleSheet(
            f"background:qlineargradient(x1:0,y1:0,x2:1,y2:1,"
            f"stop:0 {T('ACCENT')},stop:1 {T('ACCENT_ALT')});"
            "border-radius:15px;"
        )
        bl.addWidget(avatar)

        u_lbl = QLabel("Peka User")
        u_lbl.setStyleSheet(
            f"color:{T('TXT_SECONDARY')};font-size:13px;background:transparent;"
        )
        bl.addWidget(u_lbl, 1)
        lay.addWidget(bottom)

    def paintEvent(self, _):
        p = QPainter(self)
        p.fillRect(self.rect(), QColor(T("BG_SIDEBAR")))
        p.setPen(QColor(T("BORDER")))
        p.drawLine(self.width() - 1, 0, self.width() - 1, self.height())

    def refresh(self, titles: Dict[str, str], current_id: str):
        sb_val = self._scroll.verticalScrollBar().value()

        for item in list(self._items.values()):
            self._list_layout.removeWidget(item)
            item.deleteLater()
        self._items.clear()

        for sid in reversed(list(titles.keys())):
            item = HistoryItem(sid, titles[sid], sid == current_id)
            item.clicked.connect(self.session_selected)
            item.delete_clicked.connect(self.session_deleted)
            self._list_layout.insertWidget(0, item)
            self._items[sid] = item

        QTimer.singleShot(50, lambda v=sb_val: self._scroll.verticalScrollBar().setValue(v))

    def set_active(self, sid: str):
        for s, item in self._items.items():
            item.set_active(s == sid)


# ── Status indicator ──────────────────────────────────────────────────────────
class StatusDot(QWidget):
    """Small animated dot showing connection/mic state."""
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setFixedSize(8, 8)
        self._state  = "idle"        # idle | listening | thinking | error | muted
        self._alpha  = 255
        self._dir    = -1
        self._timer  = QTimer(self)
        self._timer.timeout.connect(self._tick)
        self._timer.start(40)

    def set_state(self, state: str):
        self._state = state
        self.update()

    def _tick(self):
        if self._state in ("listening", "thinking"):
            self._alpha += self._dir * 8
            if self._alpha <= 80 or self._alpha >= 255:
                self._dir *= -1
                self._alpha = max(80, min(255, self._alpha))
        else:
            self._alpha = 255
        self.update()

    def paintEvent(self, _):
        colors = {
            "idle":      T("TXT_MUTED"),
            "listening": T("SUCCESS"),
            "thinking":  T("ACCENT"),
            "error":     T("ERROR"),
            "muted":     T("ERROR"),
        }
        p = QPainter(self)
        p.setRenderHint(QPainter.RenderHint.Antialiasing)
        c = QColor(colors.get(self._state, T("TXT_MUTED")))
        c.setAlpha(self._alpha)
        p.setBrush(c)
        p.setPen(Qt.PenStyle.NoPen)
        p.drawEllipse(0, 0, 8, 8)


# ── Input box ─────────────────────────────────────────────────────────────────
class InputBox(QTextEdit):
    send_requested = pyqtSignal()

    def __init__(self, parent=None):
        super().__init__(parent)
        self.setPlaceholderText("Message Peka…   Shift+Enter for newline")
        self.setAcceptRichText(False)
        self.setVerticalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAsNeeded)
        self.setHorizontalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAlwaysOff)
        self.setFixedHeight(46)
        self.document().contentsChanged.connect(self._resize)
        self._apply_style()

    def _apply_style(self):
        self.setStyleSheet(f"""
            QTextEdit {{
                background:transparent;color:{T('TXT_PRIMARY')};
                border:none;font-size:15px;
                font-family:'Segoe UI Variable','Segoe UI','SF Pro Text',Arial,sans-serif;
                padding:0;selection-background-color:{T('ACCENT_GLOW')};
            }}
            QScrollBar:vertical {{width:4px;background:transparent;}}
            QScrollBar::handle:vertical {{background:{T('BORDER')};border-radius:2px;}}
            QScrollBar::add-line:vertical,QScrollBar::sub-line:vertical {{height:0;}}
        """)

    def _resize(self):
        doc_h = int(self.document().size().height())
        new_h = max(46, min(doc_h + 20, 220))
        self.setFixedHeight(new_h)

    def reset_height(self):
        self.setFixedHeight(46)

    def keyPressEvent(self, e: QKeyEvent):
        if e.key() in (Qt.Key.Key_Return, Qt.Key.Key_Enter):
            if not (e.modifiers() & Qt.KeyboardModifier.ShiftModifier):
                self.send_requested.emit()
                return
        super().keyPressEvent(e)


class SendButton(QPushButton):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setFixedSize(36, 36)
        self.setCursor(QCursor(Qt.CursorShape.PointingHandCursor))
        self.setToolTip("Send  (Enter)")
        self._active = False
        self._update_style()

    def set_active(self, v: bool):
        if self._active != v:
            self._active = v
            self._update_style()

    def _update_style(self):
        if self._active:
            self.setText("↑")
            self.setStyleSheet(f"""
                QPushButton {{
                    background:qlineargradient(x1:0,y1:0,x2:1,y2:1,
                        stop:0 {T('ACCENT')},stop:1 {T('ACCENT_ALT')});
                    color:white;border:none;border-radius:18px;
                    font-size:16px;font-weight:bold;
                }}
                QPushButton:hover {{background:{T('ACCENT_SOFT')};}}
                QPushButton:pressed {{opacity:0.85;}}
            """)
        else:
            self.setText("↑")
            self.setStyleSheet(f"""
                QPushButton {{
                    background:{T('BG_SURFACE')};color:{T('TXT_MUTED')};
                    border:1px solid {T('BORDER')};border-radius:18px;font-size:16px;
                }}
                QPushButton:hover {{border-color:{T('ACCENT')};color:{T('ACCENT')};}}
            """)


class AttachButton(QPushButton):
    def __init__(self, parent=None):
        super().__init__("⊕", parent)
        self.setFixedSize(34, 34)
        self.setCursor(QCursor(Qt.CursorShape.PointingHandCursor))
        self.setToolTip("Attach file  (drag & drop also works)")
        self._apply_style()

    def _apply_style(self):
        self.setStyleSheet(f"""
            QPushButton {{
                background:transparent;color:{T('TXT_MUTED')};
                border:none;border-radius:17px;font-size:18px;font-weight:300;
            }}
            QPushButton:hover {{color:{T('ACCENT')};background:{T('BG_SURFACE')};}}
        """)


class ModelChip(QPushButton):
    def __init__(self, label: str = "Gemini 2.5 Flash", parent=None):
        super().__init__(parent)
        self._label = label
        self.setText(f"{label}  ▾")
        self.setCursor(QCursor(Qt.CursorShape.PointingHandCursor))
        self.setFixedHeight(28)
        self.setToolTip("Switch model")
        self._apply_style()

    def set_label(self, label: str):
        self._label = label
        self.setText(f"{label}  ▾")

    def _apply_style(self):
        self.setStyleSheet(f"""
            QPushButton {{
                background:{T('BG_SURFACE')};color:{T('TXT_SECONDARY')};
                border:1px solid {T('BORDER')};border-radius:14px;
                padding:0 12px;font-size:12px;
                font-family:'Segoe UI Variable','Segoe UI',sans-serif;
            }}
            QPushButton:hover {{
                border-color:{T('ACCENT')};color:{T('ACCENT')};
            }}
        """)


class CharCounter(QLabel):
    _WARN  = 300
    _LIMIT = 600

    def __init__(self, parent=None):
        super().__init__(parent)
        self._apply_style(0)
        self.setVisible(False)

    def _apply_style(self, n: int):
        if n >= self._LIMIT:
            color = T("ERROR")
        elif n >= self._WARN:
            color = T("ACCENT")
        else:
            color = T("TXT_MUTED")
        self.setStyleSheet(
            f"color:{color};font-size:11px;background:transparent;"
        )

    def update_count(self, n: int):
        if n >= self._WARN:
            self.setText(f"{n} chars")
            self._apply_style(n)
            self.setVisible(True)
        else:
            self.setVisible(False)


class InputPanel(QWidget):
    file_dropped = pyqtSignal(str)

    def __init__(self, parent=None):
        super().__init__(parent)
        self.setAcceptDrops(True)
        self._focused  = False
        self._dragging = False
        self._build()

    def _build(self):
        outer = QVBoxLayout(self)
        outer.setContentsMargins(24, 8, 24, 24)
        outer.setSpacing(8)
        outer.setAlignment(Qt.AlignmentFlag.AlignHCenter)

        self.card = QWidget()
        self.card.setObjectName("inputCard")
        self.card.setMaximumWidth(CONTENT_MAX_W)
        self.card.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Fixed)
        self._style_card(False, False)

        card_lay = QVBoxLayout(self.card)
        card_lay.setContentsMargins(16, 14, 14, 12)
        card_lay.setSpacing(10)

        self.input = InputBox()
        self.input.document().contentsChanged.connect(self._on_content_changed)
        self.input.installEventFilter(self)
        card_lay.addWidget(self.input)

        bottom = QHBoxLayout()
        bottom.setSpacing(6)

        self.attach_btn = AttachButton()
        bottom.addWidget(self.attach_btn)

        self.model_chip = ModelChip()
        bottom.addWidget(self.model_chip)

        bottom.addStretch()

        self.char_counter = CharCounter()
        bottom.addWidget(self.char_counter)

        self.send_btn = SendButton()
        bottom.addWidget(self.send_btn)

        card_lay.addLayout(bottom)
        outer.addWidget(self.card, alignment=Qt.AlignmentFlag.AlignHCenter)

        hint = QLabel("Peka can make mistakes · verify important information")
        hint.setStyleSheet(
            f"color:{T('TXT_MUTED')};font-size:11px;background:transparent;"
        )
        hint.setAlignment(Qt.AlignmentFlag.AlignCenter)
        outer.addWidget(hint)

    def eventFilter(self, obj, event):
        if obj is self.input:
            if event.type() == QEvent.Type.FocusIn:
                self._focused = True
                self._style_card(True, self._dragging)
            elif event.type() == QEvent.Type.FocusOut:
                self._focused = False
                self._style_card(False, self._dragging)
        return super().eventFilter(obj, event)

    def _style_card(self, focused: bool, drag_over: bool):
        if drag_over:
            border = T("ACCENT")
            bg     = T("ACCENT_GLOW")
        elif focused:
            border = T("BORDER_FOCUS")
            bg     = T("BG_INPUT")
        else:
            border = T("BORDER")
            bg     = T("BG_INPUT")
        self.card.setStyleSheet(f"""
            QWidget#inputCard {{
                background:{bg};
                border:1.5px solid {border};
                border-radius:18px;
            }}
        """)

    def _on_content_changed(self):
        n = len(self.input.toPlainText())
        self.char_counter.update_count(n)
        self.send_btn.set_active(n > 0)

    def focus_input(self):
        self.input.setFocus()

    def dragEnterEvent(self, e: QDragEnterEvent):
        if e.mimeData().hasUrls():
            e.acceptProposedAction()
            self._dragging = True
            self._style_card(self._focused, True)

    def dragLeaveEvent(self, _):
        self._dragging = False
        self._style_card(self._focused, False)

    def dropEvent(self, e: QDropEvent):
        self._dragging = False
        self._style_card(self._focused, False)
        urls = e.mimeData().urls()
        if urls:
            self.file_dropped.emit(urls[0].toLocalFile())


# ── Message Bubble ────────────────────────────────────────────────────────────
class MessageBubble(QFrame):
    _CODE_BLOCK_RE  = re.compile(r"```(?:\w+)?\n?(.*?)```", re.DOTALL)
    _INLINE_CODE_RE = re.compile(r"`([^`]+)`")
    _BOLD_RE        = re.compile(r"\*\*(.+?)\*\*")
    _ITALIC_RE      = re.compile(r"\*(.+?)\*")
    _URL_RE         = re.compile(r"(https?://[^\s<>\"']+)")

    def __init__(self, role: str, text: str, timestamp: float = 0.0, parent=None):
        super().__init__(parent)
        self.role       = role
        self._text      = text
        self._timestamp = timestamp or time.time()
        self._build()

    def _word_count(self) -> int:
        return len(self._text.split())

    def _fmt_time(self) -> str:
        dt = datetime.fromtimestamp(self._timestamp)
        hour = dt.strftime("%I").lstrip("0") or "12"
        return f"{hour}:{dt.strftime('%M %p')}"

    def _build(self):
        lay = QVBoxLayout(self)
        lay.setSpacing(6)
        if self.role == "user":
            lay.setContentsMargins(120, 8, 24, 8)
        else:
            lay.setContentsMargins(24, 8, 120, 8)

        role_row = QHBoxLayout()
        role_row.setSpacing(8)

        if self.role != "user":
            logo = PekaLogoMark(size=20, animated=False)
            role_row.addWidget(logo, alignment=Qt.AlignmentFlag.AlignVCenter)

        role_lbl = QLabel("You" if self.role == "user" else "Peka")
        role_lbl.setStyleSheet(
            f"color:{T('TXT_SECONDARY')};font-size:12px;font-weight:600;"
            "background:transparent;letter-spacing:0.2px;"
        )
        role_row.addWidget(role_lbl)

        if self.role != "user":
            wc = self._word_count()
            badge = QLabel(f"{wc} words")
            badge.setStyleSheet(
                f"color:{T('TXT_MUTED')};font-size:11px;background:transparent;"
            )
            role_row.addWidget(badge)

        role_row.addStretch()

        ts_lbl = QLabel(self._fmt_time())
        ts_lbl.setStyleSheet(
            f"color:{T('TXT_MUTED')};font-size:11px;background:transparent;"
        )
        role_row.addWidget(ts_lbl)

        self._copy_btn = QPushButton("Copy")
        self._copy_btn.setFixedHeight(22)
        self._copy_btn.setCursor(QCursor(Qt.CursorShape.PointingHandCursor))
        self._copy_btn.setToolTip("Copy message")
        self._copy_btn.clicked.connect(self._copy)
        self._copy_btn.setStyleSheet(f"""
            QPushButton {{
                background:transparent;color:{T('TXT_MUTED')};
                border:none;font-size:11px;padding:0 8px;border-radius:5px;
            }}
            QPushButton:hover {{color:{T('ACCENT')};background:{T('BG_SURFACE')};}}
        """)
        role_row.addWidget(self._copy_btn)
        lay.addLayout(role_row)

        content = QLabel()
        content.setWordWrap(True)
        content.setTextInteractionFlags(
            Qt.TextInteractionFlag.TextSelectableByMouse
            | Qt.TextInteractionFlag.TextSelectableByKeyboard
            | Qt.TextInteractionFlag.LinksAccessibleByMouse
        )
        content.setOpenExternalLinks(True)
        content.setTextFormat(Qt.TextFormat.RichText)
        content.setText(self._format(self._text))

        if self.role == "user":
            content.setStyleSheet(f"""
                background:{T('BG_MSG_USER')};color:{T('TXT_PRIMARY')};
                font-size:15px;border-radius:16px;
                padding:12px 18px;
                font-family:'Segoe UI Variable','Segoe UI','SF Pro Text',Arial,sans-serif;
            """)
        else:
            content.setStyleSheet(f"""
                color:{T('TXT_PRIMARY')};font-size:15px;line-height:1.8;
                padding:2px 0 0 28px;
                font-family:'Segoe UI Variable','Segoe UI','SF Pro Text',Arial,sans-serif;
                background:transparent;
            """)
        lay.addWidget(content)

    def _copy(self):
        QApplication.clipboard().setText(self._text)
        self._copy_btn.setText("✓ Copied")
        QTimer.singleShot(2000, lambda: self._copy_btn.setText("Copy"))

    def _format(self, text: str) -> str:
        code_bg    = T("CODE_BG")
        code_color = T("TXT_PRIMARY")
        brd        = T("BORDER")
        acc        = T("ACCENT")

        text = (
            text
            .replace("&", "&amp;")
            .replace("<", "&lt;")
            .replace(">", "&gt;")
        )
        text = self._CODE_BLOCK_RE.sub(
            f'<pre style="background:{code_bg};border:1px solid {brd};'
            f'border-radius:10px;padding:14px 16px;font-family:monospace;'
            f'font-size:13px;color:{code_color};white-space:pre-wrap;margin:6px 0;">'
            r'\g<1></pre>',
            text,
        )
        text = self._INLINE_CODE_RE.sub(
            f'<code style="background:{code_bg};color:{acc};'
            f'padding:2px 6px;border-radius:5px;font-family:monospace;font-size:13px;">'
            r'\1</code>',
            text,
        )
        text = self._BOLD_RE.sub(r"<b>\1</b>", text)
        text = self._ITALIC_RE.sub(r"<i>\1</i>", text)
        text = self._URL_RE.sub(
            f'<a href="\\1" style="color:{acc};text-decoration:none;">\\1</a>',
            text,
        )
        text = text.replace("\n", "<br>")
        return text


# ── Typing Indicator ──────────────────────────────────────────────────────────
class TypingDot(QWidget):
    def __init__(self, phase_offset: float, parent=None):
        super().__init__(parent)
        self.setFixedSize(9, 20)
        self._phase   = phase_offset
        self._y       = 0.0
        self._cleaned = False
        self._timer   = QTimer(self)
        self._timer.timeout.connect(self._tick)
        self._timer.start(33)

    def _tick(self):
        if self._cleaned:
            return
        self._phase += 0.10
        self._y = math.sin(self._phase) * 3.5
        self.update()

    def cleanup(self):
        if self._cleaned:
            return
        self._cleaned = True
        self._timer.stop()
        self._timer.deleteLater()

    def paintEvent(self, _):
        p = QPainter(self)
        p.setRenderHint(QPainter.RenderHint.Antialiasing)
        c = QColor(T("ACCENT"))
        c.setAlpha(200)
        p.setBrush(c)
        p.setPen(Qt.PenStyle.NoPen)
        p.drawEllipse(0, int(6 + self._y), 8, 8)


class TypingIndicator(QWidget):
    def __init__(self, parent=None):
        super().__init__(parent)
        self._dots: List[TypingDot] = []
        lay = QHBoxLayout(self)
        lay.setContentsMargins(28, 4, 8, 4)
        lay.setSpacing(5)
        for offset in (0.0, 1.2, 2.4):
            d = TypingDot(offset)
            self._dots.append(d)
            lay.addWidget(d)
        lay.addStretch()

    def cleanup(self):
        for d in self._dots:
            d.cleanup()
        self._dots.clear()


# ── Welcome Screen ────────────────────────────────────────────────────────────
class WelcomeScreen(QWidget):
    suggestion_clicked = pyqtSignal(str)

    _SUGGESTIONS = [
        ("✦ Explain",    "Explain a complex concept clearly"),
        ("⌨ Code",       "Write and debug some code for me"),
        ("✂ Summarize",  "Summarize a document or article"),
        ("💡 Brainstorm", "Brainstorm creative ideas with me"),
    ]

    def __init__(self, parent=None):
        super().__init__(parent)
        self._angle = 0.0
        self._timer = QTimer(self)
        self._timer.timeout.connect(self._tick)
        self._timer.start(50)
        self._build()

    def _tick(self):
        self._angle = (self._angle + 0.3) % 360
        self.update()

    def paintEvent(self, event):
        p = QPainter(self)
        p.setRenderHint(QPainter.RenderHint.Antialiasing)
        p.fillRect(self.rect(), QColor(T("BG_PRIMARY")))

        cx = self.width() / 2
        cy = self.height() / 2
        r  = max(self.width(), self.height()) * 0.65

        grad = QRadialGradient(cx, cy, r)
        a_color = QColor(T("GRADIENT_A"))
        b_color = QColor(T("GRADIENT_B"))
        grad.setColorAt(0.0, a_color)
        grad.setColorAt(0.5, b_color)
        grad.setColorAt(1.0, QColor(0, 0, 0, 0))
        p.fillRect(self.rect(), QBrush(grad))

    def _build(self):
        lay = QVBoxLayout(self)
        lay.setAlignment(Qt.AlignmentFlag.AlignCenter)
        lay.setSpacing(0)

        self.logo = PekaLogoMark(size=64, animated=True)
        lay.addWidget(self.logo, alignment=Qt.AlignmentFlag.AlignCenter)
        lay.addSpacing(32)

        title = QLabel("How can I help you today?")
        title.setStyleSheet(f"""
            color:{T('TXT_PRIMARY')};font-size:32px;font-weight:300;
            font-family:'Segoe UI Variable Display','Segoe UI','SF Pro Display',sans-serif;
            letter-spacing:-0.8px;background:transparent;
        """)
        title.setAlignment(Qt.AlignmentFlag.AlignCenter)
        lay.addWidget(title)

        lay.addSpacing(10)

        sub = QLabel("Powered by Gemini · Always ready")
        sub.setStyleSheet(
            f"color:{T('TXT_MUTED')};font-size:15px;background:transparent;"
        )
        sub.setAlignment(Qt.AlignmentFlag.AlignCenter)
        lay.addWidget(sub)

        lay.addSpacing(52)

        chips_row = QHBoxLayout()
        chips_row.setSpacing(10)
        chips_row.setAlignment(Qt.AlignmentFlag.AlignCenter)

        for label, suggestion in self._SUGGESTIONS:
            chip = QPushButton(label)
            chip.setCursor(QCursor(Qt.CursorShape.PointingHandCursor))
            chip.setFixedHeight(38)
            chip.setToolTip(suggestion)
            chip.setStyleSheet(f"""
                QPushButton {{
                    background:{T('BG_SURFACE')};color:{T('TXT_SECONDARY')};
                    border:1px solid {T('BORDER')};border-radius:19px;
                    padding:0 20px;font-size:13px;
                    font-family:'Segoe UI Variable','Segoe UI',sans-serif;
                }}
                QPushButton:hover {{
                    border-color:{T('ACCENT')};color:{T('ACCENT')};
                    background:{T('ACCENT_GLOW')};
                }}
                QPushButton:pressed {{
                    background:{T('SIDEBAR_ACTIVE')};
                }}
            """)
            chip.clicked.connect(
                lambda _checked, s=suggestion: self.suggestion_clicked.emit(s)
            )
            chips_row.addWidget(chip)

        lay.addLayout(chips_row)

    def cleanup(self):
        self._timer.stop()
        self._timer.deleteLater()
        if hasattr(self, "logo"):
            self.logo.cleanup()


# ── Scroll-to-bottom button ───────────────────────────────────────────────────
class ScrollBottomBtn(QPushButton):
    def __init__(self, parent=None):
        super().__init__("↓", parent)
        self.setFixedSize(38, 38)
        self.setCursor(QCursor(Qt.CursorShape.PointingHandCursor))
        self.setToolTip("Scroll to bottom")
        self._apply_style()

    def _apply_style(self):
        self.setStyleSheet(f"""
            QPushButton {{
                background:{T('BG_SURFACE')};color:{T('TXT_SECONDARY')};
                border:1px solid {T('BORDER')};border-radius:19px;
                font-size:16px;font-weight:bold;
            }}
            QPushButton:hover {{
                border-color:{T('ACCENT')};color:{T('ACCENT')};
                background:{T('ACCENT_GLOW')};
            }}
        """)


# ── Chat View ─────────────────────────────────────────────────────────────────
class ChatView(QScrollArea):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setWidgetResizable(True)
        self.setHorizontalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAlwaysOff)
        self.setVerticalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAsNeeded)
        self.setFrameShape(QFrame.Shape.NoFrame)
        self._apply_style()

        self._container = QWidget()
        self._container.setStyleSheet("background:transparent;")
        self._lay = QVBoxLayout(self._container)
        self._lay.setContentsMargins(0, 28, 0, 28)
        self._lay.setSpacing(0)
        self._lay.addStretch()
        self.setWidget(self._container)

        self._bubbles: List[QWidget] = []
        self._typing_wrapper:    Optional[QWidget]          = None
        self._typing_indicator:  Optional[TypingIndicator]  = None
        self._typing_logo:       Optional[PekaLogoMark]     = None

        self._scroll_btn = ScrollBottomBtn(self)
        self._scroll_btn.setVisible(False)
        self._scroll_btn.clicked.connect(self._scroll_bottom)
        self.verticalScrollBar().valueChanged.connect(self._on_scroll)

    def _apply_style(self):
        self.setStyleSheet(f"""
            QScrollArea {{background:transparent;border:none;}}
            QScrollBar:vertical {{
                width:5px;background:transparent;margin:0;
            }}
            QScrollBar::handle:vertical {{
                background:{T('BORDER')};border-radius:3px;min-height:24px;
            }}
            QScrollBar::add-line:vertical,QScrollBar::sub-line:vertical {{height:0;}}
        """)

    def resizeEvent(self, e):
        super().resizeEvent(e)
        self._reposition_scroll_btn()

    def _reposition_scroll_btn(self):
        btn = self._scroll_btn
        btn.move(
            self.width() - btn.width() - 20,
            self.height() - btn.height() - 20,
        )

    def _on_scroll(self, val: int):
        sb = self.verticalScrollBar()
        at_bottom = val >= sb.maximum() - 30
        self._scroll_btn.setVisible(not at_bottom and sb.maximum() > 60)

    def _wrap(self, widget: QWidget) -> QWidget:
        outer = QWidget()
        outer.setStyleSheet("background:transparent;")
        ol = QHBoxLayout(outer)
        ol.setContentsMargins(0, 0, 0, 0)
        ol.addStretch(1)
        widget.setMaximumWidth(CONTENT_MAX_W)
        widget.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Preferred)
        ol.addWidget(widget, 8)
        ol.addStretch(1)
        return outer

    def add_message(self, role: str, text: str, timestamp: float = 0.0, animate: bool = True):
        bubble  = MessageBubble(role, text, timestamp)
        wrapper = self._wrap(bubble)
        self._bubbles.append(wrapper)
        self._lay.insertWidget(self._lay.count() - 1, wrapper)

        if animate:
            anim = make_fade_in(wrapper, duration=280)
            anim.start(QAbstractAnimation.DeletionPolicy.DeleteWhenStopped)

        QTimer.singleShot(80, self._scroll_bottom)

    def show_typing(self):
        if self._typing_wrapper is not None:
            return

        self._typing_indicator = TypingIndicator()
        self._typing_logo = PekaLogoMark(size=20, animated=True)
        self._typing_logo.set_thinking(True)

        inner = QWidget()
        inner.setStyleSheet("background:transparent;")
        il = QVBoxLayout(inner)
        il.setContentsMargins(24, 8, 120, 8)
        il.setSpacing(6)

        rr = QHBoxLayout()
        rr.setSpacing(8)
        rr.addWidget(self._typing_logo, alignment=Qt.AlignmentFlag.AlignVCenter)
        rl = QLabel("Peka")
        rl.setStyleSheet(
            f"color:{T('TXT_SECONDARY')};font-size:12px;font-weight:600;"
            "background:transparent;"
        )
        rr.addWidget(rl)
        rr.addStretch()
        il.addLayout(rr)
        il.addWidget(self._typing_indicator)

        self._typing_wrapper = self._wrap(inner)

        anim = make_fade_in(self._typing_wrapper, duration=200)
        self._lay.insertWidget(self._lay.count() - 1, self._typing_wrapper)
        anim.start(QAbstractAnimation.DeletionPolicy.DeleteWhenStopped)

        QTimer.singleShot(80, self._scroll_bottom)

    def hide_typing(self):
        if self._typing_wrapper is None:
            return
        if self._typing_indicator:
            self._typing_indicator.cleanup()
            self._typing_indicator = None
        if self._typing_logo:
            self._typing_logo.cleanup()
            self._typing_logo = None
        self._lay.removeWidget(self._typing_wrapper)
        self._typing_wrapper.deleteLater()
        self._typing_wrapper = None

    def clear_messages(self):
        for w in self._bubbles:
            self._lay.removeWidget(w)
            w.deleteLater()
        self._bubbles.clear()

    def load_history(self, messages: List[Dict]):
        self.clear_messages()
        for msg in messages:
            ts = msg.get("timestamp", 0.0)
            self.add_message(msg["role"], msg["content"], timestamp=ts, animate=False)
        QTimer.singleShot(120, self._scroll_bottom)

    def _scroll_bottom(self):
        sb = self.verticalScrollBar()
        sb.setValue(sb.maximum())

    def cleanup(self):
        self.hide_typing()
        self.clear_messages()


# ── Topbar ────────────────────────────────────────────────────────────────────
class Topbar(QWidget):
    theme_toggled = pyqtSignal(str)

    def __init__(self, parent=None):
        super().__init__(parent)
        self.setFixedHeight(56)
        self._build()

    def _build(self):
        lay = QHBoxLayout(self)
        lay.setContentsMargins(20, 0, 16, 0)
        lay.setSpacing(8)
        lay.addStretch()

        self._status_dot = StatusDot()
        lay.addWidget(self._status_dot, alignment=Qt.AlignmentFlag.AlignVCenter)

        self._status_lbl = QLabel("Ready")
        self._status_lbl.setStyleSheet(
            f"color:{T('TXT_MUTED')};font-size:12px;background:transparent;"
        )
        lay.addWidget(self._status_lbl)

        lay.addSpacing(12)

        self._theme_btn = self._make_btn(
            "☀  Light" if _current_theme == "dark" else "◑  Dark"
        )
        self._theme_btn.setToolTip("Toggle theme  (Ctrl+T)")
        self._theme_btn.clicked.connect(self._toggle_theme)
        lay.addWidget(self._theme_btn)

        shortcuts_btn = self._make_btn("⌨  Shortcuts")
        shortcuts_btn.setToolTip("Keyboard shortcuts  (Ctrl+?)")
        shortcuts_btn.clicked.connect(self._show_shortcuts)
        lay.addWidget(shortcuts_btn)

    def _make_btn(self, label: str) -> QPushButton:
        btn = QPushButton(label)
        btn.setFixedHeight(30)
        btn.setCursor(QCursor(Qt.CursorShape.PointingHandCursor))
        btn.setStyleSheet(f"""
            QPushButton {{
                background:{T('BG_SURFACE')};color:{T('TXT_SECONDARY')};
                border:1px solid {T('BORDER')};border-radius:8px;
                padding:0 14px;font-size:12px;
            }}
            QPushButton:hover {{color:{T('TXT_PRIMARY')};border-color:{T('ACCENT')};}}
        """)
        return btn

    def set_status(self, state: str, label: str):
        self._status_dot.set_state(state)
        self._status_lbl.setText(label)

    def _toggle_theme(self):
        new_t = "light" if _current_theme == "dark" else "dark"
        self._theme_btn.setText("◑  Dark" if new_t == "light" else "☀  Light")
        self.theme_toggled.emit(new_t)

    def _show_shortcuts(self):
        msg = (
            "<b style='font-size:14px;'>⌨  Keyboard Shortcuts</b><br><br>"
            "<code>Ctrl+N</code> &nbsp;— New conversation<br>"
            "<code>Ctrl+/</code> &nbsp;— Focus input<br>"
            "<code>Ctrl+M</code> &nbsp;— Toggle mute<br>"
            "<code>Ctrl+T</code> &nbsp;— Toggle theme<br>"
            "<code>Ctrl+?</code> &nbsp;— This dialog<br>"
            "<code>Escape</code> &nbsp;— Clear input<br>"
            "<code>Enter</code> &nbsp;&nbsp;— Send message<br>"
            "<code>Shift+Enter</code> — New line<br>"
        )
        QMessageBox.information(self, "Peka — Shortcuts", msg)

    def paintEvent(self, _):
        p = QPainter(self)
        p.fillRect(self.rect(), QColor(T("BG_PRIMARY")))
        p.setPen(QColor(T("BORDER")))
        p.drawLine(0, self.height() - 1, self.width(), self.height() - 1)


# ── Main Window ───────────────────────────────────────────────────────────────
class PekaMainWindow(QMainWindow):
    _log_sig   = pyqtSignal(str, bool)
    _state_sig = pyqtSignal(str)

    def __init__(self, face_path: str = "face.png"):
        super().__init__()
        self.setWindowTitle("Peka")
        self.resize(1160, 800)
        self.setMinimumSize(860, 580)

        self.on_text_command = None
        self._muted          = False
        self._current_file: Optional[str] = None
        self._current_model  = "gemini-2.5-flash"
        self._is_loading     = False

        self.peka = None  # will be set by main.py

        self.history_manager = ChatHistoryManager()
        load_theme()

        self._build_ui()
        self._setup_shortcuts()

        self._log_sig.connect(self._add_message)
        self._state_sig.connect(self._apply_state)

        self._ready = self._check_config()
        if not self._ready:
            QTimer.singleShot(200, self._prompt_api_key_setup)

    def set_peka(self, peka_instance):
        """Store a reference to the PekaLive session for mute sync."""
        self.peka = peka_instance

    # ── UI construction ──────────────────────────────────────────────────────
    def _build_ui(self):
        self._apply_global_style()

        central = QWidget()
        self.setCentralWidget(central)
        root = QHBoxLayout(central)
        root.setContentsMargins(0, 0, 0, 0)
        root.setSpacing(0)

        self.sidebar = Sidebar()
        self.sidebar.new_chat_clicked.connect(self._new_chat)
        self.sidebar.session_selected.connect(self._on_session_selected)
        self.sidebar.session_deleted.connect(self._on_session_deleted)
        root.addWidget(self.sidebar)

        main = QWidget()
        main.setStyleSheet(f"background:{T('BG_PRIMARY')};")
        main_lay = QVBoxLayout(main)
        main_lay.setContentsMargins(0, 0, 0, 0)
        main_lay.setSpacing(0)

        self.topbar = Topbar()
        self.topbar.theme_toggled.connect(self._on_theme_toggle)
        main_lay.addWidget(self.topbar)

        self.stack = QStackedWidget()
        self.stack.setStyleSheet(f"background:{T('BG_PRIMARY')};")

        self.welcome = WelcomeScreen()
        self.welcome.suggestion_clicked.connect(self._on_suggestion)
        self.stack.addWidget(self.welcome)   # index 0

        self.chat_view = ChatView()
        self.stack.addWidget(self.chat_view) # index 1
        main_lay.addWidget(self.stack, 1)

        self.input_panel = InputPanel()
        main_lay.addWidget(self.input_panel)
        root.addWidget(main, 1)

        # Wire signals
        ip = self.input_panel
        ip.input.send_requested.connect(self._send)
        ip.send_btn.clicked.connect(self._send)
        ip.model_chip.clicked.connect(self._show_model_menu)
        ip.attach_btn.clicked.connect(self._browse_file)
        ip.file_dropped.connect(self._handle_file)

        QTimer.singleShot(100, ip.focus_input)
        self._refresh_sidebar()
        self._load_current_session()

    def _apply_global_style(self):
        self.setStyleSheet(f"""
            QMainWindow {{background:{T('BG_PRIMARY')};}}
            QWidget {{background:{T('BG_PRIMARY')};color:{T('TXT_PRIMARY')};}}
            QMessageBox {{background:{T('BG_SURFACE')};}}
            QInputDialog {{background:{T('BG_SURFACE')};}}
            QToolTip {{
                background:{T('BG_SURFACE')};color:{T('TXT_PRIMARY')};
                border:1px solid {T('BORDER')};border-radius:8px;
                font-size:12px;padding:6px 12px;
            }}
        """)

    def _on_theme_toggle(self, new_theme: str):
        apply_theme(new_theme)
        self._refresh_styles()

    def _refresh_styles(self):
        self._apply_global_style()

        tb = self.topbar
        tb._theme_btn.setText("◑  Dark" if _current_theme == "light" else "☀  Light")
        tb.update()

        self.sidebar.update()
        self.sidebar.header._style_new_btn()
        self.sidebar.header.update()

        self.chat_view._apply_style()

        ip = self.input_panel
        ip.input._apply_style()
        ip.send_btn._update_style()
        ip.attach_btn._apply_style()
        ip.model_chip._apply_style()
        ip._style_card(ip._focused, ip._dragging)

        self.stack.setStyleSheet(f"background:{T('BG_PRIMARY')};")

        self.update()
        QApplication.processEvents()

    def _setup_shortcuts(self):
        QShortcut(QKeySequence("Ctrl+N"), self).activated.connect(self._new_chat)
        QShortcut(QKeySequence("Ctrl+/"), self).activated.connect(self.input_panel.focus_input)
        QShortcut(QKeySequence("Escape"),  self).activated.connect(self._clear_input)
        QShortcut(QKeySequence("Ctrl+M"), self).activated.connect(self._toggle_mute)
        QShortcut(QKeySequence("Ctrl+T"), self).activated.connect(
            lambda: self._on_theme_toggle("light" if _current_theme == "dark" else "dark")
        )
        QShortcut(QKeySequence("Ctrl+?"), self).activated.connect(
            self.topbar._show_shortcuts
        )

    # ── Sidebar helpers ───────────────────────────────────────────────────────
    def _refresh_sidebar(self):
        titles     = self.history_manager.get_session_titles()
        current_id = self.history_manager.current_session_id or ""
        self.sidebar.refresh(titles, current_id)

    def _load_current_session(self):
        sid  = self.history_manager.current_session_id
        msgs = self.history_manager.sessions.get(sid, []) if sid else []
        self.chat_view.load_history(msgs)
        self.stack.setCurrentIndex(1 if msgs else 0)

    def _on_session_selected(self, sid: str):
        if sid != self.history_manager.current_session_id:
            self.history_manager.load_session(sid)
            self.sidebar.set_active(sid)
            self._load_current_session()

    def _on_session_deleted(self, sid: str):
        reply = QMessageBox.question(
            self,
            "Delete conversation",
            "Permanently delete this conversation?",
            QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No,
        )
        if reply == QMessageBox.StandardButton.Yes:
            self.history_manager.delete_session(sid)
            self._refresh_sidebar()
            self._load_current_session()

    def _new_chat(self):
        self.history_manager.new_session()
        self._refresh_sidebar()
        self._load_current_session()
        self._clear_input()
        self.input_panel.focus_input()

    def _clear_input(self):
        self.input_panel.input.clear()
        self.input_panel.input.reset_height()
        self.input_panel.send_btn.set_active(False)
        self.input_panel.char_counter.setVisible(False)

    def _on_suggestion(self, text: str):
        self.input_panel.input.setPlainText(text)
        cursor = self.input_panel.input.textCursor()
        cursor.movePosition(cursor.MoveOperation.End)
        self.input_panel.input.setTextCursor(cursor)
        self.input_panel.focus_input()

    # ── Send flow ─────────────────────────────────────────────────────────────
    def _send(self):
        if self._is_loading:
            return
        text = self.input_panel.input.toPlainText().strip()
        if not text:
            return
        self._clear_input()
        self.stack.setCurrentIndex(1)
        self._add_message(text, True)
        if self.on_text_command:
            threading.Thread(
                target=self.on_text_command, args=(text,), daemon=True
            ).start()
        self.chat_view.show_typing()
        self._is_loading = True
        self.topbar.set_status("thinking", "Thinking…")
        QTimer.singleShot(120_000, self._clear_stale_typing)

    def _clear_stale_typing(self):
        if self._is_loading:
            self.chat_view.hide_typing()
            self._is_loading = False
            self.topbar.set_status("listening", "Ready")

    @pyqtSlot(str, bool)
    def _add_message(self, text: str, is_user: bool):
        role = "user" if is_user else "assistant"
        self.chat_view.add_message(role, text)
        self.history_manager.add_message(role, text)
        if not is_user and self._is_loading:
            self.chat_view.hide_typing()
            self._is_loading = False
            self.topbar.set_status("listening", "Ready")
        self._refresh_sidebar()

    # ── Model menu ────────────────────────────────────────────────────────────
    def _show_model_menu(self):
        menu = QMenu(self)
        menu.setStyleSheet(f"""
            QMenu {{
                background:{T('BG_SURFACE')};border:1px solid {T('BORDER')};
                border-radius:12px;padding:6px;
            }}
            QMenu::item {{
                padding:10px 20px;border-radius:8px;
                color:{T('TXT_SECONDARY')};font-size:13px;
            }}
            QMenu::item:selected {{
                background:{T('BG_INPUT')};color:{T('TXT_PRIMARY')};
            }}
        """)
        for mid, label in MODELS:
            prefix = "● " if mid == self._current_model else "  "
            act = menu.addAction(prefix + label)
            act.setData(mid)

        chip       = self.input_panel.model_chip
        global_pos = chip.mapToGlobal(QPoint(0, 0))
        hint       = menu.sizeHint()
        popup_y    = global_pos.y() - hint.height() - 6
        screen     = QApplication.primaryScreen().availableGeometry()

        if popup_y < screen.top():
            popup_y = global_pos.y() + chip.height() + 6
        popup_x = max(screen.left(), min(global_pos.x(), screen.right() - hint.width()))

        chosen = menu.exec(QPoint(popup_x, popup_y))
        if chosen and chosen.data():
            self._current_model = chosen.data()
            lbl = next(l for m, l in MODELS if m == self._current_model)
            self.input_panel.model_chip.set_label(lbl)

    # ── File handling ─────────────────────────────────────────────────────────
    def _browse_file(self):
        path, _ = QFileDialog.getOpenFileName(
            self, "Attach file", str(Path.home()),
            "All Files (*.*);;Images (*.jpg *.png *.webp);;Documents (*.pdf *.txt *.docx);;Code (*.py *.js *.ts)",
        )
        if path:
            self._handle_file(path)

    def _handle_file(self, path: str):
        self._current_file = path
        name = Path(path).name
        self._log_sig.emit(f"📎 File attached: **{name}**", False)
        if self.on_text_command:
            msg = (
                f"[FILE_UPLOADED] path={path} | name={name} | "
                f"Tell the user '{name}' is attached and ask what to do with it."
            )
            threading.Thread(
                target=self.on_text_command, args=(msg,), daemon=True
            ).start()

    # ── Mute ──────────────────────────────────────────────────────────────────
    def _toggle_mute(self):
        self._muted = not self._muted
        if self._muted:
            self.topbar.set_status("muted", "Muted")
        else:
            self.topbar.set_status("listening", "Ready")
        # Sync with the backend thread‑safe event
        if self.peka:
            if self._muted:
                self.peka._audio_muted.set()
            else:
                self.peka._audio_muted.clear()
        self.set_state("MUTED" if self._muted else "LISTENING")

    # ── Config / setup ────────────────────────────────────────────────────────
    def _check_config(self) -> bool:
        from core.config import api_keys_configured
        return api_keys_configured()

    def _prompt_api_key_setup(self):
        if self.isHidden():
            self.show_window()
        self._show_setup()

    def _show_setup(self):
        key, ok = QInputDialog.getText(
            self, "API Key Setup",
            "Enter your Gemini API key to get started:",
            QLineEdit.EchoMode.Password,
        )
        if ok and key.strip():
            CONFIG_DIR.mkdir(parents=True, exist_ok=True)
            API_FILE.write_text(
                json.dumps(
                    {"gemini_api_keys": [key.strip()], "os_system": platform.system()},
                    indent=4,
                ),
                encoding="utf-8",
            )
            from core.config import invalidate_key_cache
            invalidate_key_cache()
            self._ready = True
            self.topbar.set_status("listening", "Ready")
            self._log_sig.emit("Ready! How can I help?", False)
        else:
            QMessageBox.warning(
                self, "Setup Required",
                "A Gemini API key is required to use Peka.\n"
                "Get one free at aistudio.google.com",
            )
            QTimer.singleShot(400, self._prompt_api_key_setup)

    # ── Public API ────────────────────────────────────────────────────────────
    def write_log(self, text: str):
        self._log_sig.emit(text, False)

    def set_state(self, state: str):
        self._state_sig.emit(state)

    @pyqtSlot(str)
    def _apply_state(self, state: str):
        state_map = {
            "THINKING":  ("thinking",  "Thinking…"),
            "SPEAKING":  ("thinking",  "Speaking…"),
            "LISTENING": ("listening", "Ready"),
            "MUTED":     ("muted",     "Muted"),
            "ERROR":     ("error",     "Error"),
        }
        dot_state, label = state_map.get(state, ("idle", state.capitalize()))
        self.topbar.set_status(dot_state, label)

        if state == "THINKING" and not self._is_loading:
            self.chat_view.show_typing()
            self._is_loading = True

    @property
    def muted(self) -> bool:
        return self._muted

    @property
    def current_file(self) -> Optional[str]:
        return self._current_file

    def closeEvent(self, event):
        if hasattr(self, "chat_view"):
            self.chat_view.cleanup()
        if hasattr(self, "welcome"):
            self.welcome.cleanup()
        if hasattr(self, "history_manager"):
            self.history_manager.save()
        super().closeEvent(event)

    @pyqtSlot()
    def show_window(self):
        self.show()
        self.raise_()
        self.activateWindow()
        if hasattr(self, "welcome") and self.stack.currentIndex() == 0:
            self.welcome.logo.start_animation()

    @pyqtSlot()
    def hide_window(self):
        if hasattr(self, "welcome"):
            self.welcome.logo.stop_animation()
        self.hide()


# ── Public PekaUI shim ────────────────────────────────────────────────────────
class _RootShim:
    def __init__(self, app: QApplication):
        self._app = app

    def mainloop(self):
        self._app.exec()

    def protocol(self, *_):
        pass


class PekaUI:
    def __init__(self, face_path: str, size=None, start_hidden: bool = False):
        self._app = QApplication.instance() or QApplication(sys.argv)
        self._app.setStyle("Fusion")
        self._win = PekaMainWindow(face_path)
        if not start_hidden:
            self._win.show()
        self.root = _RootShim(self._app)

    @property
    def muted(self) -> bool:
        return self._win.muted

    @muted.setter
    def muted(self, v: bool):
        if v != self._win.muted:
            self._win._toggle_mute()

    @property
    def current_file(self) -> Optional[str]:
        return self._win.current_file

    @property
    def on_text_command(self):
        return self._win.on_text_command

    @on_text_command.setter
    def on_text_command(self, cb):
        self._win.on_text_command = cb

    def set_state(self, state: str):
        self._win.set_state(state)

    def write_log(self, text: str):
        self._win.write_log(text)

    def wait_for_api_key(self):
        while not self._win._ready:
            time.sleep(0.1)

    def start_speaking(self):
        self.set_state("SPEAKING")

    def stop_speaking(self):
        if not self.muted:
            self.set_state("LISTENING")


# ── System tray helper ────────────────────────────────────────────────────────
def setup_tray(app: QApplication, main_window: PekaMainWindow):
    from PyQt6.QtWidgets import QSystemTrayIcon, QStyle
    from PyQt6.QtGui import QIcon

    icon = QIcon(str(BASE_DIR / "face.png"))
    if icon.isNull():
        icon = app.style().standardIcon(QStyle.StandardPixmap.SP_ComputerIcon)
    tray = QSystemTrayIcon(icon, parent=app)
    menu = QMenu()
    menu.setStyleSheet(f"""
        QMenu {{
            background:{T('BG_SURFACE')};border:1px solid {T('BORDER')};
            border-radius:10px;padding:5px;
        }}
        QMenu::item {{padding:8px 18px;border-radius:6px;color:{T('TXT_SECONDARY')};font-size:13px;}}
        QMenu::item:selected {{background:{T('BG_INPUT')};color:{T('TXT_PRIMARY')};}}
    """)

    show_act = menu.addAction("Show / Hide")
    show_act.triggered.connect(
        lambda: (
            main_window.show_window()
            if main_window.isHidden()
            else main_window.hide_window()
        )
    )
    menu.addSeparator()
    quit_act = menu.addAction("Quit Peka")
    quit_act.triggered.connect(app.quit)

    tray.setContextMenu(menu)
    tray.setToolTip("Peka — AI Assistant")
    tray.activated.connect(
        lambda reason: (
            main_window.show_window()
            if reason == QSystemTrayIcon.ActivationReason.DoubleClick
            else None
        )
    )
    tray.show()
    return tray


# ── Standalone entry point ────────────────────────────────────────────────────
if __name__ == "__main__":
    app = QApplication(sys.argv)
    app.setApplicationName("Peka")
    app.setApplicationDisplayName("Peka — AI Assistant")
    app.setStyle("Fusion")

    load_theme()
    palette = QPalette()
    bg = QColor(THEMES[_current_theme]["BG_PRIMARY"])
    palette.setColor(QPalette.ColorRole.Window,          bg)
    palette.setColor(QPalette.ColorRole.WindowText,      QColor(THEMES[_current_theme]["TXT_PRIMARY"]))
    palette.setColor(QPalette.ColorRole.Base,            QColor(THEMES[_current_theme]["BG_INPUT"]))
    palette.setColor(QPalette.ColorRole.AlternateBase,   QColor(THEMES[_current_theme]["BG_SIDEBAR"]))
    palette.setColor(QPalette.ColorRole.Text,            QColor(THEMES[_current_theme]["TXT_PRIMARY"]))
    palette.setColor(QPalette.ColorRole.Button,          QColor(THEMES[_current_theme]["BG_SIDEBAR"]))
    palette.setColor(QPalette.ColorRole.ButtonText,      QColor(THEMES[_current_theme]["TXT_PRIMARY"]))
    palette.setColor(QPalette.ColorRole.Highlight,       QColor(THEMES[_current_theme]["ACCENT"]))
    palette.setColor(QPalette.ColorRole.HighlightedText, QColor("#ffffff"))
    app.setPalette(palette)

    font = QFont("Segoe UI Variable", 13)
    font.setFallbackFamilies(["Segoe UI", "SF Pro Text", "Helvetica Neue"])
    font.setHintingPreference(QFont.HintingPreference.PreferFullHinting)
    app.setFont(font)

    window = PekaMainWindow("face.png")
    tray   = setup_tray(app, window)
    window.show()
    sys.exit(app.exec())