from PySide6.QtCore import Qt
from PySide6.QtWidgets import QFrame, QGraphicsBlurEffect


class FrostedGlassMixin:
    """Mixin to give widgets a frosted glass background."""

    def _init_glass(self, color: str = "rgba(255,255,255,180)", blur_radius: int = 20, border_radius: int = 15) -> None:
        """Create a semi-transparent blurred background."""
        # allow transparent window and create background frame
        self.setAttribute(Qt.WA_TranslucentBackground, True)
        bg = QFrame(self)
        bg.setObjectName("glass_bg")
        bg.setStyleSheet(
            f"#glass_bg {{background-color: {color}; border-radius: {border_radius}px;}}"
        )
        effect = QGraphicsBlurEffect(bg)
        effect.setBlurRadius(blur_radius)
        bg.setGraphicsEffect(effect)
        bg.setGeometry(self.rect())
        bg.lower()
        self._glass_bg = bg

    # keep background frame filling window on resize
    def resizeEvent(self, event):  # type: ignore[override]
        super().resizeEvent(event)
        if hasattr(self, "_glass_bg"):
            self._glass_bg.setGeometry(self.rect())
