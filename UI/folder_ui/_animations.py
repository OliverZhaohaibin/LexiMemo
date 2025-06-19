# UI/folder_ui/_animations.py开始
from PySide6.QtCore import QPropertyAnimation, QParallelAnimationGroup, QEasingCurve, QPoint, QRect, QTimer
from PySide6.QtWidgets import QGraphicsOpacityEffect
from typing import Dict, List  # Import Dict and List

# Import necessary components from sibling _modules
from ._background import FolderBackground  # update_folder_background is called by update_button_positions


def create_folder_toggle_animation(folder_button, target_positions: List[QPoint], button_width, button_height,
                                   spacing):
    """
    创建文件夹展开/关闭的动画

    Args:
        folder_button: 文件夹按钮 (WordBookButton instance)
        target_positions: 子按钮目标位置列表 (for expansion)
        button_width: 按钮宽度
        button_height: 按钮高度
        spacing: 间距

    Returns:
        动画组
    """
    master_anim_group = QParallelAnimationGroup()

    # folder_button.is_expanded has been set to the *target* state before calling this
    is_expanding = folder_button.is_expanded
    duration_base = 450 if is_expanding else 250
    duration_increment = 100 if is_expanding else 40

    for index, sub_btn in enumerate(folder_button.sub_buttons):
        if is_expanding:
            sub_btn.show()  # Must be visible for animation
            sub_btn.setWindowOpacity(0)  # Start transparent for fade-in
            start_pos = folder_button.pos()
            end_pos = target_positions[index] if index < len(target_positions) else folder_button.pos()
        else:  # Collapsing
            start_pos = sub_btn.pos()
            end_pos = folder_button.pos()

        pos_anim = QPropertyAnimation(sub_btn, b"pos")
        pos_anim.setDuration(duration_base + index * duration_increment)
        pos_anim.setStartValue(start_pos)
        pos_anim.setEndValue(end_pos)
        pos_anim.setEasingCurve(QEasingCurve.OutBack if is_expanding else QEasingCurve.InBack)
        master_anim_group.addAnimation(pos_anim)

        opacity_anim = QPropertyAnimation(sub_btn, b"windowOpacity")
        opacity_anim.setDuration(duration_base - 50 if duration_base > 50 else duration_base)
        opacity_anim.setStartValue(0 if is_expanding else 1)
        opacity_anim.setEndValue(1 if is_expanding else 0)
        opacity_anim.setEasingCurve(QEasingCurve.InOutQuad)
        master_anim_group.addAnimation(opacity_anim)

    # folder_button.app is CoverContent which has _post_folder_animation from FolderAnimationMixin
    if hasattr(folder_button, 'app') and folder_button.app and hasattr(folder_button.app, '_post_folder_animation'):
        master_anim_group.finished.connect(
            lambda: folder_button.app._post_folder_animation(folder_button)
        )
    elif hasattr(folder_button, 'app') and folder_button.app and hasattr(folder_button.app, 'update_button_positions'):
        # Fallback if _post_folder_animation is not directly on app (should not happen with current structure)
        master_anim_group.finished.connect(
            folder_button.app.update_button_positions
        )

    return master_anim_group


def create_button_position_animation(button, target_pos, duration=200, easing_curve=QEasingCurve.OutBack):
    """
    创建按钮位置动画
    """
    animation = QPropertyAnimation(button, b"pos")
    animation.setDuration(duration)
    animation.setStartValue(button.pos())
    animation.setEndValue(target_pos)
    animation.setEasingCurve(easing_curve)
    return animation


