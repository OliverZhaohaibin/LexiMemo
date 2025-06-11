# ui/folder_ui/_layout.py开始
from PySide6.QtCore import QPoint, QRect, QParallelAnimationGroup  # Moved QParallelAnimationGroup here for broader use
from typing import List, TYPE_CHECKING, Optional

if TYPE_CHECKING:
    from ui.word_book_button import WordBookButton  # Or your specific button class


def calculate_main_button_positions(
        buttons: List['WordBookButton'],
        button_width: int,
        button_height: int,
        spacing: int,
        central_widget_width: int,
        top_margin: int = 40  # Added top_margin for flexibility
) -> List[QPoint]:
    """
    计算主界面按钮的位置
    """
    target_positions = []
    current_x = spacing
    current_y = spacing + top_margin

    main_buttons_for_layout = [btn for btn in buttons if
                               not btn.is_sub_button and not getattr(btn, 'is_new_button', False)]

    buttons_per_row = max(1, (central_widget_width - spacing) // (button_width + spacing))

    idx = 0
    for btn in buttons:
        if btn.is_sub_button or getattr(btn, 'is_new_button', False):
            continue

        if idx > 0 and idx % buttons_per_row == 0:
            current_y += button_height + spacing
            current_x = spacing

        target_positions.append(QPoint(current_x, current_y))
        current_x += button_width + spacing
        idx += 1

    return target_positions


def calculate_sub_button_positions(
        folder_button: 'WordBookButton',
        button_width: int,
        button_height: int,
        spacing: int,
        central_widget_width: int,
        folder_extra_width: int
) -> List[QPoint]:
    """
    计算文件夹内子按钮的位置.
    """
    target_positions = []
    if not folder_button.sub_buttons:
        return target_positions

    folder_internal_spacing = spacing * 1.5

    start_y_for_subs = folder_button.y() + button_height + spacing

    current_x = folder_internal_spacing
    current_y = start_y_for_subs

    sub_buttons_per_row = max(1, int((central_widget_width - folder_internal_spacing) // (
                button_width + folder_internal_spacing)))

    for idx, sub_btn in enumerate(folder_button.sub_buttons):
        if idx > 0 and idx % sub_buttons_per_row == 0:
            current_y += button_height + folder_internal_spacing
            current_x = folder_internal_spacing

        target_positions.append(QPoint(current_x, current_y))
        current_x += button_width + folder_internal_spacing

    return target_positions


def calculate_folder_area(
        folder_button: 'WordBookButton',
        sub_buttons: List['WordBookButton'],
        button_width: int,
        button_height: int
) -> tuple[int, int, int, int]:
    """
    计算文件夹区域（只包括传入的子按钮, 不包括文件夹按钮本身,除非sub_buttons为空）
    """
    if not sub_buttons:
        min_x = folder_button.x()
        min_y = folder_button.y()
        max_x = folder_button.x() + button_width
        max_y = folder_button.y() + button_height
        return min_x, min_y, max_x, max_y

    min_x = min(btn.x() for btn in sub_buttons)
    min_y = min(btn.y() for btn in sub_buttons)
    max_x = max(btn.x() + button_width for btn in sub_buttons)
    max_y = max(btn.y() + button_height for btn in sub_buttons)

    return min_x, min_y, max_x, max_y


def calculate_reorder_area(
        folder_button: 'WordBookButton',
        button_width: int,
        button_height: int,
        spacing: int,
        central_widget_width: int,
        folder_extra_width: int
) -> QRect:
    """
    计算文件夹内重排序区域.
    """
    if not folder_button.sub_buttons:
        left = 0
        top = folder_button.y() + button_height + spacing
        width = central_widget_width
        height = button_height + spacing
        return QRect(left, top, int(width), int(height))

    folder_internal_spacing = spacing * 1.5

    min_y_sub = min(btn.y() for btn in folder_button.sub_buttons)
    max_y_sub = max(btn.y() + button_height for btn in folder_button.sub_buttons)

    left = 0
    top = min_y_sub - folder_internal_spacing / 2
    width = central_widget_width
    height = (max_y_sub - min_y_sub) + folder_internal_spacing

    return QRect(left, int(top), int(width), int(height))


