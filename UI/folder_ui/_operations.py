# UI/folder_ui/_operations.py开始
from __future__ import annotations
import os
import sys

from UI.word_book_button import WordBookButton  # Assuming WordBookButton is in root


# Helper functions for folder operations (adapted from original folder_ui/folder_operations.py)

def _create_sub_button_instance(
    original_button: WordBookButton,
    parent_folder:  WordBookButton,
    scroll_content,
    app_instance,
) -> WordBookButton:
    """生成文件夹中的子按钮（兼容新版 WordBookButton）。"""
    # ▶ 1) 构造——新版 ctor 仅 (title, color, parent)
    sub_btn = WordBookButton(
        original_button.text(),
        original_button.color,
        parent=scroll_content,
    )
    # ▶ 2) 恢复旧代码期望的附加属性
    sub_btn.app           = app_instance          # 被多处回调使用
    sub_btn.is_sub_button = True
    sub_btn.parent_folder = parent_folder
    sub_btn.path          = original_button.path  # 打开单词本所需
    if hasattr(app_instance, "button_width") and hasattr(app_instance, "button_height"):
        sub_btn.setFixedSize(app_instance.button_width, app_instance.button_height)

    # ▶ 3) 重新绑定点击 → CoverContent.show_word_book
    if hasattr(app_instance, "show_word_book"):
        try:
            sub_btn.clicked.disconnect()
        except Exception:
            pass
        sub_btn.clicked.connect(
            lambda _checked=False, p=sub_btn.path: app_instance.show_word_book(p)
        )

    sub_btn.hide()                                # 初始隐藏，动画/布局后再显示

    # Wire signals if controller available
    controller = getattr(app_instance, "controller", None)
    if controller and hasattr(controller, "_wire_button_signals"):
        try:
            controller._wire_button_signals(sub_btn)
        except Exception:
            pass

    return sub_btn


def _internal_add_button_to_folder(button_to_add: WordBookButton, folder: WordBookButton, scroll_content,
                                   app_instance) -> WordBookButton:
    sub_btn = _create_sub_button_instance(button_to_add, folder, scroll_content, app_instance)
    folder.sub_buttons.append(sub_btn)
    folder.update_folder_icon()

    controller = getattr(app_instance, "controller", None)
    if controller and hasattr(controller, "_wire_button_signals"):
        try:
            controller._wire_button_signals(sub_btn)
        except Exception:
            pass

    return sub_btn


def _internal_remove_sub_button_from_folder(sub_btn_to_remove: WordBookButton, main_buttons_list: list[WordBookButton]):
    parent_folder = sub_btn_to_remove.parent_folder
    if parent_folder:
        if sub_btn_to_remove in parent_folder.sub_buttons:
            parent_folder.sub_buttons.remove(sub_btn_to_remove)

        # The sub_btn_to_remove is already a WordBookButton instance.
        # It just needs its state changed and to be added to the main list.
        sub_btn_to_remove.is_sub_button = False
        sub_btn_to_remove.parent_folder = None
        # It's already parented to scroll_content, no need to re-parent.
        # Add it to the main list of buttons for layout.
        if sub_btn_to_remove not in main_buttons_list:
            # Add to a sensible position, e.g., after its ex-parent or at the end
            try:
                idx = main_buttons_list.index(parent_folder)
                main_buttons_list.insert(idx + 1, sub_btn_to_remove)
            except ValueError:
                main_buttons_list.append(sub_btn_to_remove)

        sub_btn_to_remove.show()  # Make it visible as a main button

        if hasattr(parent_folder, 'update_folder_icon'):
            parent_folder.update_folder_icon()

        controller = getattr(getattr(sub_btn_to_remove, 'app', None), 'controller', None)
        if controller and hasattr(controller, "_wire_button_signals"):
            try:
                controller._wire_button_signals(sub_btn_to_remove)
            except Exception:
                pass
        return parent_folder
    return None


def _internal_check_and_remove_folder_if_needed(folder_btn: WordBookButton, main_buttons_list: list[WordBookButton],
                                                scroll_content):
    if len(folder_btn.sub_buttons) < 2:  # Dissolve if less than 2 items
        if folder_btn in main_buttons_list:
            main_buttons_list.remove(folder_btn)

        # Move remaining sub-buttons (0 or 1) to the main list
        for btn_to_repromote in folder_btn.sub_buttons:
            btn_to_repromote.is_sub_button = False
            btn_to_repromote.parent_folder = None
            # btn_to_repromote is already parented to scroll_content
            if btn_to_repromote not in main_buttons_list:
                # Add to a sensible position, e.g., where the folder was or at the end
                main_buttons_list.append(btn_to_repromote)  # Simplest: add to end
            btn_to_repromote.show()

        controller = getattr(getattr(folder_btn, 'app', None), 'controller', None)
        if controller and hasattr(controller, "_wire_button_signals"):
            for b in folder_btn.sub_buttons:
                try:
                    controller._wire_button_signals(b)
                except Exception:
                    pass

        if hasattr(folder_btn, 'background_frame') and folder_btn.background_frame:
            folder_btn.background_frame.hide()
            folder_btn.background_frame.deleteLater()

        folder_btn.hide()
        folder_btn.deleteLater()  # Remove the folder button widget itself
        return True  # Folder was dissolved
    return False


