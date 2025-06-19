import math
from typing import Optional, Tuple

from PySide6.QtCore import Qt, QPoint, QPropertyAnimation, QRect, QEasingCurve, QParallelAnimationGroup, QSize
from PySide6.QtGui import QPainter
from PySide6.QtWidgets import QPushButton, QStyleOptionButton, QStyle
from PySide6.QtCore import Property


class DraggableButton(QPushButton):
    def __init__(self, text, parent, app=None):
        super().__init__(text, parent)
        self.parent_widget = parent
        self.app = app  # 主应用窗口引用
        self.drag_start_position = QPoint()
        self.is_dragging = False
        self.setFixedSize(100, 50)
        self.is_folder = False  # 是否为文件夹按钮
        self.sub_buttons = []  # 存储子按钮
        self.is_expanded = False  # 文件夹是否展开

        # 新增属性，用于标识是否为文件夹内的子按钮
        self.is_sub_button = False
        self.parent_folder = None  # 若为子按钮，记录所属文件夹
        self.drag_out_threshold_exceeded = False  # 标记是否拖出阈值

        # 抖动动画相关
        self.jitter_animation_group = QParallelAnimationGroup(self)
        self.jitter_animations = []  # 存储动画对象，方便管理
        self._rotation = 0  # 用于旋转动画的属性

        # 新增：文件夹展开/关闭动画组属性，防止重复触发
        self.folder_animation_group = None
        # ➤➤➤ 新增：删除小按钮（右上角 ✕） ← iOS 风格
        # 使用简单的 'X' 以保证各平台都能正确显示
        self.delete_button = QPushButton("X", self)
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

    # ✕ 按钮点击 —— 主按钮走 delete_word_book，子按钮走 remove_sub_button_from_folder
    def on_delete_clicked(self):
        """✕ 按钮点击：主按钮、子按钮统一直接删除单词册。

        现在加入保护：主单词册（“总单词册”）永远不可删除。
        """
        # —— 主单词册保护 —— #
        if self.text() == "总单词册":
            from PySide6.QtWidgets import QMessageBox
            QMessageBox.information(
                self,
                "提示",
                "『总单词册』是主单词册，无法删除！"
            )
            return

        # —— 原有逻辑 —— #
        if getattr(self, "is_new_button", False):
            return  # “新建单词册” 不可删

        if hasattr(self.app, "delete_word_book"):
            self.app.delete_word_book(self)

    def start_jitter(self):
        if self.jitter_animation_group.state() == QPropertyAnimation.Running:
            return  # 避免重复启动

        duration = 200  # 动画时长增加到200毫秒，使抖动更平滑
        rotation_angle = 3  # 旋转角度保持不变

        # 清空之前的动画
        self.jitter_animation_group.stop()
        self.jitter_animation_group.clear()
        self.jitter_animations = []

        # 优化旋转动画的关键帧分布，使动画更加平滑
        animation_rotation = QPropertyAnimation(self, b"rotation")
        animation_rotation.setDuration(duration)
        animation_rotation.setKeyValueAt(0, 0)
        animation_rotation.setKeyValueAt(0.3, -rotation_angle)
        animation_rotation.setKeyValueAt(0.5, 0)
        animation_rotation.setKeyValueAt(0.7, rotation_angle)
        animation_rotation.setKeyValueAt(1, 0)
        self.jitter_animations.append(animation_rotation)

        for anim in self.jitter_animations:
            self.jitter_animation_group.addAnimation(anim)

        self.jitter_animation_group.setLoopCount(-1)  # 无限循环
        self.jitter_animation_group.start()
        # ➤ 更新 ✕ 按钮可见性
        self.update_delete_button_visibility()

    # 根据当前是否处于编辑模式决定 ✕ 是否可见
    def update_delete_button_visibility(self):
        """根据是否处于编辑模式决定 ✕ 按钮可见性，并禁止主单词册出现✕ 按钮。"""
        show = (
            self.app
            and getattr(self.app, "edit_mode", False)
            and not getattr(self, "is_new_button", False)
            and self.text() != "总单词册"          # ⭐ 关键：主单词册不显示删除按钮
        )
        self.delete_button.move(self.width() - self.delete_button.width(), 0)
        self.delete_button.setVisible(show)

    def stop_jitter(self):
        if self.jitter_animation_group.state() == QPropertyAnimation.Running:
            self.jitter_animation_group.stop()
            self._rotation = 0
            self.update()
        # ➤ 隐藏 ✕ 按钮
        self.update_delete_button_visibility()

    # 添加rotation属性的getter和setter方法，用于旋转动画
    @Property(float)
    def rotation(self):
        return self._rotation

    @rotation.setter
    def rotation(self, angle):
        self._rotation = angle
        self.update()  # 触发重绘

    def paintEvent(self, event):
        painter = QPainter(self)
        painter.setRenderHint(QPainter.Antialiasing)

        # 保存当前状态
        painter.save()

        # 如果有旋转角度，应用旋转变换
        if self._rotation != 0:
            painter.translate(self.width() / 2, self.height() / 2)
            painter.rotate(self._rotation)
            painter.translate(-self.width() / 2, -self.height() / 2)

        # 绘制按钮背景
        option = QStyleOptionButton()
        option.initFrom(self)
        option.state = QStyle.State_Enabled
        if self.isDown():
            option.state |= QStyle.State_Sunken
        elif self.isChecked():
            option.state |= QStyle.State_On
        elif not self.isFlat():
            option.state |= QStyle.State_Raised
        option.rect = self.rect()
        self.style().drawControl(QStyle.CE_PushButton, option, painter, self)

        # 绘制按钮文本
        painter.setPen(self.palette().buttonText().color())
        painter.drawText(self.rect(), Qt.AlignCenter, self.text())

        # 恢复状态
        painter.restore()

    def mousePressEvent(self, event):
        """
        左键按下 —— 准备拖动（仅编辑模式）

        ✨ 关键点
        ------------------------------------------------------------------
        1. 依旧调用 collapse_all_folders() 折叠全部文件夹；
        2. 记录 _cursor_offset（鼠标位于按钮内的相对坐标）；
        3. 折叠后启动一个 10 ms 周期的 QTimer（持续 0-800 ms）：
              • 每次 timeout → _recenter()，同步滚动条并把按钮
                调整到「当前鼠标全局坐标 − _cursor_offset」处，
                同时更新 drag_start_position。
           因为 _recenter() 每次都取实时鼠标位置，所以拖动过程
           中的任何鼠标移动都会被立即补偿。
        """
        """按下：开启拖拽 + 启动补偿计时器（800 ms 后自动停止）。"""
        if event.button() == Qt.LeftButton and self.app.edit_mode:
            from PySide6.QtCore import QTimer, QPoint
            from PySide6.QtGui  import QCursor

            # —— ① 缓存原位置 —— #
            self._origin_pos = self.pos()

            # —— ② 启动拖拽 —— #
            cursor_global       = event.globalPosition().toPoint()
            btn_global          = self.mapToGlobal(QPoint(0, 0))
            self._cursor_offset = cursor_global - btn_global
            self.drag_start_position = cursor_global
            self.raise_()
            self.is_dragging = True
            self.setStyleSheet("background-color: lightblue;")

            # —— ③ 编辑模式拖动任意按钮：折叠所有文件夹，方便排序 —— #
            if callable(getattr(self.app, "collapse_all_folders", None)):
                scroll_area = getattr(self.app, "scroll_area", None)
                old_scroll  = scroll_area.verticalScrollBar().value() if scroll_area else None
                self.app.collapse_all_folders(skip_buttons=[self])

                def _recenter():
                    if scroll_area and old_scroll is not None:
                        sb = scroll_area.verticalScrollBar()
                        sb.setValue(min(old_scroll, sb.maximum()))
                    cursor_now    = QCursor.pos()
                    target_global = cursor_now - self._cursor_offset
                    shift         = target_global - self.mapToGlobal(QPoint(0, 0))
                    if shift:
                        self.move(self.pos() + shift)
                    self.drag_start_position = cursor_now

                self._recenter_timer = QTimer(self)
                self._recenter_timer.setInterval(10)
                self._recenter_timer.timeout.connect(_recenter)
                self._recenter_timer.start()
                _recenter()  # 立即补偿首帧

                # —— ④ 800 ms 后安全停止 —— #
                QTimer.singleShot(800, self._stop_recenter_timer)

        super().mousePressEvent(event)

    def mouseMoveEvent(self, event):
        if not (event.buttons() & Qt.LeftButton) or not self.is_dragging or not self.app.edit_mode:
            return

        delta = event.globalPosition().toPoint() - self.drag_start_position
        new_pos = self.pos() + delta
        self.move(new_pos)
        self.drag_start_position = event.globalPosition().toPoint()

        # 如果是文件夹内的子按钮，则执行拖出或重排序逻辑
        if self.is_sub_button and self.parent_folder and self.app.edit_mode:
            # 计算文件夹内子按钮的布局区域
            folder_spacing = self.app.spacing * 1.5
            available_width = self.app.central_widget.width() - folder_spacing * 1.5 + self.app.folder_extra_width
            buttons_per_row = max(1, available_width // (self.app.button_width + folder_spacing))
            rows = (len(self.parent_folder.sub_buttons) + buttons_per_row - 1) // buttons_per_row

            # 计算重排序区域的边界
            reorder_area_left = self.parent_folder.x() - folder_spacing
            reorder_area_top = self.parent_folder.y() + self.app.button_height
            reorder_area_width = available_width + folder_spacing * 1.01
            reorder_area_height = (rows * (self.app.button_height + folder_spacing)) + folder_spacing * 1.01
            reorder_area = QRect(reorder_area_left, reorder_area_top, reorder_area_width, reorder_area_height)

            # 判断按钮是否在重排序区域内
            button_rect = QRect(self.pos(), self.size())
            if reorder_area.contains(button_rect.center()):
                # 显示蓝色框表示文件夹内重排序区域
                self.app.show_blue_reorder_frame(self.parent_folder)
                self.app.hide_red_removal_frame()
                self.drag_out_threshold_exceeded = False
                # 实时更新文件夹内子按钮排序（直接更新位置，无动画）
                self.app.update_sub_button_order(self.parent_folder, dragged_sub_button=self, realtime=True)
            else:
                # 超过阈值，显示红色框提示拖出文件夹
                self.app.hide_blue_reorder_frame()
                self.app.show_red_removal_frame(self.parent_folder)
                self.drag_out_threshold_exceeded = True
        else:
            # 主界面按钮执行原有的靠近检测和排序
            self.app.check_button_proximity(self)
            self.app.update_button_order(self)

    def mouseReleaseEvent(self, event):
        """
                拖拽释放 / 普通点击统一入口
                • 拖拽场景：保持子按钮重排序、文件夹合并等原有逻辑
                • 点击场景：编辑模式下仅做拖拽；非编辑模式才允许打开 / 展开
                同时在 super() 之后 setDown(False) 立即复位 pressed 颜色
                """
        """释放：停止补偿计时器；正常收尾（排序 / 合并 / 回弹）"""
        if self.app.edit_mode and self.is_dragging:
            self.is_dragging = False
            self.setStyleSheet("")

            # —— A. 子按钮 —— #
            if self.is_sub_button and self.parent_folder:
                if not self.drag_out_threshold_exceeded:
                    self.app.update_sub_button_order(
                        self.parent_folder, dragged_sub_button=self, realtime=False
                    )
                else:
                    self.app.remove_sub_button_from_folder(self)
                self.app.hide_blue_reorder_frame()
                self.app.hide_red_removal_frame()
                self.drag_out_threshold_exceeded = False

            # —— B. 主按钮 —— #
            else:
                if self.app.frame_visible and self.app.is_button_in_frame(self):
                    self.app.merge_folders()
                self.app.finalize_button_order()
                self.app.hide_frame()

            # 拖拽结束后恢复之前的展开状态（无论拖动哪种按钮）
            self.app.expand_all_folders()

            self.app.update_button_positions()

        elif not self.app.edit_mode and getattr(self, "is_folder", False):
            self.app.toggle_folder(self)

            # —— ★ 安全停止补偿计时器 —— #
        self._stop_recenter_timer()

        super().mouseReleaseEvent(event)
        self.setDown(False)
        self.update()

    # ============================================================
#  Button —— 计时器安全处理
# ============================================================

    def _stop_recenter_timer(self):
        """安全停止并销毁 _recenter_timer（若存在）。"""
        if hasattr(self, "_recenter_timer") and self._recenter_timer:
            if self._recenter_timer.isActive():
                self._recenter_timer.stop()
            self._recenter_timer.deleteLater()
            self._recenter_timer = None
