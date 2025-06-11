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
    QPushButton, QMenu, QInputDialog, QLineEdit
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

        # —— 抖动 / 拖动状态 —— #
        self._jitter_anim: QPropertyAnimation | None = None
        self._rotation: float = 0.0
        self._edit_mode = False
        self._drag_offset: QPoint | None = None
        self._dragging = False

        # —— 内联重命名 & 删除按钮 —— #
        self.name_edit = QLineEdit(self)
        self.name_edit.hide()
        self.name_edit.returnPressed.connect(self._finish_name_edit)
        self.name_edit.editingFinished.connect(self._finish_name_edit)

        self.delete_btn = QPushButton("✕", self)
        self.delete_btn.setFixedSize(22, 22)
        self.delete_btn.hide()
        self.delete_btn.clicked.connect(self.deleteRequested)
        self._update_delete_btn()

    # ===================== 抖动 ===================== #
    def start_jitter(self) -> None:
        if self._jitter_anim:
            return
        self._edit_mode = True
        self._jitter_anim = QPropertyAnimation(self, b"rotation")
        self._jitter_anim.setDuration(200)
        self._jitter_anim.setLoopCount(-1)
        self._jitter_anim.setKeyValueAt(0, 0)
        self._jitter_anim.setKeyValueAt(0.25, -2.0)
        self._jitter_anim.setKeyValueAt(0.5, 0)
        self._jitter_anim.setKeyValueAt(0.75, 2.0)
        self._jitter_anim.setKeyValueAt(1, 0)
        self._jitter_anim.start()
        self._update_delete_btn()

    def stop_jitter(self) -> None:
        if self._jitter_anim:
            self._jitter_anim.stop()
            self._jitter_anim.deleteLater()
            self._jitter_anim = None
        self.rotation = 0.0
        self._edit_mode = False
        self._update_delete_btn()

    # Property 供动画用
    def _get_rotation(self) -> float:
        return self._rotation

    def _set_rotation(self, v: float) -> None:
        self._rotation = v
        self.update()

    rotation = Property(float, _get_rotation, _set_rotation)

    # ===================== 鼠标交互 ===================== #
    def mousePressEvent(self, ev):  # noqa: N802
        if ev.button() == Qt.LeftButton:
            self._set_dark(1.0)           # 立即暗化
            self._long_press_timer.start()
            if self._edit_mode:
                self._drag_offset = ev.pos()
                self._dragging = False
                self.raise_()
        super().mousePressEvent(ev)

    def mouseReleaseEvent(self, ev):  # noqa: N802
        if ev.button() == Qt.LeftButton:
            self._long_press_timer.stop()
            self._fade_dark()
            if self._edit_mode and self._dragging:
                self._dragging = False
                if hasattr(self.parent(), "update_button_positions"):
                    try:
                        self.parent().update_button_positions()
                    except Exception:
                        pass
            elif not self._edit_mode and self.rect().contains(ev.pos()):
                self.openRequested.emit()
        super().mouseReleaseEvent(ev)

    def mouseMoveEvent(self, ev):  # noqa: N802
        if self._edit_mode and ev.buttons() & Qt.LeftButton and self._drag_offset is not None:
            if not self._dragging and (ev.pos() - self._drag_offset).manhattanLength() > 3:
                self._dragging = True
            if self._dragging:
                new_pos = self.mapToParent(ev.pos() - self._drag_offset)
                self.move(new_pos)
                return
        super().mouseMoveEvent(ev)

    def resizeEvent(self, ev):  # noqa: N802
        super().resizeEvent(ev)
        self._update_delete_btn()

    def mouseDoubleClickEvent(self, ev):  # noqa: N802
        if self._edit_mode:
            self.start_name_edit()
        else:
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

    # ===================== 内联重命名 ===================== #
    def start_name_edit(self) -> None:
        if self.name_edit.isVisible():
            return
        self.name_edit.setText(self.text())
        y = self.icon_size + 6
        self.name_edit.setGeometry(0, y, self.width(), self.height() - y)
        self.name_edit.show()
        self.name_edit.setFocus()

    def _finish_name_edit(self) -> None:
        if not self.name_edit.isVisible():
            return
        new_name = self.name_edit.text().strip()
        self.name_edit.hide()
        if new_name and new_name != self.text():
            self.renameRequested.emit(new_name)

    def _update_delete_btn(self) -> None:
        self.delete_btn.move(self.width() - self.delete_btn.width(), 0)
        self.delete_btn.setVisible(self._edit_mode)

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

        painter.save()
        if self._rotation:
            painter.translate(self.width() / 2, self.height() / 2)
            painter.rotate(self._rotation)
            painter.translate(-self.width() / 2, -self.height() / 2)

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
        painter.restore()

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
