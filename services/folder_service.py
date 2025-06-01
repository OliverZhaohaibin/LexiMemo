from __future__ import annotations

import os
import sys
from typing import List

from WordBookButton import WordBookButton

from UI.Folder_UI._background import update_all_folder_backgrounds


class FolderService:
    """Business‑logic layer for the cover page.

    * IO: scan 'books/' directory and build buttons
    * Simple visual high‑lighting for global search
    * Edit‑mode toggling (start / stop jitter)
    * Layout persistence (export / apply)
    """

    def __init__(self) -> None:
        # will be set to the ``CoverContent`` instance in ``build_buttons``
        self.content = None  # type: ignore

    # ------------------------------------------------------------------
    #               build & lay‑out buttons
    # ------------------------------------------------------------------
    def build_buttons(self, parent) -> List[WordBookButton]:
        """Create ``WordBookButton`` instances for each folder under *books/*.
        The *parent* argument is the ``CoverContent`` instance."""
        self.content = parent

        base_dir = os.path.dirname(os.path.abspath(sys.argv[0]))
        books_dir = os.path.join(base_dir, "books")
        os.makedirs(books_dir, exist_ok=True)

        buttons: list[WordBookButton] = []
        for folder in os.listdir(books_dir):
            if not folder.startswith("books_"):
                continue
            try:
                _, book_name, book_color = folder.split("_", 2)
            except ValueError:
                # malformed directory name – skip
                continue

            path = os.path.join(books_dir, folder)
            btn = WordBookButton(book_name, book_color, parent=parent, app=parent)
            btn.path = path
            buttons.append(btn)

        # -------- "新建单词本" button --------
        if parent.new_book_button.parent() is None:
            parent.new_book_button.setParent(parent)
        buttons.append(parent.new_book_button)

        return buttons

    def layout_buttons(self, content, buttons):
        content.buttons = buttons
        content.update_button_positions()
        update_all_folder_backgrounds(content, content.button_width, content.button_height)

    # ------------------------------------------------------------------
    #                    edit‑mode switch
    # ------------------------------------------------------------------
    def set_edit_mode(self, entering: bool, buttons: list[WordBookButton]) -> None:
        if self.content:
            self.content.edit_mode = entering

        for b in buttons:
            (b.start_jitter() if entering else b.stop_jitter())

        # make the "new book" button jitter as well
        if self.content:
            if entering:
                self.content.new_book_button.start_jitter()
            else:
                self.content.new_book_button.stop_jitter()

    # ------------------------------------------------------------------
    #                    search high‑light
    # ------------------------------------------------------------------
    def highlight_search(self, kw: str, buttons: list[WordBookButton]) -> None:
        kw_lc = kw.strip().lower()
        for b in buttons:
            if getattr(b, "is_new_button", False):
                continue
            matched = kw_lc and kw_lc in b.text().lower()
            b.setStyleSheet(
                b.styleSheet()
                + ("border:2px solid #e67e22;" if matched else "border:none;")
            )

    # ------------------------------------------------------------------
    #                    new‑word‑book dialog
    # ------------------------------------------------------------------
    def show_new_wordbook_dialog(self) -> bool:
        # 关键修改：把导入放进函数体里，彻底断开 cover ↔ service 的循环引用
        from UI.new_wordbook_dialog import NewWordBookDialog  # ★ 改动
        dlg = NewWordBookDialog()
        return dlg.exec() == dlg.Accepted

    # ------------------------------------------------------------------
    #                    layout persistence helpers
    # ------------------------------------------------------------------
    def export_layout(self, buttons: list[WordBookButton]):
        items = []
        for btn in buttons:
            if getattr(btn, "is_folder", False):
                items.append(
                    {
                        "type": "folder",
                        "name": btn.text(),
                        "color": getattr(btn, "color", "#a3d2ca"),
                        "is_expanded": getattr(btn, "is_expanded", False),
                        "sub_books": [sub.text() for sub in btn.sub_buttons],
                    }
                )
            else:
                items.append(
                    {
                        "type": "wordbook",
                        "name": btn.text(),
                        "color": getattr(btn, "color", "#a3d2ca"),
                    }
                )
        return items

    def apply_layout(self, layout_items, buttons: list[WordBookButton]) -> None:
        """Re‑create button order & folder hierarchy based on the JSON artefact
        previously produced by :py:meth:`export_layout`."""
        if not self.content:
            return

        # 1. current button index lookup
        name_to_btn = {btn.text(): btn for btn in buttons}
        new_buttons: list[WordBookButton] = []
        used_names: set[str] = set()

        base_dir = os.path.dirname(os.path.abspath(sys.argv[0]))
        books_dir = os.path.join(base_dir, "books")

        for item in layout_items:
            if item.get("type") == "wordbook":
                btn = name_to_btn.get(item["name"])
                if btn:
                    new_buttons.append(btn)
                    used_names.add(btn.text())

            elif item.get("type") == "folder":
                folder_btn = WordBookButton(
                    item["name"],
                    item.get("color", "#a3d2ca"),
                    parent=self.content,
                    app=self.content,
                )
                folder_btn.is_folder = True
                folder_btn.is_expanded = False
                folder_btn.sub_buttons = []

                for sub_name in item.get("sub_books", []):
                    src_btn = name_to_btn.get(sub_name)
                    if not src_btn:
                        continue

                    sub_btn = WordBookButton(
                        src_btn.text(),
                        getattr(src_btn, "color", "#a3d2ca"),
                        parent=self.content,
                        app=self.content,
                    )
                    sub_btn.is_sub_button = True
                    sub_btn.parent_folder = folder_btn
                    sub_btn.hide()  # collapsed by default
                    folder_btn.sub_buttons.append(sub_btn)

                    # bind click → open inside window
                    book_dir = f"books_{sub_btn.text()}_{sub_btn.color}"
                    book_path = os.path.join(books_dir, book_dir)
                    sub_btn.clicked.connect(
                        lambda _, p=book_path: self.content.show_word_book(p)
                    )

                    # remove original main‑button reference
                    src_btn.setParent(None)
                    src_btn.deleteLater()
                    name_to_btn.pop(sub_name, None)
                    used_names.add(sub_name)

                folder_btn.update_folder_icon()
                new_buttons.append(folder_btn)

        # 4. append any buttons that were not covered by the JSON
        for name, btn in name_to_btn.items():
            if name not in used_names:
                new_buttons.append(btn)

        # 5. write back and refresh layout
        buttons.clear()
        buttons.extend(new_buttons)
        self.content.buttons = buttons
        self.content.update_button_positions()
        update_all_folder_backgrounds(
            self.content, self.content.button_width, self.content.button_height
        )
