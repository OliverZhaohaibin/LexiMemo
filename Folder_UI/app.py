import sys
from typing import Optional, Tuple

from PySide6.QtCore import Qt, QPoint, QRect, QPropertyAnimation, QParallelAnimationGroup, QEasingCurve
from PySide6.QtWidgets import QApplication, QMainWindow, QPushButton, QVBoxLayout, QWidget

from button import DraggableButton
from frame import ButtonFrame
from utils import calculate_button_distance, is_button_in_frame
from animations import create_folder_toggle_animation, create_button_position_animation
from layout import (
    calculate_main_button_positions, calculate_sub_button_positions,
    calculate_folder_area, calculate_reorder_area
)
from folder_operations import (
    merge_buttons_to_folder, add_button_to_folder,
    remove_sub_button_from_folder, check_and_remove_folder_if_needed
)
from folder_background import update_folder_background, update_all_folder_backgrounds


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
        
        # 新增：记录文件夹展开状态，用于拖动结束后恢复
        self.folder_expanded_states = {}
        self.all_folders_collapsed = False

        self.update_button_positions()
        
    def toggle_edit_mode(self):
        """切换编辑模式"""
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
            # 更新所有文件夹背景
            update_all_folder_backgrounds(self, self.button_width, self.button_height)
        else:
            self.edit_button.setText("Edit")
            print("退出编辑模式：停止抖动")
            for btn in self.buttons:
                btn.stop_jitter()  # 停止抖动效果
            self.update_button_positions()
            
    def resizeEvent(self, event):
        """窗口大小变化事件处理"""
        super().resizeEvent(event)
        # 窗口大小变化时实时重排版所有按钮
        self.update_button_positions()
        # 更新所有展开文件夹的背景框
        update_all_folder_backgrounds(self, self.button_width, self.button_height)

    def update_button_positions(self):
        """更新所有按钮的位置，使用统一的网格布局逻辑，子按钮独占行"""
        available_width = self.central_widget.width()
        button_width_with_spacing = self.button_width + self.spacing
        self.buttons_per_row = max(1, (available_width - self.spacing) // button_width_with_spacing)
    
        start_x = self.spacing
        start_y = self.spacing + 40  # 留出编辑按钮的空间
        current_x = start_x
        current_y = start_y
    
        # 遍历所有按钮
        for btn in self.buttons:
            if not btn.is_dragging:
                # 检查是否需要换行
                if current_x + self.button_width > available_width - self.spacing:
                    current_y += self.button_height + self.spacing
                    current_x = start_x
    
                # 移动主按钮
                btn.move(current_x, current_y)
                
                # 如果是展开的文件夹，处理子按钮
                if btn.is_folder and btn.is_expanded:
                    # 子按钮从新的一行开始
                    current_y += self.button_height + self.spacing
                    current_x = start_x
                    
                    # 布局子按钮
                    for sub_btn in btn.sub_buttons:
                        if not sub_btn.is_dragging:
                            if current_x + self.button_width > available_width - self.spacing:
                                current_y += self.button_height + self.spacing
                                current_x = start_x
                            sub_btn.move(current_x, current_y)
                            current_x += button_width_with_spacing
                    
                    # 子按钮布局完成后，后续按钮从新的一行开始
                    current_y += self.button_height + self.spacing
                    current_x = start_x
                    
                    # 更新文件夹背景框
                    update_folder_background(self, btn)
                else:
                    # 普通按钮，继续在当前行
                    current_x += button_width_with_spacing
        
        # 在所有按钮位置更新后，再次更新所有文件夹背景框
        update_all_folder_backgrounds(self, self.button_width, self.button_height)

    def check_button_proximity(self, dragged_button):
        """检查拖动的主界面按钮是否与其他主界面按钮靠近"""
        if dragged_button.is_sub_button:
            return
        
        # 如果拖动的是文件夹按钮，不允许与其他按钮合并
        if dragged_button.is_folder:
            self.hide_frame()
            self.proximity_pair = None
            return
            
        closest_button = None
        min_distance = float('inf')
        for btn in self.buttons:
            if btn != dragged_button and not btn.is_sub_button:
                distance = calculate_button_distance(dragged_button, btn, self.button_width, self.button_height)
                if distance < min_distance:
                    min_distance = distance
                    closest_button = btn
        if min_distance < self.proximity_threshold:
            self.show_frame(dragged_button, closest_button)
            self.proximity_pair = (dragged_button, closest_button)
        else:
            self.hide_frame()
            self.proximity_pair = None
            
    def show_frame(self, btn1, btn2):
        """显示合并提示框"""
        left = min(btn1.x(), btn2.x()) - 10
        top = min(btn1.y(), btn2.y()) - 10
        right = max(btn1.x() + self.button_width, btn2.x() + self.button_width) + 10
        bottom = max(btn1.y() + self.button_height, btn2.y() + self.button_height) + 10
        self.frame.setGeometry(left, top, right - left, bottom - top)
        self.frame.show()
        self.frame_visible = True

    def hide_frame(self):
        """隐藏合并提示框"""
        self.frame.hide()
        self.frame_visible = False

    def show_red_removal_frame(self, parent_folder):
        """显示红色虚线框，包围文件夹按钮及其所有子按钮"""
        min_x, min_y, max_x, max_y = calculate_folder_area(parent_folder, parent_folder.sub_buttons, 
                                                         self.button_width, self.button_height)
        margin = 10
        left = min_x - margin
        top = min_y - margin
        right = max_x + margin
        bottom = max_y + margin
        self.red_removal_frame.setGeometry(left, top, right - left, bottom - top)
        self.red_removal_frame.show()

    def hide_red_removal_frame(self):
        """隐藏红色虚线框"""
        self.red_removal_frame.hide()

    def show_blue_reorder_frame(self, parent_folder):
        """显示蓝色虚线框，标识文件夹内重排序范围"""
        min_x, min_y, max_x, max_y = calculate_folder_area(parent_folder, parent_folder.sub_buttons, 
                                                         self.button_width, self.button_height)
        margin = 10
        left = min_x - margin
        top = min_y - margin
        right = max_x + margin
        bottom = max_y + margin
        self.blue_reorder_frame.setGeometry(left, top, right - left, bottom - top)
        self.blue_reorder_frame.show()

    def hide_blue_reorder_frame(self):
        """隐藏蓝色虚线框"""
        self.blue_reorder_frame.hide()

    def is_button_in_frame(self, button):
        """检查按钮是否在框架内"""
        if not self.frame_visible:
            return False
        return is_button_in_frame(button, self.frame)

    # 在 merge_folders 方法中添加背景框更新
    
    def merge_folders(self):
        """合并两个主界面按钮为一个文件夹，或将按钮添加到现有文件夹"""
        if not self.proximity_pair:
            return
        btn1, btn2 = self.proximity_pair
    
        # 确保文件夹按钮不能与其他按钮合并成新文件夹
        # 只允许将普通按钮添加到现有文件夹
        if btn2.is_folder:  # 拖动普通按钮到文件夹
            if not btn1.is_folder:  # 确保btn1不是文件夹
                print(f"将按钮 {btn1.text()} 添加到现有文件夹 {btn2.text()}")
                sub_btn = add_button_to_folder(btn1, btn2, self.central_widget, self)
                self.buttons.remove(btn1)
                btn1.hide()
                if not btn2.is_expanded and self.edit_mode:
                    self.toggle_folder(btn2)  # 展开文件夹以显示新子按钮
                elif btn2.is_expanded:
                    self.update_button_positions()
                else:
                    self.update_button_positions()
                if self.edit_mode:
                    sub_btn.start_jitter()
        elif btn1.is_folder:  # 拖动普通按钮到文件夹
            if not btn2.is_folder:  # 确保btn2不是文件夹
                print(f"将按钮 {btn2.text()} 添加到现有文件夹 {btn1.text()}")
                sub_btn = add_button_to_folder(btn2, btn1, self.central_widget, self)
                self.buttons.remove(btn2)
                btn2.hide()
                if not btn1.is_expanded and self.edit_mode:
                    self.toggle_folder(btn1)  # 展开文件夹以显示新子按钮
                elif btn1.is_expanded:
                    self.update_button_positions()
                else:
                    self.update_button_positions()
                if self.edit_mode:
                    sub_btn.start_jitter()
        else:
            # 两个普通按钮合并为新文件夹
            print(f"合并按钮 {btn1.text()} 和 {btn2.text()} 创建新文件夹")
            folder_button = merge_buttons_to_folder(btn1, btn2, self.central_widget, self)
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

    def toggle_folder(self, folder_button):
        """
        切换文件夹展开 / 折叠状态。
        —— 所有动画（子按钮、背景框、其他按钮）统一并行，避免分阶段卡顿。
        """
        from PySide6.QtCore import QPoint, QRect, QPropertyAnimation, QParallelAnimationGroup, QEasingCurve
        from Folder_UI.animations import create_folder_toggle_animation, create_button_position_animation
        from Folder_UI.folder_background import FolderBackground
        from PySide6.QtWidgets import QGraphicsOpacityEffect

        if not folder_button.is_folder:
            return

        # 动画进行中则不重复触发
        running = getattr(folder_button, "folder_animation_group", None)
        if running and running.state() == QParallelAnimationGroup.Running:
            return

        is_expanding = not folder_button.is_expanded
        folder_button.is_expanded = is_expanding

        # ------- 确保背景框存在并在最底层 -------
        for btn in self.buttons:
            if btn.is_folder and (btn.is_expanded or btn is folder_button):
                if not hasattr(btn, "background_frame"):
                    btn.background_frame = FolderBackground(self.scroll_content)
                    eff = QGraphicsOpacityEffect(btn.background_frame)
                    eff.setOpacity(1.0)
                    btn.background_frame.setGraphicsEffect(eff)
                btn.background_frame.lower()
                btn.background_frame.show()

        # 展开前需显示子按钮
        if is_expanding:
            for sub in folder_button.sub_buttons:
                sub.show()

        # ------- 计算所有按钮最终位置 -------
        final_pos = {}
        bw, bh, sp = self.button_width, self.button_height, self.spacing
        avail_w = self.scroll_content.width() or self.scroll_area.viewport().width()
        x, y = sp, sp + 40

        for btn in self.buttons:
            if x + bw > avail_w - sp:
                y += bh + sp
                x = sp

            final_pos[btn] = QPoint(x, y)

            if btn.is_folder and (btn.is_expanded or (btn is folder_button and is_expanding)):
                y += bh + sp
                x = sp
                fsp = sp * 1.5
                per_row = max(1, int((avail_w - fsp * 2) // (bw + fsp)))
                for idx, sub in enumerate(btn.sub_buttons):
                    if idx and idx % per_row == 0:
                        y += bh + fsp
                        x = sp
                    final_pos[sub] = QPoint(x, y)
                    x += bw + fsp
                if x != sp:
                    y += bh + sp
                    x = sp
            else:
                x += bw + sp

        # “新建单词册”按钮目标
        if x + bw > avail_w - sp:
            y += bh + sp
            x = sp
        new_book_target = QPoint(x, y)

        # ------- 子按钮动画 -------
        sub_targets = [final_pos[s] for s in folder_button.sub_buttons if s in final_pos]
        folder_toggle_anim = create_folder_toggle_animation(folder_button, sub_targets, bw, bh, sp)

        # ------- 背景框动画 -------
        def calc_rect(positions):
            if not positions:
                return folder_button.geometry()
            min_x = min(p.x() for p in positions)
            min_y = min(p.y() for p in positions)
            max_x = max(p.x() for p in positions) + bw
            max_y = max(p.y() for p in positions) + bh
            margin = sp // 2
            return QRect(min_x - margin, min_y - margin,
                         max_x - min_x + margin * 2, max_y - min_y + margin * 2)

        bg_frame = folder_button.background_frame
        bg_eff = bg_frame.graphicsEffect()  # type: QGraphicsOpacityEffect
        if is_expanding:
            bg_start = folder_button.geometry()
            bg_end = calc_rect(sub_targets)
        else:
            bg_start = bg_frame.geometry()
            bg_end = folder_button.geometry()

        bg_geom_anim = QPropertyAnimation(bg_frame, b"geometry")
        bg_geom_anim.setDuration(450)
        bg_geom_anim.setEasingCurve(QEasingCurve.OutBack if is_expanding else QEasingCurve.InBack)
        bg_geom_anim.setStartValue(bg_start)
        bg_geom_anim.setEndValue(bg_end)

        bg_opacity_anim = QPropertyAnimation(bg_eff, b"opacity")
        bg_opacity_anim.setDuration(450)
        if is_expanding:
            bg_opacity_anim.setStartValue(0.0 if bg_eff.opacity() < 1e-3 else bg_eff.opacity())
            bg_opacity_anim.setEndValue(1.0)
        else:
            bg_opacity_anim.setStartValue(bg_eff.opacity())
            bg_opacity_anim.setEndValue(0.0)
            bg_opacity_anim.finished.connect(lambda: (bg_frame.hide(), bg_eff.setOpacity(1.0)))

        # ------- 其他按钮 & 新建按钮动画 -------
        move_group = QParallelAnimationGroup()
        for btn, tgt in final_pos.items():
            if btn not in folder_button.sub_buttons and btn is not folder_button and not getattr(btn, "is_dragging",
                                                                                                 False):
                move_group.addAnimation(create_button_position_animation(btn, tgt, 450))
        if self.new_book_button.pos() != new_book_target:
            move_group.addAnimation(create_button_position_animation(self.new_book_button, new_book_target, 450))

        # ------- 其他已展开文件夹背景框几何动画 -------
        other_bg_anims = QParallelAnimationGroup()
        for btn in self.buttons:
            if btn.is_folder and btn.is_expanded and btn is not folder_button:
                tgt_rect = calc_rect([final_pos[s] for s in btn.sub_buttons])
                if tgt_rect != btn.background_frame.geometry():
                    anim = QPropertyAnimation(btn.background_frame, b"geometry")
                    anim.setDuration(450)
                    anim.setEasingCurve(QEasingCurve.OutBack)
                    anim.setStartValue(btn.background_frame.geometry())
                    anim.setEndValue(tgt_rect)
                    other_bg_anims.addAnimation(anim)

        # ------- 汇总并启动 -------
        master = QParallelAnimationGroup()
        master.addAnimation(folder_toggle_anim)
        master.addAnimation(bg_geom_anim)
        master.addAnimation(bg_opacity_anim)
        master.addAnimation(move_group)
        master.addAnimation(other_bg_anims)

        master.finished.connect(lambda: self.post_animation_update(folder_button))
        folder_button.folder_animation_group = master
        master.start()

    def post_animation_update(self, folder_button):
        """动画结束后的更新操作"""
        self.update_button_positions()
        # 如果是关闭操作，隐藏子按钮
        if not folder_button.is_expanded:
            for sub_btn in folder_button.sub_buttons:
                sub_btn.hide()

    def update_button_order(self, dragged_button):
        """更新主界面按钮顺序"""
        # 移除这个条件，允许文件夹按钮参与重排序，无论是否展开
        # if dragged_button.is_folder and dragged_button.is_expanded:
        #     return
        other_buttons = [btn for btn in self.buttons if btn != dragged_button and not btn.is_sub_button]
        target_positions = calculate_main_button_positions(self.buttons, self.button_width, self.button_height, 
                                                         self.spacing, self.central_widget.width())
    
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
        """实时更新主界面按钮位置（不使用动画）"""
        target_positions = calculate_main_button_positions(self.buttons, self.button_width, self.button_height, 
                                                         self.spacing, self.central_widget.width())
        main_buttons = [btn for btn in self.buttons if not btn.is_sub_button]
        for i, btn in enumerate(main_buttons):
            if i < len(target_positions) and btn != dragged_button and not btn.is_dragging:
                btn.move(target_positions[i])

    # 在 finalize_button_order 方法中添加背景框更新
    
    def finalize_button_order(self):
        """使用动画方式更新主界面按钮位置（松手后保存排序）"""
        target_positions = calculate_main_button_positions(self.buttons, self.button_width, self.button_height, 
                                                         self.spacing, self.central_widget.width())
        main_buttons = [btn for btn in self.buttons if not btn.is_sub_button]
        animation_group = QParallelAnimationGroup()
        for i, btn in enumerate(main_buttons):
            if i < len(target_positions) and btn.pos() != target_positions[i]:
                animation = create_button_position_animation(btn, target_positions[i])
                animation_group.addAnimation(animation)
        animation_group.start()
        self.update_button_positions()

    def update_sub_button_order(self, folder_button, dragged_sub_button=None, realtime=False):
        """改进版：子按钮实时吸附排序（像主按钮那样灵敏）"""
        from Folder_UI.layout import calculate_sub_button_positions
        target_positions = calculate_sub_button_positions(
            folder_button, self.button_width, self.button_height,
            self.spacing, self.central_widget.width(), self.folder_extra_width
        )

        if dragged_sub_button:
            dragged_center = QPoint(
                dragged_sub_button.x() + self.button_width // 2,
                dragged_sub_button.y() + self.button_height // 2
            )
            min_distance = float('inf')
            closest_index = 0
            for i, target_pos in enumerate(target_positions):
                target_center = QPoint(
                    target_pos.x() + self.button_width // 2,
                    target_pos.y() + self.button_height // 2
                )
                dist = (dragged_center - target_center).manhattanLength()
                if dist < min_distance:
                    min_distance = dist
                    closest_index = i

            # 重建子按钮列表
            sub_buttons = [btn for btn in folder_button.sub_buttons if btn != dragged_sub_button]
            new_sub_buttons = []
            iter_other = iter(sub_buttons)
            for idx in range(len(folder_button.sub_buttons)):
                if idx == closest_index:
                    new_sub_buttons.append(dragged_sub_button)
                else:
                    try:
                        new_sub_buttons.append(next(iter_other))
                    except StopIteration:
                        pass
            folder_button.sub_buttons = new_sub_buttons

        if realtime:
            self.finalize_sub_button_order(folder_button, dragged_button=dragged_sub_button)
        else:
            self.finalize_sub_button_order(folder_button, dragged_button=dragged_sub_button)

    def finalize_sub_button_order(self, folder_button, dragged_button=None):
        """使用动画方式更新子按钮位置（松手后保存排序）"""
        target_positions = calculate_sub_button_positions(folder_button, self.button_width, self.button_height, 
                                                        self.spacing, self.central_widget.width(), self.folder_extra_width)
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
        target_positions = calculate_sub_button_positions(folder_button, self.button_width, self.button_height, 
                                                        self.spacing, self.central_widget.width(), self.folder_extra_width)
        for i, btn in enumerate(folder_button.sub_buttons):
            if i < len(target_positions) and btn != dragged_button and not btn.is_dragging:
                btn.move(target_positions[i])
        # 实时更新背景框
        update_folder_background(self, folder_button)

    def remove_sub_button_from_folder(self, sub_btn):
        """从文件夹中移除子按钮"""
        parent_folder = remove_sub_button_from_folder(sub_btn, self.buttons)
        if parent_folder:
            if self.edit_mode:
                sub_btn.start_jitter()
            self.update_button_positions()
            check_and_remove_folder_if_needed(parent_folder, self.buttons)
            self.update_button_positions()

    def collapse_all_folders(self):
        """保存所有文件夹的展开状态，并折叠所有文件夹按钮"""
        # 清空之前的状态记录
        self.folder_expanded_states.clear()
    
        # 记录当前所有文件夹的展开状态
        for btn in self.buttons:
            if btn.is_folder and btn.is_expanded:
                self.folder_expanded_states[btn] = True
    
                # 创建折叠动画
                if not btn.folder_animation_group or btn.folder_animation_group.state() != QParallelAnimationGroup.Running:
                    # 设置状态为折叠
                    btn.is_expanded = False
    
                    # 创建折叠动画
                    sub_button_positions = [sub_btn.pos() for sub_btn in btn.sub_buttons]
                    folder_toggle_anim = create_folder_toggle_animation(btn, sub_button_positions,
                                                                        self.button_width, self.button_height,
                                                                        self.spacing)
    
                    # 动画结束后隐藏子按钮
                    folder_toggle_anim.finished.connect(lambda b=btn: self.post_animation_update(b))
    
                    # 启动动画
                    btn.folder_animation_group = folder_toggle_anim
                    folder_toggle_anim.start()
    
        self.all_folders_collapsed = True
    
    def expand_all_folders(self):
        """恢复之前展开的文件夹状态"""
        if not self.all_folders_collapsed:
            return
            
        # 恢复之前展开的文件夹
        for btn, was_expanded in self.folder_expanded_states.items():
            if was_expanded and not btn.is_expanded:
                # 创建展开动画
                if not btn.folder_animation_group or btn.folder_animation_group.state() != QParallelAnimationGroup.Running:
                    # 设置状态为展开
                    btn.is_expanded = True
                    
                    # 先显示子按钮，以便动画可见
                    for sub_btn in btn.sub_buttons:
                        sub_btn.show()
                        
                    # 计算子按钮的目标位置
                    target_positions = calculate_sub_button_positions(btn, self.button_width, self.button_height, 
                                                                    self.spacing, self.central_widget.width(), 
                                                                    self.folder_extra_width)
                    
                    # 创建展开动画
                    folder_toggle_anim = create_folder_toggle_animation(btn, target_positions,
                                                                       self.button_width, self.button_height,
                                                                       self.spacing)
                    
                    # 启动动画
                    btn.folder_animation_group = folder_toggle_anim
                    folder_toggle_anim.start()
        
        # 清空状态记录
        self.folder_expanded_states.clear()
        self.all_folders_collapsed = False
        
        # 添加这一行，确保在所有文件夹展开后更新所有按钮的位置
        self.update_button_positions()