from __future__ import annotations

import math

from PySide6.QtCore import Qt, QRectF, QPropertyAnimation
from PySide6.QtGui import QColor, QPainter, QPainterPath, QRegion
from PySide6.QtWidgets import (
    QFrame,
    QGraphicsBlurEffect,
    QGraphicsDropShadowEffect,
)

from UI.styles import BACKGROUND_COLOR


def _add_r2_corner(
    path: QPainterPath,
    cx: float,
    cy: float,
    radius: float,
    start_angle: float,
    steps: int = 16,
    power: int = 4,
) -> None:
    """Append a quarter superellipse (R2 continuous) corner to ``path``.

    ``start_angle`` is given in degrees for orientation: 0° = top-right,
    90° = bottom-right, etc.
    """

    angle = math.radians(start_angle)
    for i in range(1, steps + 1):
        t = (i / steps) * (math.pi / 2)
        x = radius * (math.sin(t) ** (2 / power))
        y = -radius * (math.cos(t) ** (2 / power))
        xr = x * math.cos(angle) - y * math.sin(angle)
        yr = x * math.sin(angle) + y * math.cos(angle)
        path.lineTo(cx + xr, cy + yr)


def _r2_path(rect: QRectF, radius: float) -> QPainterPath:
    """Create a rounded-rectangle path with R2 continuous corners."""

    w, h = rect.width(), rect.height()
    r = min(radius, w / 2, h / 2)
    p = QPainterPath()
    p.moveTo(r, 0)
    p.lineTo(w - r, 0)
    _add_r2_corner(p, w - r, r, r, 0)
    p.lineTo(w, h - r)
    _add_r2_corner(p, w - r, h - r, r, 90)
    p.lineTo(r, h)
    _add_r2_corner(p, r, h - r, r, 180)
    p.lineTo(0, r)
    _add_r2_corner(p, r, r, r, 270)
    p.closeSubpath()
    return p


class _R2Frame(QFrame):
    """Frame that paints itself as an R2-continuous rounded rectangle."""

    def __init__(self, color: str, radius: int, parent: QFrame | None = None) -> None:
        super().__init__(parent)
        self._color = QColor(color)
        self._radius = radius
        self.setAttribute(Qt.WA_TranslucentBackground, True)

    def setColor(self, color: str) -> None:
        self._color = QColor(color)
        self.update()

    def setRadius(self, radius: int) -> None:
        self._radius = radius
        self.update()

    def paintEvent(self, event):  # type: ignore[override]
        painter = QPainter(self)
        painter.setRenderHint(QPainter.Antialiasing)
        path = _r2_path(QRectF(self.rect()), self._radius)
        painter.fillPath(path, self._color)
        painter.setPen(Qt.NoPen)
        painter.drawPath(path)


class FrostedGlassMixin:
    """Mixin providing a modern glass-like card background."""

    def _init_glass(
        self,
        color: str = BACKGROUND_COLOR,
        blur_radius: int = 30,
        border_radius: int = 20,
        shadow_color: QColor | None = None,
    ) -> None:
        """Create a blurred background with soft shadow."""

        self.setAttribute(Qt.WA_TranslucentBackground, True)

        container = QFrame(self)
        container.setObjectName("glass_container")
        container.setGeometry(self.rect())
        container.setAttribute(Qt.WA_TranslucentBackground, True)

        shadow = QGraphicsDropShadowEffect(container)
        shadow.setBlurRadius(40)
        shadow.setOffset(0, 0)
        shadow.setColor(shadow_color or QColor(0, 0, 0, 100))
        container.setGraphicsEffect(shadow)
        container.lower()

        bg = _R2Frame(color, border_radius, container)
        effect = QGraphicsBlurEffect(bg)
        effect.setBlurRadius(blur_radius)
        bg.setGraphicsEffect(effect)
        bg.setGeometry(container.rect())

        self._glass_container = container
        self._glass_bg = bg
        self._glass_shadow = shadow
        self._glass_base_radius = border_radius
        self._glass_radius = border_radius
        self._update_mask()

    def resizeEvent(self, event):  # type: ignore[override]
        super().resizeEvent(event)
        if hasattr(self, "_glass_container"):
            self._glass_container.setGeometry(self.rect())
            self._glass_bg.setGeometry(self._glass_container.rect())
            self._update_mask()

    def _set_glass_color(self, color: str) -> None:
        if hasattr(self, "_glass_bg"):
            self._glass_bg.setColor(color)

    def _set_glass_radius(self, radius: int) -> None:
        if hasattr(self, "_glass_bg"):
            self._glass_bg.setRadius(radius)
            self._glass_radius = radius
            self._update_mask()

    def _set_shadow_enabled(self, enabled: bool) -> None:
        if hasattr(self, "_glass_shadow"):
            self._glass_shadow.setEnabled(enabled)

    def _update_mask(self) -> None:
        if getattr(self, "_glass_radius", 0) <= 0:
            self.clearMask()
            return
        path = _r2_path(QRectF(self.rect()), self._glass_radius)
        region = QRegion(path.toFillPolygon().toPolygon())
        self.setMask(region)


class FadeInWindowMixin:
    """Mixin that fades the window in on show for smoother popups."""

    def showEvent(self, event):  # type: ignore[override]
        self.setWindowOpacity(0.0)
        anim = QPropertyAnimation(self, b"windowOpacity", self)
        anim.setDuration(200)
        anim.setStartValue(0.0)
        anim.setEndValue(1.0)
        anim.start(QPropertyAnimation.DeleteWhenStopped)
        super().showEvent(event)

