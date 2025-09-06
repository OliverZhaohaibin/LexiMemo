from __future__ import annotations

from PySide6.QtCore import Qt, QPoint
from PySide6.QtWidgets import (
    QFrame,
    QHBoxLayout,
    QLabel,
    QStyle,
)

from UI.glass_effect import R2PushButton


class TitleBar(QFrame):
    """A simple, stylish title bar with minimize, maximize, and close buttons."""

    def __init__(self, parent, title: str | None = None) -> None:
        super().__init__(parent)
        self._parent = parent
        self.setFixedHeight(36)
        self.setObjectName("titleBar")
        self.setAttribute(Qt.WA_TranslucentBackground, True)
        self.setStyleSheet(
            "#titleBar{background: transparent;}"
            "#titleBar QPushButton{background: transparent; border: none;"
            "width: 36px; height: 24px; border-radius:4px;}"
            "#titleBar QPushButton:hover{background: rgba(255,255,255,0.3);}"
            "#titleBar QPushButton:pressed{background: rgba(255,255,255,0.5);}"
            "#titleBar QPushButton#closeButton:hover{background: #e81123;}"
        )

        layout = QHBoxLayout(self)
        layout.setContentsMargins(10, 0, 0, 0)
        layout.setSpacing(0)

        self._title_label = QLabel(title or parent.windowTitle())
        self._title_label.setStyleSheet("color: #333; font-size: 14px;")
        layout.addWidget(self._title_label)
        layout.addStretch(1)

        self._min_btn = R2PushButton(radius=4, parent=self)
        self._min_btn.setIcon(self.style().standardIcon(QStyle.SP_TitleBarMinButton))
        self._min_btn.setCursor(Qt.PointingHandCursor)
        self._min_btn.setFixedSize(36, 24)
        self._min_btn.setStyleSheet("border:none;")
        layout.addWidget(self._min_btn)
        self._min_btn.clicked.connect(parent.showMinimized)

        self._max_btn = R2PushButton(radius=4, parent=self)
        self._max_btn.setIcon(self.style().standardIcon(QStyle.SP_TitleBarMaxButton))
        self._max_btn.setCursor(Qt.PointingHandCursor)
        self._max_btn.setFixedSize(36, 24)
        self._max_btn.setStyleSheet("border:none;")
        layout.addWidget(self._max_btn)
        self._max_btn.clicked.connect(self._toggle_max)

        self._close_btn = R2PushButton(radius=4, parent=self)
        self._close_btn.setObjectName("closeButton")
        self._close_btn.setIcon(self.style().standardIcon(QStyle.SP_TitleBarCloseButton))
        self._close_btn.setCursor(Qt.PointingHandCursor)
        self._close_btn.setFixedSize(36, 24)
        self._close_btn.setStyleSheet("border:none;")
        layout.addWidget(self._close_btn)
        self._close_btn.clicked.connect(parent.close)

        self._drag_pos: QPoint | None = None

    # ---------------------------------------------------------
    def _toggle_max(self) -> None:
        if self._parent.isMaximized():
            self._parent.showNormal()
            self._max_btn.setIcon(self.style().standardIcon(QStyle.SP_TitleBarMaxButton))
            if hasattr(self._parent, "_set_shadow_enabled"):
                self._parent._set_shadow_enabled(True)
            if hasattr(self._parent, "_set_glass_radius"):
                self._parent._set_glass_radius(getattr(self._parent, "_glass_base_radius", 0))
        else:
            self._parent.showMaximized()
            self._max_btn.setIcon(self.style().standardIcon(QStyle.SP_TitleBarNormalButton))
            if hasattr(self._parent, "_set_shadow_enabled"):
                self._parent._set_shadow_enabled(False)
            if hasattr(self._parent, "_set_glass_radius"):
                # Remove rounded corners when maximized to avoid transparent edges
                self._parent._set_glass_radius(0)

    # ---------------------------------------------------------
    def mousePressEvent(self, event):  # type: ignore[override]
        if event.button() == Qt.LeftButton:
            child = self.childAt(event.position().toPoint())
            if not isinstance(child, R2PushButton):
                self._drag_pos = event.globalPosition().toPoint()
        super().mousePressEvent(event)

    def mouseMoveEvent(self, event):  # type: ignore[override]
        if self._drag_pos and event.buttons() & Qt.LeftButton:
            delta = event.globalPosition().toPoint() - self._drag_pos
            self._parent.move(self._parent.pos() + delta)
            self._drag_pos = event.globalPosition().toPoint()
        super().mouseMoveEvent(event)

    def mouseReleaseEvent(self, event):  # type: ignore[override]
        self._drag_pos = None
        super().mouseReleaseEvent(event)

    def mouseDoubleClickEvent(self, event):  # type: ignore[override]
        if event.button() == Qt.LeftButton:
            child = self.childAt(event.position().toPoint())
            if not isinstance(child, R2PushButton):
                self._toggle_max()
        super().mouseDoubleClickEvent(event)
