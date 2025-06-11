from __future__ import annotations
import os, sys
from pathlib import Path

from PySide6.QtCore import (
    Qt, QPoint, QSize, QTimer, Property, QPropertyAnimation, QEasingCurve, Signal
)
from PySide6.QtGui import (
    QColor, QPainter, QPixmap, QAction, QCursor, QFont
)
from PySide6.QtWidgets import (
    QPushButton, QMenu, QInputDialog
)

# -------- 常量 -------- #
_ICON_DIR          = "UI/word_book_button/icon"
_BASE_ICON_NAME    = "cover.webp"   # 白底透明
_DEFAULT_ICON_SIZE = 110                      # px

# ============================================================
class WordBookButtonView(QPushButton):
    """保持旧视觉/交互（含点击暗化 + 抖动）的新按钮 View。"""

    # ============ 向外暴露的信号（旧逻辑仍接收） ============ #
    renameRequested = Signal(str)
    deleteRequested = Signal()
    openRequested   = Signal()

    # ----------------- 构造 ----------------- #
    def __init__(self, title: str, color: str, parent=None) -> None:
        super().__init__(title, parent)

        # —— 对外公开字段 —— #
        self.color       = color

        bw = getattr(parent, "button_width", 120)
        bh = getattr(parent, "button_height", 150)
        self.setFixedSize(bw, bh)

        self.icon_size   = getattr(parent, "button_width", _DEFAULT_ICON_SIZE)
        self.icon_path   = self._ensure_icon_file(color)
        self.icon_pixmap = QPixmap(self.icon_path).scaled(
            self.icon_size, self.icon_size,
            Qt.KeepAspectRatio, Qt.SmoothTransformation
        )

        try:
            from font import normal_font
            f = QFont(normal_font)
            f.setBold(True)
            self.setFont(f)
        except Exception:
            pass

        # —— 基本外观 —— #
        self.setCursor(Qt.PointingHandCursor)
        self.setCheckable(False)
        self.setStyleSheet(
            "QPushButton {background: transparent; border: none; color:#333; font-weight:bold;}"
        )

        # —— 点击暗化状态 —— #
        self._dark_opacity = 0.0
        self._fade_anim: QPropertyAnimation | None = None
        self._long_press_timer = QTimer(self, singleShot=True, interval=110)
        self._long_press_timer.timeout.connect(self._on_long_press)

        # —— 抖动动画 —— #
        self._jitter_anim: QPropertyAnimation | None = None
        self._jitter_offset: float = 0.0  # -3 ~ 3 像素

    # ===================== 抖动 ===================== #
    def start_jitter(self) -> None:
        if self._jitter_anim:
            return
        self._jitter_anim = QPropertyAnimation(self, b"jitterOffset")
        self._jitter_anim.setStartValue(-3)
        self._jitter_anim.setEndValue(3)
        self._jitter_anim.setDuration(180)
        self._jitter_anim.setEasingCurve(QEasingCurve.InOutSine)
        self._jitter_anim.setLoopCount(-1)
        self._jitter_anim.start()

    def stop_jitter(self) -> None:
        if self._jitter_anim:
            self._jitter_anim.stop()
            self._jitter_anim.deleteLater()
            self._jitter_anim = None
        self.jitterOffset = 0.0

    # Property 供动画用
    def _get_jitter(self) -> float:         return self._jitter_offset
    def _set_jitter(self, v: float) -> None:
        self._jitter_offset = v
        self.update()
    jitterOffset = Property(float, _get_jitter, _set_jitter)

    # ===================== 鼠标交互 ===================== #
    def mousePressEvent(self, ev):  # noqa: N802
        if ev.button() == Qt.LeftButton:
            self._set_dark(1.0)           # 立即暗化
            self._long_press_timer.start()
        super().mousePressEvent(ev)

    def mouseReleaseEvent(self, ev):  # noqa: N802
        if ev.button() == Qt.LeftButton:
            self._long_press_timer.stop()
            self._fade_dark()
        super().mouseReleaseEvent(ev)

    def mouseDoubleClickEvent(self, ev):  # noqa: N802
        self.openRequested.emit()
        super().mouseDoubleClickEvent(ev)

    # 长按定时器回调
    def _on_long_press(self):
        if self.isDown():                 # 按住不放 → 开始淡出
            self._fade_dark()

    # ===================== 右键菜单 ===================== #
    def contextMenuEvent(self, ev):  # noqa: N802
        m = QMenu(self)
        a1 = QAction("重命名", self)
        a2 = QAction("删除", self)
        a1.triggered.connect(self._prompt_rename)
        a2.triggered.connect(self.deleteRequested)
        m.addAction(a1); m.addAction(a2)
        m.exec(ev.globalPos())

    def _prompt_rename(self):
        new_name, ok = QInputDialog.getText(self, "重命名单词本", "新名称：")
        if ok and new_name.strip():
            self.renameRequested.emit(new_name.strip())

    # ===================== 暗化动画 ===================== #
    def _set_dark(self, value: float):
        self._dark_opacity = max(0.0, min(1.0, value))
        self.update()

    def _fade_dark(self):
        if self._fade_anim and self._fade_anim.state() == QPropertyAnimation.Running:
            self._fade_anim.stop()
        self._fade_anim = QPropertyAnimation(self, b"darkOpacity", self)
        self._fade_anim.setStartValue(self._dark_opacity)
        self._fade_anim.setEndValue(0.0)
        self._fade_anim.setDuration(150)
        self._fade_anim.start()

    def _get_dark(self) -> float:         return self._dark_opacity
    def _set_dark_prop(self, v: float):   self._set_dark(v)
    darkOpacity = Property(float, _get_dark, _set_dark_prop)

    # ===================== 绘制 ===================== #
    def paintEvent(self, _):  # noqa: N802
        painter = QPainter(self)
        painter.setRenderHint(QPainter.Antialiasing)

        # 1. 抖动平移
        painter.translate(self._jitter_offset, 0)

        # 2. 悬浮高亮 / 按下背景
        if self.underMouse() or self.isDown():
            bg = QColor(self.color).lighter(130 if self.isDown() else 180)
            painter.setPen(Qt.NoPen)
            painter.setBrush(bg)
            painter.drawRoundedRect(self.rect(), 14, 14)

        # 3. 图标
        ix = (self.width() - self.icon_pixmap.width()) // 2
        painter.drawPixmap(ix, 0, self.icon_pixmap)

        # 4. 暗化遮罩
        if self._dark_opacity > 0.01:
            c = QColor(0, 0, 0, int(150 * self._dark_opacity))
            painter.fillRect(self.rect(), c)

        # 5. 文字
        text_y = self.icon_size + 6
        rect   = self.rect().adjusted(4, text_y, -4, -4)
        painter.setPen(Qt.black)
        fm = painter.fontMetrics()
        txt = fm.elidedText(self.text(), Qt.ElideRight, rect.width())
        painter.drawText(rect, Qt.AlignHCenter | Qt.AlignTop, txt)

    # ===================== 图标生成 ===================== #
    def _ensure_icon_file(self, color: str) -> str:
        """若不存在已着色图标则生成并返回路径。"""
        base = Path(os.path.abspath(sys.argv[0])).parent
        icon_dir = base / _ICON_DIR
        icon_dir.mkdir(exist_ok=True)

        fn_color = color.lstrip("#")
        out_path = icon_dir / f"colored_icon_{fn_color}.png"
        if out_path.exists():
            return str(out_path)

        src = icon_dir / _BASE_ICON_NAME
        if not src.exists():
            pix = QPixmap(self.icon_size, self.icon_size); pix.fill(QColor(color))
            pix.save(out_path)
            return str(out_path)

        try:
            from PIL import Image
            im = Image.open(src).convert("RGBA")
            r, g, b = QColor(color).red(), QColor(color).green(), QColor(color).blue()
            datas = [(r, g, b, a) if a > 0 else (255, 255, 255, 0) for (*_, a) in im.getdata()]
            im.putdata(datas)
            im.save(out_path)
        except Exception:
            pix = QPixmap(self.icon_size, self.icon_size); pix.fill(QColor(color))
            pix.save(out_path)
        return str(out_path)
