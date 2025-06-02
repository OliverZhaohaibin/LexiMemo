# UI/Folder_UI/_hints.py开始
from PySide6.QtCore import QRect
from ._layout import calculate_folder_area # Assumes calculate_folder_area is in _layout.py

class FolderHintMixin:
    """Unified management for hint frames.
    Host class (e.g., CoverContent) needs:
    - QFrame attributes: self.frame, self.blue_reorder_frame, self.red_removal_frame
    - bool: self.frame_visible
    - int: self.button_width, self.button_height, self.spacing
    - QWidget: self.scroll_content (for its width)
    """
    def show_frame(self, btn1, btn2):
        """Shows a blue dashed frame around two buttons to indicate a merge possibility."""
        if not hasattr(self, 'frame'): return
        left = min(btn1.x(), btn2.x()) - 10
        top = min(btn1.y(), btn2.y()) - 10
        right = max(btn1.x() + self.button_width, btn2.x() + self.button_width) + 10
        bottom = max(btn1.y() + self.button_height, btn2.y() + self.button_height) + 10
        self.frame.setGeometry(left, top, right - left, bottom - top)
        self.frame.show()
        self.frame_visible = True

    def hide_frame(self):
        """Hides the blue merge hint frame."""
        if hasattr(self, 'frame'):
            self.frame.hide()
        self.frame_visible = False

    def is_button_in_frame(self, button) -> bool:
        """Checks if the center of a button is within the visible blue merge hint frame."""
        if not self.frame_visible or not hasattr(self, 'frame'):
            return False
        button_rect = QRect(button.pos(), button.size())
        return self.frame.geometry().contains(button_rect.center())

    def show_blue_reorder_frame(self, parent_folder):
        """Shows a blue dashed frame indicating the reorder area within an expanded folder."""
        if not hasattr(self, 'blue_reorder_frame') or not hasattr(self, 'scroll_content'): return

        # Use calculate_folder_area from ._layout
        min_x_subs_only, min_y_subs_only, max_x_subs_only, max_y_subs_only = calculate_folder_area(
            parent_folder, parent_folder.sub_buttons, self.button_width, self.button_height
        )
        margin = 10
        # The reorder frame should span the width of the scroll content
        # and cover the vertical extent of sub-buttons.
        # Top starts from the top of the sub-button area.
        # If no sub_buttons, use parent_folder's bottom as reference.
        if parent_folder.sub_buttons:
            top = min_y_subs_only - margin
            height = (max_y_subs_only - min_y_subs_only) + 2 * margin
        else: # Fallback if no sub_buttons, frame below folder button
            top = parent_folder.y() + self.button_height + self.spacing - margin
            height = self.button_height + 2 * margin # A default height

        self.blue_reorder_frame.setGeometry(0, top, self.scroll_content.width(), height)
        self.blue_reorder_frame.show()
        self.blue_reorder_frame.raise_()


    def hide_blue_reorder_frame(self):
        """Hides the blue reorder hint frame."""
        if hasattr(self, 'blue_reorder_frame'):
            self.blue_reorder_frame.hide()

    def show_red_removal_frame(self, parent_folder):
        """Shows a red dashed frame indicating the area outside which a sub-button is considered "removed"."""
        if not hasattr(self, 'red_removal_frame'): return

        # The removal frame should be slightly larger than the folder's total area
        # including the folder button itself and its sub-buttons.
        all_buttons_for_area = [parent_folder] + parent_folder.sub_buttons
        min_x, min_y, max_x, max_y = calculate_folder_area(
            parent_folder, # This first arg is mostly for initial pos if sub_buttons is empty
            all_buttons_for_area, # Pass all relevant buttons for area calculation
            self.button_width,
            self.button_height
        )
        margin = 20 # A larger margin for the removal frame
        left = min_x - margin
        top = min_y - margin
        width = (max_x - min_x) + 2 * margin
        height = (max_y - min_y) + 2 * margin
        self.red_removal_frame.setGeometry(left, top, width, height)
        self.red_removal_frame.show()
        self.red_removal_frame.raise_()


    def hide_red_removal_frame(self):
        """Hides the red removal hint frame."""
        if hasattr(self, 'red_removal_frame'):
            self.red_removal_frame.hide()

__all__ = ["FolderHintMixin"]
# UI/Folder_UI/_hints.py结束