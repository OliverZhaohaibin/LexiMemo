from __future__ import annotations

from PySide6.QtCore import QEvent
from PySide6.QtWidgets import QWidget

from Folder_UI.common.folderUI_API import (
    FolderAnimationMixin,
    FolderLayoutMixin,
    FolderHintMixin,
    FolderOperationMixin,
)
from UI.Folder_UI._background import update_all_folder_backgrounds
from UI.Folder_UI._frame import ButtonFrame
from WordBookButton import WordBookButton


class CoverContent(
    FolderAnimationMixin,
    FolderLayoutMixin,
    FolderHintMixin,
    FolderOperationMixin,
    QWidget,
):
    """Scroll‑area content that actually lays out the word‑book buttons and
    handles drag‑and‑drop / folder UI interactions.  It fulfils all
    dependencies required by the 4 FolderUI mixins.
    """

    def __init__(self, parent=None) -> None:
        # *parent* must be the ``QScrollArea`` that hosts this widget.
        super().__init__(parent)
        if parent is None:
            raise ValueError("CoverContent must be constructed with its QScrollArea as parent")

        # ---------- external references ----------
        self.scroll_area = parent          # type: QScrollArea
        self.scroll_content = self         # mixins expect this alias

        # ---------- layout parameters ----------
        self.button_width: int = 120
        self.button_height: int = 150
        self.spacing: int = 10
        self.folder_extra_width: int = 150

        # ---------- runtime state ----------
        self.edit_mode: bool = False
        self.buttons: list[WordBookButton] = []

        # ---------- hint frames ----------
        self.frame = ButtonFrame(
            self,
            "border:2px dashed #3498db; background:rgba(52,152,219,.1);",
        )  # blue merge rectangle
        self.blue_reorder_frame = ButtonFrame(
            self,
            "border:2px dashed blue; background:rgba(0,0,255,.1);",
        )  # blue internal‑order rectangle
        self.red_removal_frame = ButtonFrame(
            self,
            "border:2px dashed red; background:rgba(255,0,0,.1);",
        )  # red removal rectangle
        self.frame_visible: bool = False
        self.blue_reorder_frame.hide()
        self.red_removal_frame.hide()

        # ---------- “新建单词本” ----------
        self.new_book_button = WordBookButton(
            "新建单词本",
            "#a3d2ca",
            parent=self,
            app=self,
        )
        self.new_book_button.is_new_button = True
        # click signal will be rebound by controller

        # intercept wheel so that hint rectangles disappear while scrolling
        self.scroll_area.viewport().installEventFilter(self)

    # ------------------------------------------------------------------
    # FolderOperationMixin callback
    # ------------------------------------------------------------------
    def show_word_book(self, path: str, target_word: str | None = None) -> None:
        """Open the inside‑window for a single word book."""
        if self.edit_mode:
            return
        win = WordBookApp(path, target_word=target_word)
        win.show()

    # ------------------------------------------------------------------
    # QWidget overrides
    # ------------------------------------------------------------------
    def resizeEvent(self, event):  # noqa: D401
        super().resizeEvent(event)
        self.update_button_positions()
        update_all_folder_backgrounds(self, self.button_width, self.button_height)

    def eventFilter(self, obj, ev):
        if ev.type() == QEvent.Wheel and self.frame_visible:
            # hide hint rectangles while scrolling
            self.hide_frame()
        return super().eventFilter(obj, ev)