class FolderLayoutMixin:
    """
    把『按钮网格布局 / 拖拽排序』相关算法统一放到这里。
    """

    def update_button_positions(self) -> None:
        """
        Re-compute the geometry of every main WordBookButton *and* the
        ``new_book_button`` inside ``scroll_content``.

        · 如果 self.buttons 为空，也会为 new_book_button 计算位置，
          使首次启动 / 全删光单词本时仍能看到 ui 元素。
        · 布局规则与旧版一致：从左上开始按行排，自动换行。
        """
        # ---------- 0) 基本健壮性检查 ----------
        if not hasattr(self, "buttons"):
            return  # 组件初始化异常才早退

        available_width = (
                self.scroll_content.width()
                or self.scroll_area.viewport().width()
        )
        bw, bh, sp = self.button_width, self.button_height, self.spacing
        top_margin = getattr(self, "top_margin", 40)

        current_x = sp
        current_y = sp + top_margin
        buttons_per_row = max(1, (available_width - sp) // (bw + sp))

        # ---------- 1) 布局主按钮 ----------
        for idx, btn in enumerate(self.buttons):
            if idx and idx % buttons_per_row == 0:  # 换行
                current_x = sp
                current_y += bh + sp

            btn.move(current_x, current_y)
            current_x += bw + sp

        # ---------- 2) 布局「新建单词本」按钮（始终可见） ----------
        if hasattr(self, "new_book_button"):
            if not self.buttons:  # 没任何主按钮
                current_x, current_y = sp, sp + top_margin
            elif current_x + bw > available_width - sp:  # 当前行放不下
                current_x = sp
                current_y += bh + sp

            self.new_book_button.move(current_x, current_y)

        # ---------- 3) 更新 scroll_content 的最小尺寸 ----------
        total_items = len(self.buttons) + (1 if hasattr(self, "new_book_button") else 0)
        rows = (total_items + buttons_per_row - 1) // buttons_per_row
        min_h = top_margin + rows * (bh + sp) + sp
        self.scroll_content.setMinimumSize(available_width, min_h)

    def update_button_order(self, dragged_button: 'WordBookButton'):
        if dragged_button.is_sub_button or not hasattr(self, "buttons"):
            return

        other_buttons = [b for b in self.buttons if b is not dragged_button and not getattr(b, 'is_new_button', False)]

        all_main_buttons = [b for b in self.buttons if not b.is_sub_button and not getattr(b, 'is_new_button', False)]

        targets = calculate_main_button_positions(
            all_main_buttons, self.button_width, self.button_height,
            self.spacing, self.scroll_content.width(), getattr(self, "top_margin", 40)
        )
        if not targets: return

        dragged_center = dragged_button.pos() + QPoint(self.button_width // 2, self.button_height // 2)

        closest_slot_index = 0
        min_dist = float('inf')

        num_slots = len(all_main_buttons)

        for i in range(num_slots):
            slot_pos = targets[i] if i < len(targets) else targets[-1]
            slot_center = slot_pos + QPoint(self.button_width // 2, self.button_height // 2)
            dist = (dragged_center - slot_center).manhattanLength()
            if dist < min_dist:
                min_dist = dist
                closest_slot_index = i

        if dragged_button in self.buttons:
            self.buttons.remove(dragged_button)

        current_main_buttons = [b for b in self.buttons if
                                not b.is_sub_button and not getattr(b, 'is_new_button', False)]

        new_main_buttons_order = []
        other_iter = iter(current_main_buttons)

        for i in range(len(current_main_buttons) + 1):
            if i == closest_slot_index:
                new_main_buttons_order.append(dragged_button)
            else:
                try:
                    new_main_buttons_order.append(next(other_iter))
                except StopIteration:
                    break

        self.buttons = new_main_buttons_order

        self.animate_button_positions(dragged_button)

    def animate_button_positions(self, dragged_button: Optional['WordBookButton'] = None):
        all_main_buttons = [b for b in self.buttons if not b.is_sub_button and not getattr(b, 'is_new_button', False)]

        targets = calculate_main_button_positions(
            all_main_buttons,
            self.button_width, self.button_height, self.spacing,
            self.scroll_content.width(), getattr(self, "top_margin", 40)
        )

        for i, btn in enumerate(all_main_buttons):
            if i < len(targets) and btn is not dragged_button and not getattr(btn, "is_dragging", False):
                btn.move(targets[i])

        current_x = self.spacing
        current_y = self.spacing + getattr(self, "top_margin", 40)
        available_width = self.scroll_content.width() or self.scroll_area.viewport().width()
        bw, bh, sp = self.button_width, self.button_height, self.spacing
        buttons_per_row = max(1, (available_width - sp) // (bw + sp))

        num_main_items = len(all_main_buttons)

        final_row_idx = (num_main_items - 1) // buttons_per_row if num_main_items > 0 else -1
        final_col_idx = (num_main_items - 1) % buttons_per_row if num_main_items > 0 else -1

        current_y += final_row_idx * (bh + sp) if final_row_idx >= 0 else 0
        current_x += (final_col_idx + 1) * (bw + sp) if final_col_idx >= 0 else 0

        if hasattr(self, 'new_book_button'):
            if num_main_items == 0:
                current_x = sp
                current_y = sp + getattr(self, "top_margin", 40)
            elif current_x + bw > available_width - sp:
                current_y += bh + sp
                current_x = sp

            if not getattr(self.new_book_button, "is_dragging", False) and \
                    self.new_book_button.pos() != QPoint(current_x, current_y):
                from ._animations import create_button_position_animation
                anim = create_button_position_animation(self.new_book_button, QPoint(current_x, current_y),
                                                        duration=100)
                anim.start()

    def finalize_button_order(self):
        all_main_buttons = [b for b in self.buttons if not b.is_sub_button and not getattr(b, 'is_new_button', False)]

        targets = calculate_main_button_positions(
            all_main_buttons, self.button_width, self.button_height,
            self.spacing, self.scroll_content.width(), getattr(self, "top_margin", 40)
        )

        # QParallelAnimationGroup imported at the top of the file now
        from ._animations import create_button_position_animation

        anim_group = QParallelAnimationGroup(self)
        for i, btn in enumerate(all_main_buttons):
            if i < len(targets) and btn.pos() != targets[i]:
                anim = create_button_position_animation(btn, targets[i], duration=300)
                anim_group.addAnimation(anim)

        if hasattr(self, 'new_book_button'):
            current_x = self.spacing
            current_y = self.spacing + getattr(self, "top_margin", 40)
            available_width = self.scroll_content.width() or self.scroll_area.viewport().width()
            bw, bh, sp = self.button_width, self.button_height, self.spacing
            buttons_per_row = max(1, (available_width - sp) // (bw + sp))

            num_main_items = len(all_main_buttons)
            final_row_idx = (num_main_items - 1) // buttons_per_row if num_main_items > 0 else -1
            final_col_idx = (num_main_items - 1) % buttons_per_row if num_main_items > 0 else -1

            current_y += final_row_idx * (bh + sp) if final_row_idx >= 0 else 0
            current_x += (final_col_idx + 1) * (bw + sp) if final_col_idx >= 0 else 0

            if num_main_items == 0:
                current_x = sp
                current_y = sp + getattr(self, "top_margin", 40)
            elif current_x + bw > available_width - sp:
                current_y += bh + sp
                current_x = sp

            new_book_final_pos = QPoint(current_x, current_y)
            if self.new_book_button.pos() != new_book_final_pos:
                anim = create_button_position_animation(self.new_book_button, new_book_final_pos, duration=300)
                anim_group.addAnimation(anim)

        anim_group.finished.connect(self.update_button_positions)
        anim_group.start()

    def update_sub_button_order(self, folder_button: 'WordBookButton',
                                dragged_sub_button: Optional['WordBookButton'] = None, realtime: bool = False):
        targets = calculate_sub_button_positions(
            folder_button, self.button_width, self.button_height,
            self.spacing, self.scroll_content.width(),
            getattr(self, 'folder_extra_width', 0)
        )

        if dragged_sub_button:
            d_center = dragged_sub_button.pos() + QPoint(self.button_width // 2, self.button_height // 2)

            closest_idx = 0
            if targets:
                closest_idx = min(
                    range(len(targets)),
                    key=lambda i: (targets[i] + QPoint(self.button_width // 2,
                                                       self.button_height // 2) - d_center).manhattanLength()
                )

            if dragged_sub_button in folder_button.sub_buttons:
                folder_button.sub_buttons.remove(dragged_sub_button)

            new_sub_order = folder_button.sub_buttons[:]
            new_sub_order.insert(closest_idx, dragged_sub_button)
            folder_button.sub_buttons = new_sub_order

        if realtime:
            self.finalize_sub_button_order_realtime(folder_button, dragged_button=dragged_sub_button)
        else:
            self.finalize_sub_button_order(folder_button, dragged_button=dragged_sub_button)

    def finalize_sub_button_order_realtime(self, folder_button: 'WordBookButton',
                                           dragged_button: Optional['WordBookButton'] = None):
        targets = calculate_sub_button_positions(
            folder_button, self.button_width, self.button_height, self.spacing,
            self.scroll_content.width(), getattr(self, 'folder_extra_width', 0)
        )

        for i, btn in enumerate(folder_button.sub_buttons):
            if i < len(targets) and btn is not dragged_button and not getattr(btn, "is_dragging", False):
                btn.move(targets[i])

        from ._background import update_folder_background
        update_folder_background(self, folder_button)

    def finalize_sub_button_order(self, folder_button: 'WordBookButton',
                                  dragged_button: Optional['WordBookButton'] = None):
        targets = calculate_sub_button_positions(
            folder_button, self.button_width, self.button_height, self.spacing,
            self.scroll_content.width(), getattr(self, 'folder_extra_width', 0)
        )

        # QParallelAnimationGroup imported at the top of the file now
        from ._animations import create_button_position_animation

        anim_group = QParallelAnimationGroup(self)
        for i, btn in enumerate(folder_button.sub_buttons):
            if i < len(targets) and btn is not dragged_button and not getattr(btn, "is_dragging",
                                                                              False) and btn.pos() != targets[i]:
                anim = create_button_position_animation(btn, targets[i], duration=300)
                anim_group.addAnimation(anim)

        from ._background import update_folder_background
        anim_group.finished.connect(lambda: update_folder_background(self, folder_button))
        anim_group.start()


__all__ = [
    "FolderLayoutMixin",
    "calculate_main_button_positions",
    "calculate_sub_button_positions",
    "calculate_folder_area",
    "calculate_reorder_area",
]
# ui/folder_ui/_layout.py结束