import math
import sys
from typing import Optional, Tuple

from PySide6.QtCore import Qt, QPoint, QPropertyAnimation, QRect, QEasingCurve, QParallelAnimationGroup, QSize
from PySide6.QtGui import QPainter
from PySide6.QtWidgets import (
    QApplication,
    QMainWindow,
    QPushButton,
    QVBoxLayout,
    QWidget,
    QFrame, QStyleOptionButton, QStyle
)
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

    def stop_jitter(self):
        if self.jitter_animation_group.state() == QPropertyAnimation.Running:
            self.jitter_animation_group.stop()
            # 确保旋转角度恢复到0度
            self._rotation = 0
            self.update()  # 触发重绘以更新显示

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
        if event.button() == Qt.LeftButton:
            if self.app.edit_mode:  # 仅在编辑模式下检测拖动
                self.drag_start_position = event.globalPosition().toPoint()
                self.raise_()
                self.is_dragging = True
                self.setStyleSheet("background-color: lightblue;")
                print(f"Button {self.text()} Mouse Press - is_dragging: {self.is_dragging}")
            else:
                # 非编辑模式下点击交由 mouseReleaseEvent 处理
                pass
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
        if self.is_dragging and self.app.edit_mode:
            self.is_dragging = False
            self.setStyleSheet("")
            # 如果是文件夹内子按钮，在编辑模式下检测是否拖出父文件夹区域
            if self.is_sub_button and self.parent_folder and self.app.edit_mode:
                self.app.hide_blue_reorder_frame()  # 拖动结束后隐藏蓝色框
                if not self.drag_out_threshold_exceeded:
                    print(f"子按钮 {self.text()} 在文件夹 {self.parent_folder.text()} 区域内释放，执行文件夹内重排序")
                    # 采用动画方式调整（松手后直接保存排序）
                    self.app.update_sub_button_order(self.parent_folder, dragged_sub_button=self, realtime=False)
                elif self.drag_out_threshold_exceeded:
                    parent_rect = QRect(self.parent_folder.pos(), self.parent_folder.size())
                    button_center = self.pos() + QPoint(self.width() // 2, self.height() // 2)
                    if not parent_rect.contains(button_center):
                        print(f"子按钮 {self.text()} 被拖出文件夹 {self.parent_folder.text()} 区域，执行移出操作")
                        self.app.remove_sub_button_from_folder(self)
                self.app.hide_red_removal_frame()
                self.drag_out_threshold_exceeded = False
            else:
                # 检查是否在框内释放鼠标，如是则合并文件夹
                if self.app and self.app.frame_visible and self.app.is_button_in_frame(self):
                    print(f"事件触发: 按钮 {self.text()} 在框内释放，准备合并文件夹")
                    self.app.merge_folders()
                if self.app:
                    self.app.finalize_button_order()
                    self.app.hide_frame()
            print(f"Button {self.text()} Mouse Release - is_dragging: {self.is_dragging}")
            super().mouseReleaseEvent(event)
        else:
            # 非编辑模式下，若非拖拽操作，则点击文件夹按钮切换展开/关闭
            if not self.app.edit_mode and self.is_folder:
                print(f"文件夹按钮 {self.text()} 被点击，切换展开/关闭状态")
                self.app.toggle_folder(self)
            else:
                super().mouseReleaseEvent(event)


class ButtonFrame(QFrame):
    def __init__(self, parent, border_style):
        super().__init__(parent)
        self.setFrameShape(QFrame.Box)
        self.setLineWidth(2)
        self.setStyleSheet(border_style)
        self.hide()


class DraggableFolderApp(QMainWindow):
    def __init__(self):
        super().__init__()
        self.setWindowTitle("可拖拽文件夹按钮示例")
        self.setGeometry(100, 100, 600, 400)

        # 创建中央部件和主布局
        self.central_widget = QWidget()
        self.main_layout = QVBoxLayout(self.central_widget)
        self.setCentralWidget(self.central_widget)

        # 编辑模式按钮
        self.edit_mode = False
        self.edit_button = QPushButton("Edit", self.central_widget)
        self.edit_button.setFixedSize(60, 30)
        self.edit_button.move(10, 10)
        self.edit_button.clicked.connect(self.toggle_edit_mode)

        # 创建主界面按钮（初始为主按钮，增加到10个）
        self.buttons = [DraggableButton(f"Button {i + 1}", self.central_widget, self) for i in range(10)]
        # 初始位置将由 update_button_positions 方法自动计算
        for i, btn in enumerate(self.buttons):
            row = i // 3
            col = i % 3
            btn.move(100 + col * 150, 100 + row * 70)

        # 按钮属性
        self.button_width = 100
        self.button_height = 50
        self.spacing = 20
        self.buttons_per_row = 0  # 动态计算
        self.drag_out_threshold = 200  # 拖出文件夹的阈值

        # 用于显示合并提示的蓝色框（主界面）
        self.frame = ButtonFrame(self.central_widget,
                                 "border: 2px dashed #3498db; background-color: rgba(52, 152, 219, 0.1);")
        self.frame_visible = False

        # 红色虚线框提示拖出文件夹
        self.red_removal_frame = ButtonFrame(self.central_widget,
                                             "border: 2px dashed red; background-color: rgba(255, 0, 0, 0.1);")
        self.red_removal_frame.hide()

        # 蓝色虚线框用于显示文件夹内重排序范围（固定大小）
        self.blue_reorder_frame = ButtonFrame(self.central_widget,
                                              "border: 2px dashed blue; background-color: rgba(0, 0, 255, 0.1);")
        self.blue_reorder_frame.hide()

        # 当前靠近的按钮对（用于合并文件夹逻辑）
        self.proximity_pair: Optional[Tuple[DraggableButton, DraggableButton]] = None
        self.proximity_threshold = 68

        # 新增参数：扩展文件夹内的操作区域（单位：像素）
        self.folder_extra_width = 150

        self.update_button_positions()

    def toggle_edit_mode(self):
        self.edit_mode = not self.edit_mode
        # 遍历所有按钮，控制抖动动画（包括主按钮和子按钮）
        all_buttons = self.buttons + [sub_btn for btn in self.buttons if btn.is_folder for sub_btn in btn.sub_buttons]
        for button in all_buttons:
            if self.edit_mode:
                button.start_jitter()
            else:
                button.stop_jitter()
        if self.edit_mode:
            self.edit_button.setText("Exit Edit")
            print("进入编辑模式：自动展开所有文件夹并启动抖动")
            # 自动展开所有文件夹
            for btn in self.buttons:
                if btn.is_folder and not btn.is_expanded:
                    btn.is_expanded = True
                    for sub_btn in btn.sub_buttons:
                        sub_btn.show()
                btn.start_jitter()  # 启动抖动效果
            self.update_button_positions()
        else:
            self.edit_button.setText("Edit")
            print("退出编辑模式：停止抖动")
            for btn in self.buttons:
                btn.stop_jitter()  # 停止抖动效果
            self.update_button_positions()

    def resizeEvent(self, event):
        super().resizeEvent(event)
        # 窗口大小变化时实时重排版所有按钮
        self.update_button_positions()

    def update_button_positions(self):
        """更新所有按钮的位置，主界面按钮与文件夹内子按钮分开排列，支持窗口大小调整时实时重排版"""
        available_width = self.central_widget.width()
        button_width_with_spacing = self.button_width + self.spacing
        # 动态计算每行可容纳的按钮数量，确保至少有1个按钮
        self.buttons_per_row = max(1, (available_width - self.spacing) // button_width_with_spacing)

        start_x = self.spacing
        start_y = self.spacing + 40  # 留出编辑按钮的空间
        current_x = start_x
        current_y = start_y

        # 先处理非拖拽状态的主界面按钮
        for btn in self.buttons:
            if btn.is_folder and btn.is_expanded:
                if not btn.is_dragging:
                    btn.move(current_x, current_y)
                folder_x = current_x
                folder_y = current_y

                # 计算子按钮位置，使用更大的操作区域
                folder_spacing = self.spacing * 1.5
                available_sub_width = available_width - folder_spacing + self.folder_extra_width
                sub_buttons_per_row = max(1, (available_sub_width - folder_spacing) // (
                            self.button_width + folder_spacing))

                sub_x = start_x
                sub_y = folder_y + self.button_height + self.spacing
                sub_row = 0
                sub_col = 0

                for sub_btn in btn.sub_buttons:
                    if sub_col >= sub_buttons_per_row:
                        sub_row += 1
                        sub_col = 0
                        sub_x = start_x
                        sub_y = folder_y + self.button_height + self.spacing + sub_row * (
                                    self.button_height + self.spacing)

                    if not sub_btn.is_dragging:
                        sub_btn.move(sub_x, sub_y)
                        sub_btn.show()

                    sub_x += self.button_width + folder_spacing
                    sub_col += 1

                # 根据子按钮占用行数调整下一个主按钮的位置
                sub_rows = (len(btn.sub_buttons) + sub_buttons_per_row - 1) // sub_buttons_per_row
                current_y = folder_y + self.button_height + self.spacing * (
                            sub_rows + 1) + self.button_height * sub_rows
                current_x = start_x
            else:
                if current_x + self.button_width > available_width - self.spacing:
                    current_y += self.button_height + self.spacing
                    current_x = start_x
                if not btn.is_dragging:
                    btn.move(current_x, current_y)
                current_x += button_width_with_spacing

    def check_button_proximity(self, dragged_button):
        """检查拖动的主界面按钮是否与其他主界面按钮靠近"""
        if dragged_button.is_sub_button:
            return
        closest_button = None
        min_distance = float('inf')
        for btn in self.buttons:
            if btn != dragged_button and not btn.is_sub_button:
                distance = self.calculate_button_distance(dragged_button, btn)
                if distance < min_distance:
                    min_distance = distance
                    closest_button = btn
        if min_distance < self.proximity_threshold:
            self.show_frame(dragged_button, closest_button)
            self.proximity_pair = (dragged_button, closest_button)
        else:
            self.hide_frame()
            self.proximity_pair = None

    def calculate_button_distance(self, btn1, btn2):
        center1 = btn1.pos() + QPoint(self.button_width // 2, self.button_height // 2)
        center2 = btn2.pos() + QPoint(self.button_width // 2, self.button_height // 2)
        dx = center1.x() - center2.x()
        dy = center1.y() - center2.y()
        return math.sqrt(dx * dx + dy * dy)

    def show_frame(self, btn1, btn2):
        left = min(btn1.x(), btn2.x()) - 10
        top = min(btn1.y(), btn2.y()) - 10
        right = max(btn1.x() + self.button_width, btn2.x() + self.button_width) + 10
        bottom = max(btn1.y() + self.button_height, btn2.y() + self.button_height) + 10
        self.frame.setGeometry(left, top, right - left, bottom - top)
        self.frame.show()
        self.frame_visible = True

    def hide_frame(self):
        self.frame.hide()
        self.frame_visible = False

    def show_red_removal_frame(self, parent_folder):
        """显示红色虚线框，包围文件夹按钮及其所有子按钮"""
        min_x = parent_folder.x()
        min_y = parent_folder.y()
        max_x = parent_folder.x() + parent_folder.width()
        max_y = parent_folder.y() + parent_folder.height()
        for sub_btn in parent_folder.sub_buttons:
            min_x = min(min_x, sub_btn.x())
            min_y = min(min_y, sub_btn.y())
            max_x = max(max_x, sub_btn.x() + sub_btn.width())
            max_y = max(max_y, sub_btn.y() + sub_btn.height())
        margin = 10
        left = min_x - margin
        top = min_y - margin
        right = max_x + margin
        bottom = max_y + margin
        self.red_removal_frame.setGeometry(left, top, right - left, bottom - top)
        self.red_removal_frame.show()

    def hide_red_removal_frame(self):
        self.red_removal_frame.hide()

    def show_blue_reorder_frame(self, parent_folder):
        """显示蓝色虚线框，标识文件夹内重排序范围"""
        min_x = parent_folder.x()
        min_y = parent_folder.y()
        max_x = parent_folder.x() + parent_folder.width()
        max_y = parent_folder.y() + parent_folder.height()
        for sub_btn in parent_folder.sub_buttons:
            min_x = min(min_x, sub_btn.x())
            min_y = min(min_y, sub_btn.y())
            max_x = max(max_x, sub_btn.x() + sub_btn.width())
            max_y = max(max_y, sub_btn.y() + sub_btn.height())
        margin = 10
        left = min_x - margin
        top = min_y - margin
        right = max_x + margin
        bottom = max_y + margin
        self.blue_reorder_frame.setGeometry(left, top, right - left, bottom - top)
        self.blue_reorder_frame.show()

    def hide_blue_reorder_frame(self):
        self.blue_reorder_frame.hide()

    def is_button_in_frame(self, button):
        if not self.frame_visible:
            return False
        button_rect = QRect(button.pos(), button.size())
        frame_rect = QRect(self.frame.pos(), self.frame.size())
        return frame_rect.contains(button_rect)

    def merge_folders(self):
        """合并两个主界面按钮为一个文件夹，或将按钮添加到现有文件夹"""
        if not self.proximity_pair:
            return
        btn1, btn2 = self.proximity_pair

        if btn2.is_folder:  # Dragged onto an existing folder (btn2 is the folder)
            print(f"将按钮 {btn1.text()} 添加到现有文件夹 {btn2.text()}")
            self.add_button_to_folder(btn1, btn2)
        elif btn1.is_folder:  # Dragged onto an existing folder (btn1 is the folder)
            print(f"将按钮 {btn2.text()} 添加到现有文件夹 {btn1.text()}")
            self.add_button_to_folder(btn2, btn1)
        else:
            print(f"合并按钮 {btn1.text()} 和 {btn2.text()} 创建新文件夹")
            folder_name = f"Folder {len([b for b in self.buttons if b.is_folder]) + 1}"
            folder_button = DraggableButton(folder_name, self.central_widget, self)
            folder_button.is_folder = True
            folder_button.move(btn1.pos())
            folder_button.setStyleSheet("background-color: #f0f0f0; font-weight: bold;")
            # 将原按钮作为子按钮加入文件夹
            if btn1.is_folder:
                folder_button.sub_buttons.extend(btn1.sub_buttons)
            else:
                sub_btn1 = DraggableButton(btn1.text(), self.central_widget, self)
                sub_btn1.is_sub_button = True
                sub_btn1.parent_folder = folder_button
                folder_button.sub_buttons.append(sub_btn1)
                sub_btn1.hide()
            if btn2.is_folder:
                folder_button.sub_buttons.extend(btn2.sub_buttons)
            else:
                sub_btn2 = DraggableButton(btn2.text(), self.central_widget, self)
                sub_btn2.is_sub_button = True
                sub_btn2.parent_folder = folder_button
                folder_button.sub_buttons.append(sub_btn2)
                sub_btn2.hide()
            self.buttons.remove(btn1)
            self.buttons.remove(btn2)
            self.buttons.append(folder_button)
            folder_button.show()
            btn1.hide()
            btn2.hide()
            self.toggle_folder(folder_button)  # 自动展开新文件夹
            # 确保新创建的文件夹按钮在编辑模式下有抖动效果
            if self.edit_mode:
                folder_button.start_jitter()
                for sub_btn in folder_button.sub_buttons:
                    sub_btn.start_jitter()

        self.update_button_positions()
        self.hide_frame()  # 合并后隐藏提示框

    def add_button_to_folder(self, button_to_add, folder):
        """将一个按钮添加到现有文件夹"""
        sub_btn = DraggableButton(button_to_add.text(), self.central_widget, self)
        sub_btn.is_sub_button = True
        sub_btn.parent_folder = folder
        folder.sub_buttons.append(sub_btn)
        sub_btn.hide()  # 初始隐藏
        self.buttons.remove(button_to_add)
        button_to_add.hide()
        if not folder.is_expanded and self.edit_mode:
            self.toggle_folder(folder)  # 展开文件夹以显示新子按钮
        elif folder.is_expanded:
            self.update_button_positions()
        else:
            self.update_button_positions()
        if self.edit_mode:
            sub_btn.start_jitter()

    def toggle_folder(self, folder_button):
        if not folder_button.is_folder:
            return

        # 若已有动画正在进行，则忽略点击
        if folder_button.folder_animation_group and folder_button.folder_animation_group.state() == QParallelAnimationGroup.Running:
            return

        folder_button.is_expanded = not folder_button.is_expanded
        print(f"切换文件夹 {folder_button.text()} 状态: is_expanded = {folder_button.is_expanded}")

        # 计算目标位置：参照 update_sub_button_order 的布局逻辑
        folder_spacing = self.spacing * 2
        current_y = folder_button.y() + self.button_height + folder_spacing
        available_width = self.central_widget.width() - folder_spacing * 2 + self.folder_extra_width
        sub_buttons_per_row = max(1, available_width // (self.button_width + folder_spacing))
        target_positions = []
        rows = (len(folder_button.sub_buttons) + sub_buttons_per_row - 1) // sub_buttons_per_row
        for row in range(rows):
            for col in range(sub_buttons_per_row):
                if len(target_positions) < len(folder_button.sub_buttons):
                    x = folder_spacing + col * (self.button_width + folder_spacing)
                    y = current_y + row * (self.button_height + folder_spacing)
                    target_positions.append(QPoint(x, y))

        master_anim_group = QParallelAnimationGroup()
        duration_base = 400

        # 遍历每个子按钮，添加位置和透明度动画
        for index, sub_btn in enumerate(folder_button.sub_buttons):
            # 若展开：先显示子按钮，并设置初始状态
            if folder_button.is_expanded:
                sub_btn.show()
                sub_btn.setWindowOpacity(0)
                start_pos = folder_button.pos()
                end_pos = target_positions[index]
            else:
                # 关闭时，动画从当前位置到文件夹按钮位置
                start_pos = sub_btn.pos()
                end_pos = folder_button.pos()

            pos_anim = QPropertyAnimation(sub_btn, b"pos")
            pos_anim.setDuration(duration_base + index * 100)
            pos_anim.setStartValue(start_pos)
            pos_anim.setEndValue(end_pos)
            # 使用弹性曲线
            pos_anim.setEasingCurve(QEasingCurve.OutBack if folder_button.is_expanded else QEasingCurve.InBack)
            master_anim_group.addAnimation(pos_anim)

            opacity_anim = QPropertyAnimation(sub_btn, b"windowOpacity")
            opacity_anim.setDuration(duration_base - 50)
            if folder_button.is_expanded:
                opacity_anim.setStartValue(0)
                opacity_anim.setEndValue(1)
            else:
                opacity_anim.setStartValue(1)
                opacity_anim.setEndValue(0)
            opacity_anim.setEasingCurve(QEasingCurve.InOutQuad)
            master_anim_group.addAnimation(opacity_anim)

            # 可选：尺寸动画（此处不修改固定尺寸，可根据需求取消下面代码）
            # size_anim = QPropertyAnimation(sub_btn, b"size")
            # size_anim.setDuration(duration_base - 50)
            # if folder_button.is_expanded:
            #     size_anim.setStartValue(QSize(0, 0))
            #     size_anim.setEndValue(QSize(self.button_width, self.button_height))
            # else:
            #     size_anim.setStartValue(QSize(self.button_width, self.button_height))
            #     size_anim.setEndValue(QSize(0, 0))
            # size_anim.setEasingCurve(QEasingCurve.OutCubic)
            # master_anim_group.addAnimation(size_anim)

            # 关闭时动画结束后隐藏子按钮
            if not folder_button.is_expanded:
                pos_anim.finished.connect(sub_btn.hide)

        # 动画结束后更新整个界面布局
        master_anim_group.finished.connect(self.update_button_positions)
        folder_button.folder_animation_group = master_anim_group
        master_anim_group.start()

    def update_button_order(self, dragged_button):
        if dragged_button.is_folder and dragged_button.is_expanded:
            return
        other_buttons = [btn for btn in self.buttons if btn != dragged_button and not btn.is_sub_button]
        target_positions = []
        current_x = self.spacing
        current_y = self.spacing + 40
        for i in range(len([btn for btn in self.buttons if not btn.is_sub_button])):
            if current_x + self.button_width > self.central_widget.width() - self.spacing:
                current_y += self.button_height + self.spacing
                current_x = self.spacing
            target_positions.append(QPoint(current_x, current_y))
            current_x += self.button_width + self.spacing

        dragged_x = dragged_button.x()
        dragged_y = dragged_button.y()

        def calculate_distance_to_target(index):
            target_pos = target_positions[index]
            return (target_pos - QPoint(dragged_x, dragged_y)).manhattanLength()

        if target_positions:
            insert_index = min(range(len(target_positions)), key=calculate_distance_to_target)
        else:
            insert_index = 0

        new_buttons = []
        other_buttons_iter = iter(other_buttons)
        for i in range(len(target_positions) + 1):
            if i == insert_index:
                new_buttons.append(dragged_button)
            else:
                try:
                    new_buttons.append(next(other_buttons_iter))
                except StopIteration:
                    pass

        print(f"update_button_order - Dragged: {dragged_button.text()}, insert_index: {insert_index}")
        main_buttons = [btn for btn in self.buttons if not btn.is_sub_button]
        for btn in new_buttons:
            if btn in main_buttons:
                main_buttons.remove(btn)
        main_buttons = new_buttons
        self.buttons = [btn for btn in self.buttons if btn.is_sub_button] + main_buttons
        self.animate_button_positions(dragged_button)

    def animate_button_positions(self, dragged_button=None):
        target_positions = []
        current_x = self.spacing
        current_y = self.spacing + 40
        main_buttons = [btn for btn in self.buttons if not btn.is_sub_button]
        for i in range(len(main_buttons)):
            if current_x + self.button_width > self.central_widget.width() - self.spacing:
                current_y += self.button_height + self.spacing
                current_x = self.spacing
            target_positions.append(QPoint(current_x, current_y))
            current_x += self.button_width + self.spacing

        for i, btn in enumerate(main_buttons):
            target_pos = target_positions[i]
            if btn != dragged_button and not btn.is_dragging:
                btn.move(target_pos)

    def finalize_button_order(self):
        target_positions = []
        current_x = self.spacing
        current_y = self.spacing + 40
        main_buttons = [btn for btn in self.buttons if not btn.is_sub_button]
        for i in range(len(main_buttons)):
            if current_x + self.button_width > self.central_widget.width() - self.spacing:
                current_y += self.button_height + self.spacing
                current_x = self.spacing
            target_positions.append(QPoint(current_x, current_y))
            current_x += self.button_width + self.spacing

        for i, btn in enumerate(main_buttons):
            target_pos = target_positions[i]
            if btn.pos() != target_pos:
                animation = QPropertyAnimation(btn, b"pos")
                animation.setDuration(200)
                animation.setEndValue(target_pos)
                animation.start()

        self.update_button_positions()

    def update_sub_button_order(self, folder_button, dragged_sub_button=None, realtime=False):
        """更新文件夹内子按钮的位置，实现实时吸附排序"""
        target_positions = []
        folder_spacing = self.spacing * 2  # 文件夹内使用更大间距
        current_y = folder_button.y() + self.button_height + folder_spacing
        available_width = self.central_widget.width() - folder_spacing * 2 + self.folder_extra_width
        buttons_per_row = max(1, available_width // (self.button_width + folder_spacing))
        rows = (len(folder_button.sub_buttons) + buttons_per_row - 1) // buttons_per_row
        for row in range(rows):
            for col in range(buttons_per_row):
                if len(target_positions) < len(folder_button.sub_buttons):
                    x = folder_spacing + col * (self.button_width + folder_spacing)
                    y = current_y + row * (self.button_height + folder_spacing)
                    target_positions.append(QPoint(x, y))

        if dragged_sub_button:
            dragged_center = QPoint(dragged_sub_button.x() + self.button_width // 2,
                                    dragged_sub_button.y() + self.button_height // 2)
            min_distance = float('inf')
            closest_index = 0
            for i, target_pos in enumerate(target_positions):
                target_center = QPoint(target_pos.x() + self.button_width // 2,
                                       target_pos.y() + self.button_height // 2)
                distance = (target_center - dragged_center).manhattanLength()
                if distance < min_distance:
                    min_distance = distance
                    closest_index = i
            sub_buttons = [btn for btn in folder_button.sub_buttons if btn != dragged_sub_button]
            new_sub_buttons = []
            other_buttons_iter = iter(sub_buttons)
            for i in range(len(folder_button.sub_buttons)):
                if i == closest_index:
                    new_sub_buttons.append(dragged_sub_button)
                else:
                    try:
                        new_sub_buttons.append(next(other_buttons_iter))
                    except StopIteration:
                        pass
            folder_button.sub_buttons = new_sub_buttons

        if realtime:
            self.finalize_sub_button_order_realtime(folder_button, dragged_button=dragged_sub_button)
        else:
            self.finalize_sub_button_order(folder_button, dragged_button=dragged_sub_button)

    def finalize_sub_button_order(self, folder_button, dragged_button=None):
        """使用动画方式更新子按钮位置（松手后保存排序）"""
        target_positions = []
        folder_spacing = self.spacing * 2
        current_y = folder_button.y() + self.button_height + folder_spacing
        available_width = self.central_widget.width() - folder_spacing * 2 + self.folder_extra_width
        buttons_per_row = max(1, available_width // (self.button_width + folder_spacing))
        rows = (len(folder_button.sub_buttons) + buttons_per_row - 1) // buttons_per_row
        for row in range(rows):
            for col in range(buttons_per_row):
                if len(target_positions) < len(folder_button.sub_buttons):
                    x = folder_spacing + col * (self.button_width + folder_spacing)
                    y = current_y + row * (self.button_height + folder_spacing)
                    target_positions.append(QPoint(x, y))
        animation_group = QParallelAnimationGroup()
        for i, btn in enumerate(folder_button.sub_buttons):
            if i < len(target_positions) and btn != dragged_button and not btn.is_dragging:
                animation = QPropertyAnimation(btn, b"pos")
                animation.setDuration(300)
                animation.setEasingCurve(QEasingCurve.OutBack)
                animation.setStartValue(btn.pos())
                animation.setEndValue(target_positions[i])
                animation_group.addAnimation(animation)
        animation_group.start()

    def finalize_sub_button_order_realtime(self, folder_button, dragged_button=None):
        """实时更新文件夹内子按钮位置，不使用动画"""
        target_positions = []
        folder_spacing = self.spacing * 2
        current_y = folder_button.y() + self.button_height + folder_spacing
        available_width = self.central_widget.width() - folder_spacing * 2 + self.folder_extra_width
        buttons_per_row = max(1, available_width // (self.button_width + folder_spacing))
        rows = (len(folder_button.sub_buttons) + buttons_per_row - 1) // buttons_per_row
        for row in range(rows):
            for col in range(buttons_per_row):
                if len(target_positions) < len(folder_button.sub_buttons):
                    x = folder_spacing + col * (self.button_width + folder_spacing)
                    y = current_y + row * (self.button_height + folder_spacing)
                    target_positions.append(QPoint(x, y))
        for i, btn in enumerate(folder_button.sub_buttons):
            if i < len(target_positions) and btn != dragged_button and not btn.is_dragging:
                btn.move(target_positions[i])

    def remove_sub_button_from_folder(self, sub_btn):
        parent_folder = sub_btn.parent_folder
        if parent_folder:
            if sub_btn in parent_folder.sub_buttons:
                parent_folder.sub_buttons.remove(sub_btn)
            if sub_btn not in self.buttons:
                self.buttons.append(sub_btn)
            sub_btn.is_sub_button = False
            sub_btn.parent_folder = None
            sub_btn.show()
            if self.edit_mode:
                sub_btn.start_jitter()
            self.update_button_positions()
            self.check_and_remove_folder_if_needed(parent_folder)

    def check_and_remove_folder_if_needed(self, folder_btn):
        if len(folder_btn.sub_buttons) < 2:
            print(f"文件夹 {folder_btn.text()} 内按钮不足2个，执行删除文件夹操作")
            if folder_btn in self.buttons:
                self.buttons.remove(folder_btn)
            if len(folder_btn.sub_buttons) == 1:
                remaining_btn = folder_btn.sub_buttons[0]
                remaining_btn.is_sub_button = False
                remaining_btn.parent_folder = None
                if remaining_btn not in self.buttons:
                    self.buttons.append(remaining_btn)
            folder_btn.hide()
            self.update_button_positions()


if __name__ == "__main__":
    app = QApplication(sys.argv)
    window = DraggableFolderApp()
    window.show()
    sys.exit(app.exec())
