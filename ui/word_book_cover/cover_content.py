# ui/cover_content.py开始
from __future__ import annotations
from typing import TYPE_CHECKING

from PySide6.QtCore import QEvent, Qt
from PySide6.QtWidgets import QWidget, QScrollArea, QMessageBox
from PySide6.QtGui import QResizeEvent

from ui.folder_ui.api import (
    FolderAnimationMixin,
    FolderLayoutMixin,
    FolderHintMixin,
    FolderOperationMixin,
    update_all_folder_backgrounds,
    ButtonFrame,
    calculate_button_distance
)
from ui.word_book_button import WordBookButton
from ui.word_book_button import WordBookButtonView, WordBookButtonViewModel
from controllers.wordbook_button_controller import WordBookButtonController
from repositories.wordbook_repository import WordBook


from ui.word_book_inside.word_book_window import WordBookWindow

if TYPE_CHECKING:
    from controllers.cover_controller import CoverController


class CoverContent(
    QWidget,
    FolderAnimationMixin,
    FolderLayoutMixin,
    FolderHintMixin,
    FolderOperationMixin
):
    """Scroll‑area content that actually lays out the word‑book buttons and
    handles drag‑and‑drop / folder ui interactions.  It fulfils all
    dependencies required by the 4 FolderUI mixins.
    """

    def __init__(self, parent: QScrollArea) -> None:
        super().__init__(parent)
        if not isinstance(parent, QScrollArea):
            raise ValueError("CoverContent must be constructed with its QScrollArea as parent")

        self.scroll_area: QScrollArea = parent
        self.scroll_content: CoverContent = self
        self.controller: CoverController | None = None

        self.button_width: int = 120
        self.button_height: int = 150
        self.spacing: int = 20
        self.top_margin: int = 60
        self.folder_extra_width: int = 0

        self.edit_mode: bool = False
        self.buttons: list[WordBookButton] = []
        self.proximity_pair = None
        self.proximity_threshold = 100  # ADJUSTED FROM 68 (was too small for 120px wide buttons)

        self.frame = ButtonFrame(self, "border:2px dashed #3498db; background:rgba(52,152,219,.1);")
        self.blue_reorder_frame = ButtonFrame(self, "border:2px dashed blue; background:rgba(0,0,255,.1);")
        self.red_removal_frame = ButtonFrame(self, "border:2px dashed red; background:rgba(255,0,0,.1);")
        self.frame_visible: bool = False

        self.new_book_button = WordBookButton("新建单词本", "#a3d2ca", parent=self)
        self.new_book_button.app = self
        self.new_book_button.is_new_button = True
        self.new_book_button.is_folder = False
        self.new_book_button.is_sub_button = False
        self.new_book_button.setFixedSize(self.button_width, self.button_height)

        self.scroll_area.viewport().installEventFilter(self)
        self._child_windows: list[WordBookWindow] = []
        self.setAcceptDrops(True)

    def check_button_proximity(self, dragged_button: WordBookButton):
        """Checks proximity for merging non-folder button with another non-folder button,
           or adding a non-folder button to an existing folder."""
        if dragged_button.is_sub_button or \
                getattr(dragged_button, 'is_new_button', False) or \
                dragged_button.is_folder:
            self.hide_frame()
            self.proximity_pair = None
            return

        closest_target = None
        min_distance_to_target = float('inf')

        for target_btn in self.buttons:
            if target_btn is dragged_button or \
                    target_btn.is_sub_button or \
                    getattr(target_btn, 'is_new_button', False):
                continue

            distance = calculate_button_distance(dragged_button, target_btn, self.button_width, self.button_height)

            if distance < min_distance_to_target:
                min_distance_to_target = distance
                closest_target = target_btn

        if closest_target and min_distance_to_target < self.proximity_threshold:
            self.show_frame(dragged_button, closest_target)
            self.proximity_pair = (dragged_button, closest_target)
        else:
            self.hide_frame()
            self.proximity_pair = None

    def show_word_book(self, path: str, target_word: str | None = None) -> None:
        if self.edit_mode and not getattr(self, 'opening_during_edit_allowed', False):
            return
        win = WordBookWindow(path, target_word=target_word)
        self._child_windows.append(win)
        win.setAttribute(Qt.WA_DeleteOnClose)
        win.destroyed.connect(lambda: self._child_windows.remove(win) if win in self._child_windows else None)
        win.show()

    def delete_word_book(self, button_to_delete: WordBookButton):
        if self.controller:
            self.controller.delete_word_book(button_to_delete)
        else:
            QMessageBox.warning(self, "Error", "Controller not available for deletion.")

    def resizeEvent(self, event: QResizeEvent) -> None:
        super().resizeEvent(event)
        self.update_button_positions()

    def eventFilter(self, obj, ev: QEvent) -> bool:
        if obj is self.scroll_area.viewport():
            if ev.type() == QEvent.Type.Wheel:
                if self.frame_visible: self.hide_frame()
                if self.blue_reorder_frame.isVisible(): self.hide_blue_reorder_frame()
                if self.red_removal_frame.isVisible(): self.hide_red_removal_frame()
            elif ev.type() == QEvent.Type.Resize:
                self.update_button_positions()

        return super().eventFilter(obj, ev)
