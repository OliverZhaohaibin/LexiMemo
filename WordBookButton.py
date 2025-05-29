from PySide6.QtWidgets import QPushButton, QLineEdit, QMessageBox
from PySide6.QtGui import QIcon, QColor, QPainter, QPixmap, QFont
from PySide6.QtWidgets import QStyleOptionButton, QStyle
from PySide6.QtCore import Qt, QRect, QPoint, QPropertyAnimation, QTimer, QEasingCurve, Property
from PIL import Image
import os
import sys
from font import normal_font
from Folder_UI.button import DraggableButton
from Folder_UI.layout import calculate_folder_area


class WordBookButton(DraggableButton):
    """自定义单词本按钮，支持拖拽、文件夹展开/折叠、子按钮拖出等交互。"""

    def __init__(self, title: str, color: str, parent=None, app=None):
        super().__init__(title, parent if parent is not None else parent, app)

        # —— 基本属性 —— #
        self.color          = color
        self.is_folder      = False
        self.is_expanded    = False
        self.is_sub_button  = False
        self.parent_folder  = None
        self.sub_buttons    = []
        self.is_dragging    = False
        self.drag_start_position       = QPoint()
        self.drag_out_threshold_exceeded = False
        self.rename_source  = "edit"
        self._fade_opacity: float = 1.0  # 深色背景当前透明度
        self._fade_anim: QPropertyAnimation | None = None
        self._suppress_dark: bool = False  # 渐隐结束 → True 彻底不再绘制
        # —— 字体 / 尺寸 —— #
        cover_font = QFont(normal_font)
        cover_font.setBold(True)
        self.setFont(cover_font)
        self.icon_size  = 120
        self.setFixedSize(120, 150)

        # —— 图标 —— #
        icon_path            = self.create_colored_icon(color)
        self.icon_path       = icon_path
        self.icon_pixmap     = QPixmap(icon_path).scaled(self.icon_size, self.icon_size)

        # —— hover / pressed 样式（颜色深、浅） —— #
        hover_color, pressed_color = color, color
        self.setStyleSheet(f"""
            QPushButton {{
                background-color: transparent;
                border: none;
                text-align: center;
            }}
            QPushButton::hover {{
                background-color: {WordBookButton.lighten_color(hover_color)};
                border-radius: 15px;
            }}
            QPushButton::pressed {{
                background-color: {pressed_color};
                border-radius: 15px;
            }}
        """)

        # —— 内联名称编辑控件 —— #
        self.name_edit = QLineEdit(self)
        self.name_edit.hide()
        self.name_edit.setAlignment(Qt.AlignCenter)
        self.name_edit.setStyleSheet("""
            QLineEdit {
                border: 1px solid #888;
                border-radius: 4px;
                background-color: rgba(255, 255, 255, 0.9);
            }
        """)
        self.name_edit.returnPressed.connect(self.finish_name_edit)
        self.name_edit.editingFinished.connect(self.finish_name_edit)

        # —— 删除按钮（右上角 ✕） —— #
        self.delete_button = QPushButton("✕", self)
        self.delete_button.setFixedSize(22, 22)
        self.delete_button.move(self.width() - self.delete_button.width(), 0)
        self.delete_button.setStyleSheet("""
               QPushButton {
                   background-color: #FF4D4D;
                   color: #FFFFFF;
                   border: none;
                   border-radius: 11px;
                   font-weight: bold;
               }
               QPushButton:hover { background-color: #FF8080; }
           """)
        self.delete_button.hide()
        self.delete_button.clicked.connect(self.on_delete_clicked)
        self.delete_button.setCursor(Qt.ArrowCursor)   # ✕ 按钮始终保持默认箭头

        # —— 启用鼠标跟踪，以便不按键时也能接收 mouseMoveEvent —— #
        self.setMouseTracking(True)

        # ----------  新增：按压动画/计时  ---------- #
        self._orig_geometry: QRect | None = None  # 原始几何
        self._shrink_anim: QPropertyAnimation | None = None
        self._restore_anim: QPropertyAnimation | None = None
        self._long_press_timer: QTimer | None = None
        self._suppress_dark: bool = False  # 0.5 s后取消变深
    # ------------------------------------------------------------
    # 光标更新辅助
    # ------------------------------------------------------------
    def _update_cursor(self, pos: QPoint):
        """
        根据鼠标位置更新光标（仅编辑模式生效）
          • 名称区域       → IBeam（文本）
          • 删除按钮区域   → Arrow（默认）
          • 其余按钮区域   → PointingHand（手掌）
        """
        if self.app and self.app.edit_mode:
            # 1. 删除按钮区域优先
            if self.delete_button.isVisible() and self.delete_button.geometry().contains(pos):
                self.setCursor(Qt.ArrowCursor)
                return

            # 2. 名称文字所在矩形
            name_rect = QRect(
                0,
                self.icon_size + 5,
                self.width(),
                self.height() - self.icon_size - 5
            )
            if name_rect.contains(pos):
                self.setCursor(Qt.IBeamCursor)
            else:
                self.setCursor(Qt.PointingHandCursor)
        else:
            # 非编辑模式：保持默认
            self.setCursor(Qt.ArrowCursor)
    # ------------------------- 静态辅助方法 ------------------------- #
    @staticmethod
    def lighten_color(color: str, factor: float = 0.6) -> str:
        rgb = QColor(color).getRgb()[:3]
        lightened = [int(min(255, c + (255 - c) * factor)) for c in rgb]
        return QColor(*lightened).name()

    def create_colored_icon(self, color: str) -> str:
        base_dir = os.path.dirname(os.path.abspath(sys.argv[0]))
        icon_dir = os.path.join(base_dir, "icon")
        os.makedirs(icon_dir, exist_ok=True)
        icon_path = os.path.join(icon_dir, f"colored_icon_{color[1:]}.png")
        if os.path.exists(icon_path):
            return icon_path
        base_image_path = os.path.join(base_dir, "icon", "cover.webp")
        base_image = Image.open(base_image_path).convert("RGBA")
        datas = base_image.getdata()
        new_data = []
        target = Image.new("RGBA", (1, 1), color).getdata()[0]
        for item in datas:
            if not (item[0] > 200 and item[1] > 200 and item[2] > 200):
                new_data.append(target)
            else:
                new_data.append((255, 255, 255, 0))
        base_image.putdata(new_data)
        base_image.save(icon_path)
        return icon_path

    def update_folder_icon(self):
        """
        重新生成九宫格文件夹图标并刷新显示。
        若子按钮数量发生变化（新增 / 移除 / 重排）时，务必调用本方法。
        """
        if not self.is_folder or not self.sub_buttons:
            return

        # 收集最多 9 张子按钮图标
        sub_icon_paths = []
        for sub in self.sub_buttons[:9]:
            # 普通按钮 & 另一个文件夹按钮都会在 __init__ 中写入 icon_path
            if hasattr(sub, "icon_path") and sub.icon_path:
                sub_icon_paths.append(sub.icon_path)

        if not sub_icon_paths:  # 没有可用子图标则跳过
            return

        from Folder_UI.utils import create_folder_icon
        icon_path = create_folder_icon(
            sub_icon_paths=sub_icon_paths,
            folder_name=self.text()
        )

        self.icon_path = icon_path
        self.icon_pixmap = QPixmap(icon_path).scaled(self.icon_size, self.icon_size)
        self.update()  # 触发重绘

    # --------------------------- 绘制 --------------------------- #
    def paintEvent(self, event):
        """先绘制浅色 hover，再叠加可渐隐的深色层。"""
        painter = QPainter(self)
        painter.setRenderHint(QPainter.Antialiasing)

        # ---------- ① 浅色 hover 背景 ----------
        base_color = None
        if self.underMouse():  # 包括按住时
            base_color = QColor(WordBookButton.lighten_color(self.color))

        if base_color:
            painter.setPen(Qt.NoPen)
            painter.setBrush(base_color)
            painter.drawRoundedRect(self.rect(), 15, 15)

        # ---------- ② 深色按压层（会淡出） ----------
        if (
                self.isDown()
                and not self._suppress_dark
                and self._fade_opacity > 0.0
        ):
            overlay = QColor(self.color)
            overlay.setAlphaF(self._fade_opacity)  # α 随动画变化 1 → 0
            painter.setPen(Qt.NoPen)
            painter.setBrush(overlay)
            painter.drawRoundedRect(self.rect(), 15, 15)

        # ---------- ③ 抖动旋转支持 ----------
        painter.save()
        if getattr(self, "_rotation", 0):
            painter.translate(self.width() / 2, self.height() / 2)
            painter.rotate(self._rotation)
            painter.translate(-self.width() / 2, -self.height() / 2)

        # ---------- ④ 图标 & 标题 ----------
        if hasattr(self, "icon_pixmap"):
            icon_x = (self.width() - self.icon_pixmap.width()) // 2
            painter.drawPixmap(icon_x, 0, self.icon_pixmap)

        painter.setPen(self.palette().buttonText().color())
        text_rect = QRect(
            0, self.icon_size + 5, self.width(), self.height() - self.icon_size - 5
        )
        painter.drawText(text_rect, Qt.AlignHCenter | Qt.AlignTop, self.text())
        painter.restore()

    # ------------------------------------------------------------
    # 鼠标进入：立即设置一次光标
    # ------------------------------------------------------------

    def enterEvent(self, event):
        self._update_cursor(event.pos())
        super().enterEvent(event)

    def mouseDoubleClickEvent(self, event):
        """
        在编辑模式下，双击按钮名称区域进入重命名状态；
        非编辑模式保持原有行为。
        """
        if self.app and self.app.edit_mode:
            self.start_name_edit()
            return  # 不向父类传递，避免触发拖动
        super().mouseDoubleClickEvent(event)

    # -------------------- 名称编辑核心逻辑 --------------------
    def start_name_edit(self):
        """
        内联进入重命名状态（编辑模式双击 / 右键菜单皆可调用）。
        使用 QTimer.singleShot 确保在弹出式菜单完全关闭后再获取焦点，
        避免偶发需要二次点击的问题。
        """
        from PySide6.QtCore import QTimer      # 局部导入，避免循环依赖

        # ——— 准备编辑框 ——— #
        self.stop_jitter()                     # 停止抖动
        self.name_edit.setText(self.text())    # 预填旧名
        self.name_edit.selectAll()             # 全选文本，方便直接输入

        # 覆盖标题文字区域
        y_start = self.icon_size + 5
        self.name_edit.setGeometry(
            0, y_start,
            self.width(),
            self.height() - y_start
        )
        self.name_edit.show()

        # 关键：等当前事件（右键菜单）处理完再聚焦
        QTimer.singleShot(0, self.name_edit.setFocus)

    def finish_name_edit(self):
        """完成重命名；依据调用来源决定是否恢复抖动，并在成功后立即保存布局。"""
        if not self.name_edit.isVisible():
            return

        new_name = self.name_edit.text().strip()
        self.name_edit.hide()

        # -------- A. 无改动 / 空名 --------
        if not new_name or new_name == self.text():
            if self.app.edit_mode and self.rename_source == "edit":
                self.start_jitter()  # 仅编辑模式下恢复抖动
            return

        # -------- B. 检查重名 --------
        sibling_names = [btn.text() for btn in self.app.buttons if btn is not self]
        if new_name in sibling_names:
            QMessageBox.warning(self, "重名冲突", "已有同名单词本或文件夹！")
            if self.app.edit_mode and self.rename_source == "edit":
                self.start_jitter()
            return

        old_name = self.text()
        self.setText(new_name)

        # -------- C. 文件夹 / 普通按钮处理 --------
        if self.is_folder:
            self.update_folder_icon()  # 文件夹需刷新九宫格图标
        else:
            try:
                self.rename_wordbook_directory(old_name, new_name)
            except Exception as e:
                QMessageBox.warning(self, "重命名失败", f"{e}")
                self.setText(old_name)
                if self.app.edit_mode and self.rename_source == "edit":
                    self.start_jitter()
                return

        # 更新点击路径
        if not self.is_folder:
            try:
                self.clicked.disconnect()
            except TypeError:
                pass
            base_dir = os.path.dirname(os.path.abspath(sys.argv[0]))
            new_path = os.path.join(base_dir, "books",
                                    f"books_{new_name}_{self.color}")
            self.clicked.connect(lambda _, p=new_path: self.app.show_word_book(p))

        # 子按钮刷新父文件夹图标
        if self.is_sub_button and self.parent_folder:
            self.parent_folder.update_folder_icon()

        # 刷新整体布局
        self.app.update_button_positions()

        # -------- D. 立即保存最新布局 --------
        try:
            self.app.save_layout_to_json()  # ⭐ 新增：重命名后立刻持久化
        except Exception as e:
            print(f"❌ 保存布局失败: {e}")

        # -------- E. 结束后抖动恢复策略 --------
        if self.app.edit_mode and self.rename_source == "edit":
            self.start_jitter()

        self.rename_source = "edit"  # 重置来源标记

    def rename_wordbook_directory(self, old_name: str, new_name: str):
        """
        将磁盘上的 books_<名称>_<颜色> 文件夹重命名。
        若目标已存在则抛出异常。
        """
        base_dir  = os.path.dirname(os.path.abspath(sys.argv[0]))
        books_dir = os.path.join(base_dir, "books")
        old_folder = f"books_{old_name}_{self.color}"
        new_folder = f"books_{new_name}_{self.color}"
        old_path = os.path.join(books_dir, old_folder)
        new_path = os.path.join(books_dir, new_folder)

        if os.path.exists(new_path):
            raise FileExistsError("目标名称已存在，请换一个名称。")
        if not os.path.exists(old_path):
            # 若原目录不存在（如首次创建后尚未保存），忽略磁盘重命名
            return

        os.rename(old_path, new_path)

    # --------------------------- 事件 --------------------------- #
    def mousePressEvent(self, event):
        if event.button() == Qt.LeftButton:
            if self.app and getattr(self.app, "edit_mode", False):
                # 编辑模式
                if getattr(self, "is_new_button", False):
                    # “新建单词本”按钮：按原行为直接走基类 QPushButton 的实现
                    QPushButton.mousePressEvent(self, event)
                    return

                # 开始拖动
                self.drag_start_position = event.globalPosition().toPoint()
                self.is_dragging = True
                self.setStyleSheet(
                    "background-color: rgba(200,200,200,0.2); border-radius: 15px;"
                )

                # ⚠️ 折叠所有文件夹的逻辑已经在 DraggableButton 中实现，
                #    只需要保证稍后会调用 super().mousePressEvent(event)
                #    即可触发，无需重复编写。
            else:
                # 非编辑模式：只有点击封面图标区域才响应
                icon_rect = QRect(
                    0,
                    0,
                    self.icon_pixmap.width() if hasattr(self, "icon_pixmap") else self.icon_size,
                    self.icon_size,
                )
                if not icon_rect.contains(event.pos()):
                    return

        self._start_press_effect()
        # 关键修改：调用父类 DraggableButton 的 mousePressEvent，
        # 以触发其内部的 collapse_all_folders() 逻辑
        super().mousePressEvent(event)

        # ------------------------------------------------------------
        # 鼠标移动：拖拽 + 光标更新（编辑模式专用）
        # ------------------------------------------------------------

    def mouseMoveEvent(self, event):
        # —— ① 光标热区实时更新 —— #
        self._update_cursor(event.pos())

        # —— ② 若非“按住左键拖动”场景，交给父类处理即可 —— #
        if (
                not (event.buttons() & Qt.LeftButton)  # 未按住左键
                or not self.is_dragging  # 未进入拖动状态
                or not self.app.edit_mode  # 不在编辑模式
        ):
            super().mouseMoveEvent(event)  # 保持 Hover 效果等
            return

        # ---------- 主/子按钮跟随鼠标移动 ---------- #
        delta = event.globalPosition().toPoint() - self.drag_start_position
        self.move(self.pos() + delta)
        self.drag_start_position = event.globalPosition().toPoint()

        # ---------- A. 子按钮拖拽逻辑 ---------- #
        if self.is_sub_button and self.parent_folder and self.app.edit_mode:
            # 计算除自身外其他子按钮的 folder 区域，保持区域随拖动静止
            other_sub_buttons = [btn for btn in self.parent_folder.sub_buttons if btn is not self]
            folder_area = calculate_folder_area(
                self.parent_folder,
                other_sub_buttons,
                self.app.button_width,
                self.app.button_height,
            )
            min_x, min_y, max_x, max_y = folder_area
            center = QPoint(
                self.x() + self.app.button_width // 2,
                self.y() + self.app.button_height // 2,
            )

            # 判定是否仍在“文件夹内部重排区”
            margin = 10
            left_bound = 0
            right_bound = self.app.scroll_content.width()
            top_bound = min_y
            bottom_bound = max_y
            inside = (
                    left_bound - margin <= center.x() <= right_bound + margin and
                    top_bound - margin <= center.y() <= bottom_bound + margin
            )

            if inside:  # ★ 重排
                self.app.show_blue_reorder_frame(self.parent_folder)
                self.app.hide_red_removal_frame()
                self.drag_out_threshold_exceeded = False
                self.app.update_sub_button_order(
                    self.parent_folder,
                    dragged_sub_button=self,
                    realtime=True,
                )
            else:  # ★ 拖出提示
                self.app.hide_blue_reorder_frame()
                self.app.show_red_removal_frame(self.parent_folder)
                self.drag_out_threshold_exceeded = True

        # ---------- B. 主界面按钮拖拽逻辑 ---------- #
        else:
            # 近距离合并提示框 & 主按钮排序
            self.app.check_button_proximity(self)
            self.app.update_button_order(self)

    def mouseReleaseEvent(self, event):
        # ---------- 1. 编辑模式下拖拽释放 ----------
        if self.app and self.app.edit_mode and self.is_dragging:
            super().mouseReleaseEvent(event)
            self.setDown(False)
            self.update()
            return

        # ---------- 2. 非编辑模式：点击封面 ----------
        if event.button() == Qt.LeftButton:
            icon_rect = QRect(
                0, 0,
                self.icon_pixmap.width() if hasattr(self, "icon_pixmap") else self.icon_size,
                self.icon_size,
            )
            if icon_rect.contains(event.pos()) and self.is_folder:
                self.app.toggle_folder(self)

        self._start_press_effect()
        super().mouseReleaseEvent(event)       # 交回基类，保证 clicked()
        self.setDown(False)                    # 🔑 复位 pressed 状态
        self.update()

    # ------------------------------------------------------------
    # 按压／松开视觉效果（已去除缩小动画）
    # ------------------------------------------------------------
    def _start_press_effect(self):
        """按下时：仅触发深色遮罩的淡入计时，不再缩小按钮尺寸"""
        # ---------- a. 深色遮罩计时 ----------
        self._suppress_dark = False
        self.setFadeOpacity(1.0)  # 立即显示深色层

        if self._fade_anim and self._fade_anim.state() == QPropertyAnimation.Running:
            self._fade_anim.stop()

        if self._long_press_timer:
            self._long_press_timer.stop()
        self._long_press_timer = QTimer(self)
        self._long_press_timer.setSingleShot(True)
        self._long_press_timer.timeout.connect(self._disable_darkening)
        self._long_press_timer.start(100)  # 0.1 s 后允许渐隐

        # ---------- b. 取消所有缩放相关动画 ----------
        self._orig_geometry = None  # 不再记录原始几何
        if self._shrink_anim and self._shrink_anim.state() == QPropertyAnimation.Running:
            self._shrink_anim.stop()
        if self._restore_anim and self._restore_anim.state() == QPropertyAnimation.Running:
            self._restore_anim.stop()
        self._shrink_anim = None
        self._restore_anim = None

    def _end_press_effect(self):
        """松开时：只淡出深色遮罩，不做尺寸复原"""
        # ---------- a. 终止深色遮罩计时 / 动画 ----------
        if self._long_press_timer:
            self._long_press_timer.stop()

        self._suppress_dark = False
        self.setFadeOpacity(0.0)  # 立即隐藏深色层
        if self._fade_anim and self._fade_anim.state() == QPropertyAnimation.Running:
            self._fade_anim.stop()

        # ---------- b. 取消任何残留的缩放动画 ----------
        if self._shrink_anim and self._shrink_anim.state() == QPropertyAnimation.Running:
            self._shrink_anim.stop()
        if self._restore_anim and self._restore_anim.state() == QPropertyAnimation.Running:
            self._restore_anim.stop()
        self._shrink_anim = None
        self._restore_anim = None

    def _disable_darkening(self):
        """0.5 s 到期：深色背景『渐隐』约 180 ms，然后彻底去除"""
        if self._fade_anim and self._fade_anim.state() == QPropertyAnimation.Running:
            self._fade_anim.stop()

        self._fade_anim = QPropertyAnimation(self, b"fadeOpacity")
        self._fade_anim.setDuration(100)  # 若需调整速度就在此改
        self._fade_anim.setEasingCurve(QEasingCurve.OutQuad)
        self._fade_anim.setStartValue(1.0)
        self._fade_anim.setEndValue(0.0)

        def _after():
            self._suppress_dark = True  # 渐隐完毕 → 不再绘制

        self._fade_anim.finished.connect(_after)
        self._fade_anim.start()

    def getFadeOpacity(self) -> float:
        return self._fade_opacity

    def setFadeOpacity(self, value: float):
        self._fade_opacity = value
        self.update()

    fadeOpacity = Property(float, getFadeOpacity, setFadeOpacity)