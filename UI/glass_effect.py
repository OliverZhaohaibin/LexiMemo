from __future__ import annotations

from PySide6.QtCore import Qt, QRectF, QPropertyAnimation, QSize
from PySide6.QtGui import (
    QColor,
    QPainter,
    QPainterPath,
    QBitmap,
    QImage,
    QPixmap,
)
from PySide6.QtWidgets import (
    QFrame,
    QPushButton,
    QGraphicsBlurEffect,
    QGraphicsDropShadowEffect,
)

from UI.styles import BACKGROUND_COLOR


def with_alpha(color: str, alpha: int) -> QColor:
    """Return ``color`` with the given alpha applied."""
    c = QColor(color)
    c.setAlpha(alpha)
    return c


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


def _feathered_mask(size: QSize, radius: int, scale: int = 4) -> QBitmap:
    """Return an anti-aliased mask for an R2-rounded rect using oversampling."""
    w, h = size.width() * scale, size.height() * scale
    image = QImage(w, h, QImage.Format_ARGB32)
    image.fill(Qt.transparent)
    painter = QPainter(image)
    painter.setRenderHint(QPainter.Antialiasing)
    hq_hint = getattr(QPainter, "HighQualityAntialiasing", None)
    if hq_hint is not None:
        painter.setRenderHint(hq_hint)
    path = _r2_path(QRectF(0, 0, w, h), radius * scale)
    painter.fillPath(path, Qt.white)
    painter.end()
    pix = QPixmap.fromImage(image)
    pix = pix.scaled(size, Qt.IgnoreAspectRatio, Qt.SmoothTransformation)
    return pix.mask()


def apply_r2_mask(widget, radius: int) -> None:
    """Clip ``widget`` to an R2-continuous rounded rectangle mask."""
    widget.setMask(_feathered_mask(widget.size(), radius))


class _R2Frame(QFrame):
    """Frame that paints itself as an R2-continuous rounded rectangle."""

    def __init__(self, color: QColor | str, radius: int, parent: QFrame | None = None) -> None:
        super().__init__(parent)
        self._color = QColor(color)
        self._radius = radius
        self.setAttribute(Qt.WA_TranslucentBackground, True)

    def setColor(self, color: QColor | str) -> None:
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


class R2PushButton(QPushButton):
    """QPushButton with an R2-continuous mask for smoother corners."""

    def __init__(self, *args, radius: int = 12, **kwargs) -> None:
        super().__init__(*args, **kwargs)
        self._r2_radius = radius
        self.setAttribute(Qt.WA_TranslucentBackground, True)

    def setRadius(self, radius: int) -> None:
        self._r2_radius = radius
        apply_r2_mask(self, self._r2_radius)

    def resizeEvent(self, event):  # type: ignore[override]
        super().resizeEvent(event)
        apply_r2_mask(self, self._r2_radius)


class FrostedGlassMixin:
    """Mixin providing a modern glass-like card background."""

    def _init_glass(
        self,
        color: QColor | str = BACKGROUND_COLOR,
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
        # allow mouse interactions to reach widgets above the frosted layer
        container.setAttribute(Qt.WA_TransparentForMouseEvents, True)

        shadow = QGraphicsDropShadowEffect(container)
        shadow.setBlurRadius(40)
        shadow.setOffset(0, 0)
        shadow.setColor(shadow_color or QColor(0, 0, 0, 100))
        container.setGraphicsEffect(shadow)
        container.lower()

        bg = _R2Frame(color, border_radius, container)
        bg.setAttribute(Qt.WA_TransparentForMouseEvents, True)
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

    def _set_glass_color(self, color: QColor | str) -> None:
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
        self.setMask(_feathered_mask(self.size(), self._glass_radius))


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

