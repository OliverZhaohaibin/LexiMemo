from __future__ import annotations

from PySide6.QtCore import Qt, QPoint
from PySide6.QtWidgets import QFrame, QHBoxLayout, QLabel, QPushButton


class TitleBar(QFrame):
    """A simple, stylish title bar with minimize, maximize, and close buttons."""

    def __init__(self, parent, title: str | None = None) -> None:
        super().__init__(parent)
        self._parent = parent
        self.setFixedHeight(36)
        self.setObjectName("titleBar")
        self.setStyleSheet(
            "#titleBar{background-color: rgba(255,255,255,180);"
            "border-bottom: 1px solid rgba(255,255,255,40);}" 
            "#titleBar QPushButton{background: transparent; border: none;"
            "width: 32px; height: 24px; color: #333;}" 
            "#titleBar QPushButton:hover{background: rgba(255,255,255,80);}" 
            "#titleBar QPushButton#closeButton:hover{background: #e81123; color: white;}"
        )

        layout = QHBoxLayout(self)
        layout.setContentsMargins(10, 0, 0, 0)
        layout.setSpacing(0)

        self._title_label = QLabel(title or parent.windowTitle())
        self._title_label.setStyleSheet("color: #333; font-size: 14px;")
        layout.addWidget(self._title_label)
        layout.addStretch(1)

        self._min_btn = QPushButton("-", self)
        self._min_btn.clicked.connect(parent.showMinimized)
        layout.addWidget(self._min_btn)

        self._max_btn = QPushButton("◻", self)
        self._max_btn.clicked.connect(self._toggle_max)
        layout.addWidget(self._max_btn)

        self._close_btn = QPushButton("✕", self)
        self._close_btn.setObjectName("closeButton")
        self._close_btn.clicked.connect(parent.close)
        layout.addWidget(self._close_btn)

        self._drag_pos: QPoint | None = None

    # ---------------------------------------------------------
    def _toggle_max(self) -> None:
        if self._parent.isMaximized():
            self._parent.showNormal()
        else:
            self._parent.showMaximized()

    # ---------------------------------------------------------
    def mousePressEvent(self, event):  # type: ignore[override]
        if event.button() == Qt.LeftButton:
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
            self._toggle_max()
        super().mouseDoubleClickEvent(event)
