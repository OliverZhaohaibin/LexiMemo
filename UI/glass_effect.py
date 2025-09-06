from __future__ import annotations

from PySide6.QtCore import Qt, QRectF, QPropertyAnimation
from PySide6.QtGui import QColor, QPainter, QPainterPath, QImage, QBitmap
from PySide6.QtWidgets import (
    QPushButton,
    QStyle,
    QStyleOptionButton,
    QStylePainter,
)

from UI.styles import BACKGROUND_COLOR


def _r2_path(rect: QRectF, radius: float) -> QPainterPath:
    """Return a rounded rectangle with R2-continuous (squircle) corners.

    The shape uses cubic Bézier curves with the Apple squircle constant
    (≈0.551915) to avoid the jagged artefacts of polyline sampling.
    """

    r = min(radius, rect.width() / 2, rect.height() / 2)
    x, y, w, h = rect.x(), rect.y(), rect.width(), rect.height()
    c = r * 0.551915024494  # control point coefficient

    path = QPainterPath()
    path.moveTo(x + w - r, y)

    path.cubicTo(x + w - r + c, y, x + w, y + r - c, x + w, y + r)
    path.lineTo(x + w, y + h - r)

    path.cubicTo(x + w, y + h - r + c, x + w - r + c, y + h, x + w - r, y + h)
    path.lineTo(x + r, y + h)

    path.cubicTo(x + r - c, y + h, x, y + h - r + c, x, y + h - r)
    path.lineTo(x, y + r)

    path.cubicTo(x, y + r - c, x + r - c, y, x + r, y)
    path.closeSubpath()
    return path


def _r2_mask(size, radius: int, scale: int = 4) -> QBitmap:
    """Return a high-quality bitmap mask for an R2-rounded rectangle."""

    img = QImage(size.width() * scale, size.height() * scale, QImage.Format_ARGB32)
    img.fill(Qt.transparent)
    painter = QPainter(img)
    painter.setRenderHint(QPainter.Antialiasing)
    hq_hint = getattr(QPainter, "HighQualityAntialiasing", None)
    if hq_hint is not None:
        painter.setRenderHint(hq_hint)
    path = _r2_path(QRectF(0, 0, img.width(), img.height()), radius * scale)
    painter.fillPath(path, Qt.white)
    painter.end()
    img = img.scaled(size, Qt.IgnoreAspectRatio, Qt.SmoothTransformation)
    alpha = img.convertToFormat(QImage.Format_Alpha8)
    return QBitmap.fromImage(alpha)


class R2PushButton(QPushButton):
    """QPushButton that paints itself with R2-continuous corners."""

    def __init__(self, *args, radius: int = 12, **kwargs) -> None:
        super().__init__(*args, **kwargs)
        self._r2_radius = radius
        self.setAttribute(Qt.WA_TranslucentBackground, True)

    def setRadius(self, radius: int) -> None:
        self._r2_radius = radius
        self.update()

    def paintEvent(self, event):  # type: ignore[override]
        painter = QStylePainter(self)
        option = QStyleOptionButton()
        option.initFrom(self)
        option.text = self.text()
        option.icon = self.icon()
        option.iconSize = self.iconSize()
        option.rect = self.rect()
        painter.setRenderHint(QPainter.Antialiasing)
        hq_hint = getattr(QPainter, "HighQualityAntialiasing", None)
        if hq_hint is not None:
            painter.setRenderHint(hq_hint)
        path = _r2_path(QRectF(self.rect()), self._r2_radius)
        painter.setClipPath(path)
        painter.drawControl(QStyle.CE_PushButton, option)
        

class R2WindowMixin:
    """Mixin that clips a top-level widget to R2-continuous corners."""

    def _init_r2(
        self,
        color: QColor | str = BACKGROUND_COLOR,
        border_radius: int = 20,
    ) -> None:
        self._r2_base_radius = border_radius
        self._r2_radius = border_radius
        self.setAttribute(Qt.WA_TranslucentBackground, True)
        self.setStyleSheet(f"background: {QColor(color).name()};")
        self._update_mask()

    def _update_mask(self) -> None:
        self.setMask(_r2_mask(self.size(), self._r2_radius))

    def resizeEvent(self, event):  # type: ignore[override]
        super().resizeEvent(event)
        if hasattr(self, "_r2_radius"):
            self._update_mask()

    def _set_r2_radius(self, radius: int) -> None:
        self._r2_radius = radius
        self._update_mask()


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

