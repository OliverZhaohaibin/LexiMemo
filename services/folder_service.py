# services/folder_service.py开始
from __future__ import annotations
import os
import sys
from typing import List, Dict, Any, TYPE_CHECKING

from WordBookButton import WordBookButton
from UI.Folder_UI.api import update_all_folder_backgrounds

if TYPE_CHECKING:
    from UI.cover_content import CoverContent  # For type hinting


class FolderService:
    """Business‑logic layer for the cover page operations related to folders and buttons."""

    def __init__(self) -> None:
        self.content: 'CoverContent' | None = None

    def build_buttons(self, cover_content_instance: 'CoverContent') -> List[WordBookButton]:
        """Scans 'books/' directory and creates WordBookButton instances.
        The 'cover_content_instance' is UI.cover_content.CoverContent."""
        self.content = cover_content_instance

        base_dir = os.path.dirname(os.path.abspath(sys.argv[0]))
        books_dir = os.path.join(base_dir, "books")
        os.makedirs(books_dir, exist_ok=True)

        buttons: list[WordBookButton] = []

        total_word_book_name = "总单词册"
        total_word_book_color = "#FF0000"
        total_word_book_folder_name = f"books_{total_word_book_name}_{total_word_book_color}"
        total_word_book_path_on_disk = os.path.join(books_dir, total_word_book_folder_name)
        if not os.path.exists(total_word_book_path_on_disk):
            os.makedirs(total_word_book_path_on_disk, exist_ok=True)
            from db import init_db as db_init_db
            db_init_db(os.path.join(total_word_book_path_on_disk, "wordbook.db"))

        book_folders_data = []
        for folder_on_disk in os.listdir(books_dir):
            if not folder_on_disk.startswith("books_") or not os.path.isdir(os.path.join(books_dir, folder_on_disk)):
                continue
            try:
                _, book_name, book_color = folder_on_disk.split("_", 2)
                book_folders_data.append({'name': book_name, 'color': book_color, 'folder_name': folder_on_disk})
            except ValueError:
                continue

        sorted_book_folders = sorted(
            book_folders_data,
            key=lambda x: (x['name'] != total_word_book_name, x['name'])
        )

        for book_data in sorted_book_folders:
            path = os.path.join(books_dir, book_data['folder_name'])
            btn = WordBookButton(book_data['name'], book_data['color'], parent=self.content, app=self.content)
            btn.path = path

            if not btn.is_folder and hasattr(self.content, 'show_word_book'):
                try:
                    btn.clicked.disconnect()
                except RuntimeError:
                    pass
                btn.clicked.connect(lambda checked=False, p=btn.path: self.content.show_word_book(p))  # type: ignore
            buttons.append(btn)

        self.content.buttons = buttons
        return buttons

    def set_edit_mode(self, entering: bool, buttons_on_content: list[WordBookButton]) -> None:
        """Toggles edit mode for buttons (jitter, delete visibility)."""
        if not self.content: return

        for b in buttons_on_content:
            if not getattr(b, 'is_new_button', False):
                if entering:
                    b.start_jitter()
                else:
                    b.stop_jitter()

        if hasattr(self.content, 'new_book_button'):
            if entering:
                self.content.new_book_button.start_jitter()
            else:
                self.content.new_book_button.stop_jitter()

        if entering:
            for b_main in buttons_on_content:
                if b_main.is_folder and b_main.is_expanded:
                    for sub_b in b_main.sub_buttons:
                        sub_b.start_jitter()

    def highlight_search(self, kw: str, buttons_on_content: list[WordBookButton]) -> None:
        kw_lc = kw.strip().lower()
        all_buttons_to_check = buttons_on_content[:]
        if hasattr(self.content, 'new_book_button'):
            all_buttons_to_check.append(self.content.new_book_button)

        for b in all_buttons_to_check:
            if getattr(b, "is_new_button", False) and b is not self.content.new_book_button:
                continue

            original_stylesheet = getattr(b, '_original_stylesheet', b.styleSheet())
            if not hasattr(b, '_original_stylesheet'):
                b._original_stylesheet = original_stylesheet

            is_match = kw_lc and kw_lc in b.text().lower()

            current_style = b.styleSheet()
            border_highlight = "border:2px solid #e67e22;"

            if is_match:
                if border_highlight not in current_style:
                    import re
                    style_no_border = re.sub(r"border:.*?;", "", current_style, flags=re.IGNORECASE)
                    style_no_border = re.sub(r"\s\s+", " ", style_no_border).strip()
                    if style_no_border and not style_no_border.endswith(';'):
                        style_no_border += ";"
                    b.setStyleSheet(style_no_border + " " + border_highlight if style_no_border else border_highlight)
            else:
                b.setStyleSheet(original_stylesheet)

    def show_new_wordbook_dialog(self) -> tuple[bool, str | None, str | None]:
        from UI.new_wordbook_dialog import NewWordBookDialog
        parent_window = self.content.window() if self.content else None
        dlg = NewWordBookDialog(parent_window)
        if dlg.exec():
            return True, dlg.book_name, dlg.book_color
        return False, None, None

    def export_layout(self, buttons_on_content: list[WordBookButton]) -> List[Dict[str, Any]]:
        """Exports the current layout of buttons and folders."""
        items = []
        for btn in buttons_on_content:
            if getattr(btn, "is_new_button", False): continue

            item_data: Dict[str, Any] = {
                "name": btn.text(),
                "color": btn.color,
            }
            if btn.path:  # Store path if available
                item_data["path"] = btn.path

            if btn.is_folder:
                item_data["type"] = "folder"
                item_data["is_expanded"] = btn.is_expanded
                item_data["sub_books"] = []
                for sub in btn.sub_buttons:
                    sub_book_data = {
                        "name": sub.text(),
                        "color": sub.color,
                    }
                    if sub.path:
                        sub_book_data["path"] = sub.path
                    item_data["sub_books"].append(sub_book_data)
            else:
                item_data["type"] = "wordbook"
            items.append(item_data)
        return items

    def apply_layout(self, layout_items: List[Dict[str, Any]], current_buttons_from_scan: list[WordBookButton]) -> None:
        """Reconstructs button order and folder hierarchy based on saved layout.
        'current_buttons_from_scan' are WordBookButton instances from disk.
        'self.content' is CoverContent.
        """
        if not self.content: return

        # Map scanned buttons by path for reliable lookup
        path_to_scanned_btn: dict[str, WordBookButton] = {
            btn.path: btn for btn in current_buttons_from_scan if btn.path
        }
        # Fallback map by name_color for items that might have lost path or are new folders
        name_color_to_scanned_btn: dict[str, WordBookButton] = {
            f"{btn.text()}_{btn.color}": btn for btn in current_buttons_from_scan
        }

        new_ordered_main_buttons: list[WordBookButton] = []
        processed_paths: set[str] = set()  # Tracks paths of buttons already placed

        for item_spec in layout_items:
            item_name = item_spec.get("name")
            item_color = item_spec.get("color")
            item_path = item_spec.get("path")  # Path from layout file
            item_type = item_spec.get("type")

            current_btn_instance: WordBookButton | None = None

            # Try to find existing button by path first, then by name_color
            if item_path and item_path in path_to_scanned_btn:
                current_btn_instance = path_to_scanned_btn[item_path]
            elif item_name and item_color:
                current_btn_instance = name_color_to_scanned_btn.get(f"{item_name}_{item_color}")

            if item_type == "folder":
                folder_btn: WordBookButton
                if current_btn_instance and current_btn_instance.path and current_btn_instance.path not in processed_paths:
                    # An existing scanned button is now marked as a folder
                    folder_btn = current_btn_instance
                    processed_paths.add(folder_btn.path)
                elif current_btn_instance and not current_btn_instance.path and f"{item_name}_{item_color}" not in processed_paths:  # Check by name_color if path was missing
                    folder_btn = current_btn_instance
                    processed_paths.add(f"{item_name}_{item_color}")  # Use name_color as processed key
                else:  # Create a new folder button if not found or already processed
                    folder_btn = WordBookButton(item_name, item_color, parent=self.content, app=self.content)

                folder_btn.is_folder = True
                folder_btn.is_expanded = item_spec.get("is_expanded", False)
                folder_btn.sub_buttons = []  # Clear any previous sub_buttons if reusing an instance

                for sub_item_spec in item_spec.get("sub_books", []):
                    sub_name = sub_item_spec.get("name")
                    sub_color = sub_item_spec.get("color")
                    sub_path = sub_item_spec.get("path")

                    original_scanned_sub_btn: WordBookButton | None = None
                    if sub_path and sub_path in path_to_scanned_btn:
                        original_scanned_sub_btn = path_to_scanned_btn[sub_path]
                    elif sub_name and sub_color:
                        original_scanned_sub_btn = name_color_to_scanned_btn.get(f"{sub_name}_{sub_color}")

                    if original_scanned_sub_btn and original_scanned_sub_btn.path and original_scanned_sub_btn.path not in processed_paths:
                        # This sub-button is taken from the scanned list
                        # We don't create a new instance, we *move* the scanned instance into the folder
                        original_scanned_sub_btn.is_sub_button = True
                        original_scanned_sub_btn.parent_folder = folder_btn
                        original_scanned_sub_btn.hide()

                        if hasattr(self.content, 'show_word_book'):
                            try:
                                original_scanned_sub_btn.clicked.disconnect()
                            except RuntimeError:
                                pass
                            original_scanned_sub_btn.clicked.connect(
                                lambda checked=False, p=original_scanned_sub_btn.path: self.content.show_word_book(p)
                                # type: ignore
                            )
                        folder_btn.sub_buttons.append(original_scanned_sub_btn)
                        processed_paths.add(original_scanned_sub_btn.path)
                    elif not original_scanned_sub_btn:
                        print(f"Warning: Sub-book '{sub_name}' (color: {sub_color}) from layout not found on disk.")

                folder_btn.update_folder_icon()
                new_ordered_main_buttons.append(folder_btn)

            elif item_type == "wordbook":
                if current_btn_instance and current_btn_instance.path and current_btn_instance.path not in processed_paths:
                    current_btn_instance.is_folder = False
                    current_btn_instance.sub_buttons = []
                    if hasattr(self.content, 'show_word_book') and current_btn_instance.path:
                        try:
                            current_btn_instance.clicked.disconnect()
                        except RuntimeError:
                            pass
                        current_btn_instance.clicked.connect(
                            lambda checked=False, p=current_btn_instance.path: self.content.show_word_book(p)
                            # type: ignore
                        )
                    new_ordered_main_buttons.append(current_btn_instance)
                    processed_paths.add(current_btn_instance.path)
                elif not current_btn_instance and item_name and item_color:  # Only print warning if it was expected to be found
                    print(f"Warning: Wordbook '{item_name}' (color: {item_color}) from layout not found on disk.")

        # Add any scanned buttons that were not in the layout (e.g., newly created books)
        for path, btn in path_to_scanned_btn.items():
            if path not in processed_paths:
                btn.is_folder = False
                btn.sub_buttons = []
                if hasattr(self.content, 'show_word_book') and btn.path:
                    try:
                        btn.clicked.disconnect()
                    except RuntimeError:
                        pass
                    btn.clicked.connect(
                        lambda checked=False, p=btn.path: self.content.show_word_book(p)  # type: ignore
                    )
                new_ordered_main_buttons.append(btn)

        # Cleanup: remove buttons from scanned list that were incorporated as sub_buttons
        # and are thus no longer main buttons.
        final_main_buttons = []
        for btn in new_ordered_main_buttons:
            if not btn.is_sub_button:
                final_main_buttons.append(btn)
            # Ensure correct parent for Qt display
            if btn.parent() != self.content:
                btn.setParent(self.content)
            btn.show()

        self.content.buttons = final_main_buttons
        self.content.update_button_positions()

# services/folder_service.py结束