class FolderAnimationMixin:
    """混入类：提供文件夹展开 / 折叠相关全部动画 & 批量折叠/恢复能力。
       Assumes self is CoverContent.
    """

    def toggle_folder(self, folder_button):
        """切换单个文件夹的展开 / 折叠状态（含动画）。"""
        if not hasattr(folder_button, "is_folder") or not folder_button.is_folder:
            return

        current_anim_group = getattr(folder_button, "folder_animation_group", None)
        if current_anim_group and current_anim_group.state() == QParallelAnimationGroup.Running:
            return

        # Determine target state and set it on the button
        target_is_expanding = not folder_button.is_expanded
        folder_button.is_expanded = target_is_expanding

        self._ensure_background_frames(folder_button)  # Ensure frame exists, show/hide handled by animation

        if target_is_expanding:
            for sub in folder_button.sub_buttons:
                sub.show()
                sub.setWindowOpacity(0)

        # Calculate final positions for ALL buttons based on the NEW state of the toggled folder
        final_pos_map, new_book_target_pos = self._calculate_final_positions(folder_button, target_is_expanding)

        sub_targets_for_current_folder = [final_pos_map[s] for s in folder_button.sub_buttons if s in final_pos_map]

        folder_toggle_anim = create_folder_toggle_animation(
            folder_button, sub_targets_for_current_folder,
            self.button_width, self.button_height, self.spacing
        )

        bg_geom_anim, bg_opacity_anim = self._build_background_anims(
            folder_button, sub_targets_for_current_folder, target_is_expanding
        )

        move_other_items_group = self._build_move_group(folder_button, final_pos_map, new_book_target_pos)
        other_folders_bg_anim_group = self._build_other_bg_group(folder_button, final_pos_map)

        master_animation_group = QParallelAnimationGroup()
        master_animation_group.addAnimation(folder_toggle_anim)
        master_animation_group.addAnimation(bg_geom_anim)
        master_animation_group.addAnimation(bg_opacity_anim)
        master_animation_group.addAnimation(move_other_items_group)
        master_animation_group.addAnimation(other_folders_bg_anim_group)

        # _post_folder_animation is connected by create_folder_toggle_animation's finished signal
        folder_button.folder_animation_group = master_animation_group
        master_animation_group.start()

    def collapse_all_folders(self):
        """批量折叠界面上 *所有* 已展开文件夹（并记录状态）。"""
        if not hasattr(self, 'buttons'): return

        self.folder_expanded_states: Dict = {}
        self.all_folders_collapsed = True  # Mark that a "collapse all" operation was performed

        any_folder_animated = False
        for btn in self.buttons:  # self.buttons is from CoverContent
            if hasattr(btn, 'is_folder') and btn.is_folder and \
                    hasattr(btn, 'is_expanded') and btn.is_expanded:

                self.folder_expanded_states[btn] = True  # Record it was expanded

                current_anim_group = getattr(btn, "folder_animation_group", None)
                if not current_anim_group or current_anim_group.state() != QParallelAnimationGroup.Running:
                    btn.is_expanded = False  # CRITICAL: Set state BEFORE creating animation

                    anim = create_folder_toggle_animation(
                        btn, [], self.button_width, self.button_height, self.spacing
                    )
                    btn.folder_animation_group = anim
                    anim.start()
                    any_folder_animated = True

        if not any_folder_animated and hasattr(self, 'update_button_positions'):
            # If no folders were actually collapsed (e.g., all were already closed),
            # still trigger a layout update to ensure consistency, especially if exiting edit mode.
            QTimer.singleShot(0, self.update_button_positions)

    def expand_all_folders(self):
        """恢复上一次 `collapse_all_folders` 保存的展开状态。"""
        if not hasattr(self, 'buttons'):
            return

        # Only proceed if a "collapse all" op was done and states were saved & not empty
        if not getattr(self, "all_folders_collapsed", False) or \
                not hasattr(self, "folder_expanded_states") or \
                not self.folder_expanded_states:
            if hasattr(self, 'update_button_positions'):
                QTimer.singleShot(0, self.update_button_positions)  # Ensure layout is current
            return

        any_folder_animated = False
        needs_retry = False
        for btn_from_state, was_expanded in self.folder_expanded_states.items():
            # Check if button still exists in the current list of buttons on CoverContent
            if btn_from_state not in self.buttons:
                continue

            # Ensure we are targeting a folder that was marked as expanded and is currently not
            if was_expanded and hasattr(btn_from_state, 'is_folder') and btn_from_state.is_folder and \
                    hasattr(btn_from_state, 'is_expanded') and not btn_from_state.is_expanded:

                current_anim_group = getattr(btn_from_state, "folder_animation_group", None)
                if not current_anim_group or current_anim_group.state() != QParallelAnimationGroup.Running:
                    btn_from_state.is_expanded = True  # Set target state to expanding

                    for sub in btn_from_state.sub_buttons:
                        sub.show()
                        sub.setWindowOpacity(0)

                    # Calculate target positions for sub-buttons for this specific folder's expansion
                    final_pos_map, _ = self._calculate_final_positions(btn_from_state,
                                                                       True)  # True for is_expanding_current_folder
                    target_positions_for_subs = [final_pos_map[s] for s in btn_from_state.sub_buttons if
                                                 s in final_pos_map]

                    anim = create_folder_toggle_animation(
                        btn_from_state, target_positions_for_subs,
                        self.button_width, self.button_height, self.spacing
                    )
                    btn_from_state.folder_animation_group = anim
                    anim.start()
                    any_folder_animated = True
                else:
                    needs_retry = True

        if needs_retry and not any_folder_animated:
            # Collapse animations still running; try again shortly without clearing state
            if not hasattr(self, '_expand_retry_timer') or self._expand_retry_timer is None:
                self._expand_retry_timer = QTimer(self, singleShot=True)
                self._expand_retry_timer.timeout.connect(self.expand_all_folders)
            self._expand_retry_timer.start(150)
            return

        # If retry not needed, cleanup any existing timer and clear state
        if hasattr(self, '_expand_retry_timer') and self._expand_retry_timer:
            if self._expand_retry_timer.isActive():
                self._expand_retry_timer.stop()
            self._expand_retry_timer.deleteLater()
            self._expand_retry_timer = None

        self.folder_expanded_states.clear()  # Clear states after attempting expansion
        self.all_folders_collapsed = False

        # A final layout update after a delay to ensure all animations settle.
        # Individual animations also call _post_folder_animation -> update_button_positions.
        if hasattr(self, 'update_button_positions'):
            # Delay slightly more than the longest potential animation (duration_base + N*duration_increment for sub_buttons)
            # Max sub_buttons is 9. Longest collapse is 250 + 8*40 = 570. Longest expand 450 + 8*100 = 1250.
            # A generic delay for safety.
            QTimer.singleShot(600, self.update_button_positions)

    def _ensure_background_frames(self, folder_button):
        """Ensures the folder_button being toggled (and other already expanded ones)
           have a background frame widget ready. Visibility is handled by animations.
        """
        buttons_needing_frames = []
        if hasattr(self, 'buttons'):
            for btn in self.buttons:
                if hasattr(btn, 'is_folder') and btn.is_folder:
                    # If it's the button being toggled OR it's another folder that is already expanded
                    if btn is folder_button or (hasattr(btn, 'is_expanded') and btn.is_expanded):
                        buttons_needing_frames.append(btn)

        if not buttons_needing_frames and (hasattr(folder_button, 'is_folder') and folder_button.is_folder):
            buttons_needing_frames.append(folder_button)

        for btn_with_frame in buttons_needing_frames:
            if not hasattr(btn_with_frame, "background_frame") or btn_with_frame.background_frame is None:
                btn_with_frame.background_frame = FolderBackground(self.scroll_content)  # self is CoverContent
                eff = QGraphicsOpacityEffect(btn_with_frame.background_frame)
                # Opacity is set by animation, but default to 1 if not animated.
                eff.setOpacity(1.0)
                btn_with_frame.background_frame.setGraphicsEffect(eff)

            # Ensure it's visible and under other elements initially if it's being animated to show
            # Or just ensure it's there for animation. Visibility is managed by animation logic mostly.
            btn_with_frame.background_frame.lower()
            # Don't show() here; let animation control visibility. If it's expanding, opacity starts at 0.
            # If it's collapsing, it's already visible.

    def _calculate_final_positions(self, folder_button_being_toggled, is_expanding_current_folder):
        # self refers to CoverContent
        bw, bh, sp = self.button_width, self.button_height, self.spacing
        avail_w = self.scroll_content.width() or self.scroll_area.viewport().width()
        x, y = sp, sp + (getattr(self, "top_margin", 40) or 40)
        final_pos: Dict['WordBookButton', QPoint] = {}  # Use actual button type if available

        buttons_for_layout = []
        if hasattr(self, 'buttons'):
            buttons_for_layout = self.buttons

        buttons_per_row = max(1, (avail_w - sp) // (bw + sp))
        main_button_idx = 0

        for btn in buttons_for_layout:
            if getattr(btn, "is_dragging", False): continue  # Skip dragging button for calculation

            if main_button_idx > 0 and main_button_idx % buttons_per_row == 0:
                y += bh + sp
                x = sp
            final_pos[btn] = QPoint(x, y)

            # Determine if this folder (btn) will be expanded in the final layout
            is_this_folder_expanded_in_final_state = False
            if hasattr(btn, 'is_folder') and btn.is_folder:
                if btn is folder_button_being_toggled:
                    is_this_folder_expanded_in_final_state = is_expanding_current_folder
                elif hasattr(btn, 'is_expanded') and btn.is_expanded:  # Another folder that remains expanded
                    is_this_folder_expanded_in_final_state = True

            if is_this_folder_expanded_in_final_state:
                y += bh + sp  # Space for folder button itself, sub-buttons start below
                sub_x = sp  # Sub-buttons start from the left, using normal spacing for first item

                fsp = sp * 1.5  # Folder internal spacing for subsequent items in a row
                # Sub-buttons per row calculation should consider the specific layout for sub-buttons
                sub_buttons_per_row = max(1, int((avail_w - sp - (sp - fsp)) // (
                            bw + fsp)))  # Adjusted for potentially tighter packing

                for idx, sub_btn in enumerate(btn.sub_buttons):
                    if getattr(sub_btn, "is_dragging", False): continue

                    if idx > 0 and idx % sub_buttons_per_row == 0:
                        y += bh + fsp  # Move to next row for sub-buttons
                        sub_x = sp

                    final_pos[sub_btn] = QPoint(sub_x, y)
                    sub_x += (bw + fsp)

                if btn.sub_buttons:  # If there were sub-buttons, add space after them
                    y += bh + sp  # Use normal spacing after the block of sub-buttons
                x = sp  # Next main button starts from left
                main_button_idx = -1  # Reset column counter for main buttons
            else:  # Normal button or collapsed folder
                x += bw + sp

            main_button_idx += 1

        new_book_target = QPoint(0, 0)  # Default
        if hasattr(self, 'new_book_button'):
            if main_button_idx > 0 and main_button_idx % buttons_per_row == 0:
                y += bh + sp
                x = sp
            elif not buttons_for_layout:  # No main buttons, new_book_button is first
                x = sp
                y = sp + (getattr(self, "top_margin", 40) or 40)

            new_book_target = QPoint(x, y)

        return final_pos, new_book_target

    def _sub_targets(self, folder_button):  # Used by expand_all_folders
        # True because we are calculating for an expansion scenario
        final_pos_map, _ = self._calculate_final_positions(folder_button, True)
        return [final_pos_map[s] for s in folder_button.sub_buttons if s in final_pos_map]

    def _build_background_anims(self, folder_button, sub_targets, is_expanding):
        bw, bh, sp = self.button_width, self.button_height, self.spacing

        def calc_rect_for_bg(parent_folder_pos_in_final_layout, sub_button_final_positions):
            if not sub_button_final_positions:  # No sub-buttons, rect is around folder button
                return QRect(parent_folder_pos_in_final_layout.x() - sp // 2,
                             parent_folder_pos_in_final_layout.y() - sp // 2,
                             bw + sp, bh + sp)

            min_x = min((p.x() for p in sub_button_final_positions))
            min_y = min((p.y() for p in sub_button_final_positions))
            max_x = max((p.x() for p in sub_button_final_positions)) + bw
            max_y = max((p.y() for p in sub_button_final_positions)) + bh
            margin = sp // 2  # Standard margin for background
            return QRect(min_x - margin, min_y - margin, max_x - min_x + 2 * margin, max_y - min_y + 2 * margin)

        bg_frame = folder_button.background_frame
        bg_eff = bg_frame.graphicsEffect()  # type: QGraphicsOpacityEffect

        # Final position of the folder button itself from the calculated map
        folder_final_pos = self._calculate_final_positions(folder_button, is_expanding)[0].get(folder_button,
                                                                                               folder_button.pos())

        if is_expanding:
            # Start geom from folder's current position, end at rect around sub-targets
            # Opacity from 0 to 1
            bg_start_geom = QRect(folder_button.pos(), folder_button.size())  # Or folder_final_pos if it moved
            bg_end_geom = calc_rect_for_bg(folder_final_pos, sub_targets)

            bg_frame.setGeometry(bg_start_geom)  # Set initial geometry for expansion animation
            bg_frame.show()  # Make sure it's visible to animate opacity
            bg_eff.setOpacity(0.0)
        else:  # Collapsing
            # Start geom from current frame geom, end at folder's final position
            # Opacity from 1 to 0
            bg_start_geom = bg_frame.geometry()
            bg_end_geom = QRect(folder_final_pos, folder_button.size())
            # Opacity is already 1.0 if it was visible

        geom_anim = QPropertyAnimation(bg_frame, b"geometry")
        geom_anim.setDuration(450)
        geom_anim.setEasingCurve(QEasingCurve.OutBack if is_expanding else QEasingCurve.InBack)
        geom_anim.setStartValue(bg_start_geom)
        geom_anim.setEndValue(bg_end_geom)

        opac_anim = QPropertyAnimation(bg_eff, b"opacity")
        opac_anim.setDuration(350)
        opac_anim.setEasingCurve(QEasingCurve.InOutQuad)
        if is_expanding:
            opac_anim.setStartValue(0.0)
            opac_anim.setEndValue(1.0)
        else:  # Collapsing
            opac_anim.setStartValue(bg_eff.opacity())  # Current opacity
            opac_anim.setEndValue(0.0)
            # Hide frame and reset opacity after collapse animation
            opac_anim.finished.connect(lambda: (
                bg_frame.hide(),
                bg_eff.setOpacity(1.0)  # Reset for next time
            ))
        return geom_anim, opac_anim

    def _build_move_group(self, folder_button_being_toggled, final_pos_map, new_book_target_pos):
        # self refers to CoverContent
        group = QParallelAnimationGroup()

        for btn, target_pos_for_btn in final_pos_map.items():
            is_sub_of_current_toggled_folder = btn in folder_button_being_toggled.sub_buttons
            is_current_toggled_folder_itself = btn is folder_button_being_toggled

            if not is_sub_of_current_toggled_folder and \
                    not is_current_toggled_folder_itself and \
                    not getattr(btn, "is_dragging", False):
                if btn.pos() != target_pos_for_btn:
                    group.addAnimation(
                        create_button_position_animation(btn, target_pos_for_btn, 450)
                    )

        if hasattr(self, 'new_book_button') and self.new_book_button.pos() != new_book_target_pos:
            group.addAnimation(
                create_button_position_animation(self.new_book_button, new_book_target_pos, 450)
            )
        return group

    def _build_other_bg_group(self, folder_button_being_toggled, final_pos_map):
        # self refers to CoverContent
        group = QParallelAnimationGroup()
        bw, bh, sp = self.button_width, self.button_height, self.spacing

        def calc_rect_for_other_bg(parent_folder_final_pos, sub_button_final_positions):
            # Same logic as in _build_background_anims's calc_rect_for_bg
            if not sub_button_final_positions:
                return QRect(parent_folder_final_pos.x() - sp // 2, parent_folder_final_pos.y() - sp // 2, bw + sp,
                             bh + sp)
            min_x = min((p.x() for p in sub_button_final_positions))
            min_y = min((p.y() for p in sub_button_final_positions))
            max_x = max((p.x() for p in sub_button_final_positions)) + bw
            max_y = max((p.y() for p in sub_button_final_positions)) + bh
            margin = sp // 2
            return QRect(min_x - margin, min_y - margin, max_x - min_x + 2 * margin, max_y - min_y + 2 * margin)

        for btn in self.buttons:  # self.buttons from CoverContent
            if hasattr(btn, 'is_folder') and btn.is_folder and \
                    hasattr(btn, 'is_expanded') and btn.is_expanded and \
                    btn is not folder_button_being_toggled:  # Only for *other* expanded folders

                if hasattr(btn, "background_frame") and btn.background_frame is not None:
                    # Get final positions for this "other" folder and its sub-buttons
                    other_folder_final_pos = final_pos_map.get(btn, btn.pos())
                    other_folder_sub_button_final_pos = [final_pos_map[s] for s in btn.sub_buttons if
                                                         s in final_pos_map]

                    target_bg_rect = calc_rect_for_other_bg(other_folder_final_pos, other_folder_sub_button_final_pos)

                    if target_bg_rect != btn.background_frame.geometry() and not target_bg_rect.isEmpty():
                        anim = QPropertyAnimation(btn.background_frame, b"geometry")
                        anim.setDuration(450)
                        anim.setEasingCurve(QEasingCurve.OutBack)  # Consistent easing
                        anim.setStartValue(btn.background_frame.geometry())
                        anim.setEndValue(target_bg_rect)
                        group.addAnimation(anim)
        return group

    def _post_folder_animation(self, folder_button):
        """动画结束后的统一收尾。"""
        # print(f"_post_folder_animation for {folder_button.text()}, is_expanded: {folder_button.is_expanded}") # DEBUG
        if not folder_button.is_expanded:  # Collapsed
            for sub_btn in folder_button.sub_buttons:
                sub_btn.hide()
                sub_btn.setWindowOpacity(1.0)  # Reset opacity for next potential show

            if hasattr(folder_button, 'background_frame') and folder_button.background_frame:
                folder_button.background_frame.hide()
                if folder_button.background_frame.graphicsEffect():
                    folder_button.background_frame.graphicsEffect().setOpacity(1.0)  # Reset effect
        else:  # Expanded
            for sub_btn in folder_button.sub_buttons:
                sub_btn.setWindowOpacity(1.0)  # Ensure fully opaque after expansion
            if hasattr(folder_button, 'background_frame') and folder_button.background_frame:
                if folder_button.background_frame.graphicsEffect():
                    folder_button.background_frame.graphicsEffect().setOpacity(1.0)

        # Crucial: update positions for all buttons, which also updates backgrounds
        if hasattr(self, 'update_button_positions'):
            self.update_button_positions()


__all__ = [
    "FolderAnimationMixin",
    "create_folder_toggle_animation",
    "create_button_position_animation",
]
# UI/folder_ui/_animations.py结束