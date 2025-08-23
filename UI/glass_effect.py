from PySide6.QtCore import Qt
from PySide6.QtGui import QColor
from PySide6.QtWidgets import QFrame, QGraphicsBlurEffect, QGraphicsDropShadowEffect


def with_alpha(hex_color: str, alpha: int) -> str:
    """Convert ``#RRGGBB`` color to ``rgba(r,g,b,alpha)`` string."""
    q = QColor(hex_color)
    return f"rgba({q.red()},{q.green()},{q.blue()},{alpha})"


class FrostedGlassMixin:
    """Mixin providing a modern frosted glass card background."""

    def _init_glass(
        self,
        color: str = "rgba(255,255,255,140)",
        blur_radius: int = 30,
        border_radius: int = 20,
        shadow_color: QColor | None = None,
    ) -> None:
        """Create a semi-transparent blurred background with soft shadow."""

        self.setAttribute(Qt.WA_TranslucentBackground, True)

        # container with drop shadow
        container = QFrame(self)
        container.setObjectName("glass_container")
        container.setGeometry(self.rect())
        shadow = QGraphicsDropShadowEffect(container)
        shadow.setBlurRadius(40)
        shadow.setOffset(0, 0)
        shadow.setColor(shadow_color or QColor(0, 0, 0, 100))
        container.setGraphicsEffect(shadow)
        container.lower()

        # actual frosted background
        bg = QFrame(container)
        bg.setObjectName("glass_bg")
        bg.setStyleSheet(
            f"#glass_bg {{background-color: {color}; border-radius: {border_radius}px;"
            "border:1px solid rgba(255,255,255,60);}}"
        )
        effect = QGraphicsBlurEffect(bg)
        effect.setBlurRadius(blur_radius)
        bg.setGraphicsEffect(effect)
        bg.setGeometry(container.rect())

        self._glass_container = container
        self._glass_bg = bg
        self._glass_radius = border_radius

    # keep background frame filling window on resize
    def resizeEvent(self, event):  # type: ignore[override]
        super().resizeEvent(event)
        if hasattr(self, "_glass_container"):
            self._glass_container.setGeometry(self.rect())
            self._glass_bg.setGeometry(self._glass_container.rect())

    # allow subclasses to update background tint
    def _set_glass_color(self, color: str) -> None:
        if hasattr(self, "_glass_bg"):
            self._glass_bg.setStyleSheet(
                f"#glass_bg {{background-color: {color}; border-radius: {self._glass_radius}px;"
                "border:1px solid rgba(255,255,255,60);}}"
            )
