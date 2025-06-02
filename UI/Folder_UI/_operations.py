# UI/Folder_UI/_operations.py开始
from __future__ import annotations
import os
import sys

from WordBookButton import WordBookButton  # Assuming WordBookButton is in root


# Helper functions for folder operations (adapted from original Folder_UI/folder_operations.py)

def _create_sub_button_instance(original_button: WordBookButton, parent_folder: WordBookButton, scroll_content,
                                app_instance) -> WordBookButton:
    """Creates a new WordBookButton instance to act as a sub-button."""
    sub_btn = WordBookButton(original_button.text(), original_button.color, parent=scroll_content, app=app_instance)
    sub_btn.is_sub_button = True
    sub_btn.parent_folder = parent_folder
    sub_btn.path = original_button.path  # Critical: preserve the path for opening the book

    # Re-connect the clicked signal to the app_instance's (CoverContent) show_word_book method
    # WordBookButton's default click is to call self.app.show_word_book(self.path)
    # Ensure this is correctly handled or re-bound if necessary.
    # If WordBookButton.clicked signal is already connected and path is set, it might just work.
    # For clarity, we can ensure connection:
    if hasattr(app_instance, 'show_word_book'):
        try:
            sub_btn.clicked.disconnect()  # Disconnect any previous if WordBookButton constructor connects it
        except:
            pass
        sub_btn.clicked.connect(lambda checked=False, p=sub_btn.path: app_instance.show_word_book(p))

    sub_btn.hide()  # Initially hidden, will be shown by animation or layout update
    return sub_btn


def _internal_add_button_to_folder(button_to_add: WordBookButton, folder: WordBookButton, scroll_content,
                                   app_instance) -> WordBookButton:
    sub_btn = _create_sub_button_instance(button_to_add, folder, scroll_content, app_instance)
    folder.sub_buttons.append(sub_btn)
    folder.update_folder_icon()
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
            # If folder was not expanded, expand it to show the new sub_button
            if not folder_btn.is_expanded:
                self.toggle_folder(folder_btn)  # From AnimationMixin
        elif folder_btn.is_expanded:  # If already expanded, just update positions
            self.update_button_positions()  # This will show the new_sub_btn

        # If not in edit mode and folder is collapsed, sub_btn is added but stays hidden until folder expands
        # update_button_positions will handle overall layout.

        folder_btn.update_folder_icon()

    def _create_new_folder(self, btn1: WordBookButton, btn2: WordBookButton):
        # `self` is CoverContent
        folder_name = f"Folder {len([b for b in self.buttons if b.is_folder]) + 1}"
        # Use color of the button that was likely static (btn1 if btn2 was dragged, or vice-versa)
        # For simplicity, using btn1's color.
        folder_color = btn1.color

        folder_btn = WordBookButton(folder_name, folder_color, parent=self.scroll_content, app=self)
        folder_btn.is_folder = True
        folder_btn.is_expanded = False  # Start collapsed, toggle_folder will handle expansion
        folder_btn.move(btn1.pos())  # Initial position
        folder_btn.sub_buttons = []

        # Create sub_button instances for btn1 and btn2
        sub1 = _create_sub_button_instance(btn1, folder_btn, self.scroll_content, self)
        sub2 = _create_sub_button_instance(btn2, folder_btn, self.scroll_content, self)
        folder_btn.sub_buttons.extend([sub1, sub2])

        # Remove original btn1 and btn2 from main list and scene
        if btn1 in self.buttons: self.buttons.remove(btn1)
        btn1.hide();
        btn1.deleteLater()
        if btn2 in self.buttons: self.buttons.remove(btn2)
        btn2.hide();
        btn2.deleteLater()

        # Add new folder_btn to main list
        self.buttons.append(folder_btn)
        folder_btn.show()  # Make folder button visible
        folder_btn.update_folder_icon()

        if self.edit_mode:
            folder_btn.start_jitter()
            sub1.start_jitter()  # New sub-buttons also jitter
            sub2.start_jitter()
            self.toggle_folder(folder_btn)  # Expand new folder in edit mode
        else:
            self.toggle_folder(folder_btn)  # Expand new folder by default


__all__ = ["FolderOperationMixin"]
# UI/Folder_UI/_operations.py结束