class FolderOperationMixin:
    """
    业务操作 Mixin.
    Host class (CoverContent) needs:
        buttons (List[WordBookButton]), scroll_content,
        button_width, button_height, spacing,
        edit_mode, proximity_pair, frame_visible (from HintMixin)
        update_button_positions() (from LayoutMixin),
        toggle_folder() (from AnimationMixin),
        hide_frame() (from HintMixin),
        show_word_book() (own method),
        controller (CoverController, for saving layout)
    """

    def remove_sub_button_from_folder(self, sub_btn: WordBookButton):
        # `self` is CoverContent
        parent_folder = _internal_remove_sub_button_from_folder(sub_btn, self.buttons)
        if not parent_folder:
            return

        if self.edit_mode:
            sub_btn.start_jitter()  # Start jitter on the now main button

        # Check if the parent folder needs to be dissolved
        dissolved = _internal_check_and_remove_folder_if_needed(parent_folder, self.buttons, self.scroll_content)

        self.update_button_positions()  # Refresh layout

        controller = getattr(self, "controller", None)
        if controller and hasattr(controller, "_wire_button_signals"):
            try:
                controller._wire_button_signals(sub_btn)
            except Exception:
                pass

        if hasattr(self, 'controller') and hasattr(self.controller, 'save_current_layout'):
            self.controller.save_current_layout()

    def merge_folders(self):
        # `self` is CoverContent
        if not getattr(self, "proximity_pair", None):
            return

        btn1, btn2 = self.proximity_pair

        # --- A. Add a normal button to an existing folder ---
        if btn2.is_folder and not btn1.is_folder:  # btn1 (dragged) into btn2 (folder)
            self._add_to_existing_folder(src_btn=btn1, folder_btn=btn2)
        elif btn1.is_folder and not btn2.is_folder:  # btn2 (dragged) into btn1 (folder)
            self._add_to_existing_folder(src_btn=btn2, folder_btn=btn1)

        # --- B. Merge two normal buttons into a new folder ---
        elif not btn1.is_folder and not btn2.is_folder:
            self._create_new_folder(btn1, btn2)

        # --- C. Merging folder into folder (not typically supported by simple drag) ---
        # else: # Both are folders, or one is folder and other is also folder (complex case)
        # print("Folder to Folder merge not implemented via simple proximity.")
        # self.hide_frame()
        # return

        self.update_button_positions()
        self.hide_frame()  # From HintMixin

        if hasattr(self, 'controller') and hasattr(self.controller, 'save_current_layout'):
            self.controller.save_current_layout()

    def _add_to_existing_folder(self, src_btn: WordBookButton, folder_btn: WordBookButton):
        # `self` is CoverContent
        new_sub_btn = _internal_add_button_to_folder(src_btn, folder_btn, self.scroll_content, self)

        if src_btn in self.buttons:
            self.buttons.remove(src_btn)
        src_btn.hide()
        src_btn.deleteLater()  # Original button is replaced by new_sub_btn

        if self.edit_mode:
            new_sub_btn.start_jitter()
            if not folder_btn.is_expanded:
                self.toggle_folder(folder_btn)  # From AnimationMixin
            else:
                new_sub_btn.show()
                self.update_button_positions()
        elif folder_btn.is_expanded:
            new_sub_btn.show()
            self.update_button_positions()

        # If not in edit mode and folder is collapsed, sub_btn is added but stays hidden until folder expands
        # update_button_positions will handle overall layout.

        folder_btn.update_folder_icon()

    def _create_new_folder(self, btn1: WordBookButton, btn2: WordBookButton):
        """拖两个主按钮合并 → 新建文件夹。"""
        folder_name = f"Folder {len([b for b in self.buttons if b.is_folder]) + 1}"
        folder_color = btn1.color

        # ▶ 新版构造；随后补挂 app 属性
        folder_btn = WordBookButton(folder_name, folder_color, parent=self.scroll_content)
        folder_btn.app = self
        folder_btn.is_folder = True
        folder_btn.is_expanded = False
        folder_btn.sub_buttons = []
        if hasattr(self, "button_width") and hasattr(self, "button_height"):
            folder_btn.setFixedSize(self.button_width, self.button_height)
        folder_btn.move(btn1.pos())  # 先放到原按钮位置

        # 子按钮实例化（复用上面新改的工具函数）
        sub1 = _create_sub_button_instance(btn1, folder_btn, self.scroll_content, self)
        sub2 = _create_sub_button_instance(btn2, folder_btn, self.scroll_content, self)
        folder_btn.sub_buttons.extend([sub1, sub2])

        controller = getattr(self, "controller", None)
        if controller and hasattr(controller, "_wire_button_signals"):
            try:
                controller._wire_button_signals(folder_btn)
                controller._wire_button_signals(sub1)
                controller._wire_button_signals(sub2)
            except Exception:
                pass

        # 移除原按钮
        for old in (btn1, btn2):
            if old in self.buttons:
                self.buttons.remove(old)
            old.hide();
            old.deleteLater()

        # 挂到主列表并更新 UI
        self.buttons.append(folder_btn)
        folder_btn.show()
        folder_btn.update_folder_icon()

        if self.edit_mode:
            folder_btn.start_jitter();
            sub1.start_jitter();
            sub2.start_jitter()
            self.toggle_folder(folder_btn)  # 编辑模式下自动展开
        else:
            self.toggle_folder(folder_btn)


__all__ = ["FolderOperationMixin"]
# UI/folder_ui/_operations.py结束