# controllers/cover_controller.py开始
from __future__ import annotations
import os
import sys
from PySide6.QtCore import QObject, QEvent, Slot, Qt, QUrl, QTimer  # Added QTimer
from PySide6.QtWidgets import QMenu, QMessageBox
from PySide6.QtGui import QDesktopServices

from UI.word_book_cover.cover_view import CoverView
from services.folder_service import FolderService
from services.cover_layout_service import CoverLayoutService
from WordBookButton import WordBookButton
from UI.word_book_inside.word_book_window import WordBookWindow
from db import delete_word as db_delete_word_directly, init_db as db_init_db
import shutil


class CoverController(QObject):
    def __init__(self, view: CoverView) -> None:
        super().__init__()
        self.view: CoverView = view
        self.fs: FolderService = FolderService()
        self.ls: CoverLayoutService = CoverLayoutService()
        self.edit_mode: bool = False
        self._child_windows: list[WordBookWindow] = []

        self.view.content.controller = self  # Link controller to content for callbacks

        v = self.view
        v.editToggled.connect(self._set_edit_mode)
        v.searchTextChanged.connect(self._on_search_text)
        v.suggestionSelected.connect(self._open_word_by_text)

        self._load_buttons_and_layout()
        self._build_word_index()
        v.scroll_area.viewport().installEventFilter(self)

    def _get_content_buttons(self) -> list[WordBookButton]:
        """Helper to get the current list of main buttons from CoverContent."""
        return getattr(self.view.content, 'buttons', [])

    def _load_buttons_and_layout(self) -> None:
        self.view.clear_wordbook_buttons()

        # fs.build_buttons populates self.view.content.buttons
        _ = self.fs.build_buttons(self.view.content)

        if hasattr(self.view.content, 'new_book_button'):
            try:
                self.view.content.new_book_button.clicked.disconnect()
            except RuntimeError:
                pass
            self.view.content.new_book_button.clicked.connect(self._create_wordbook)
            self.view.content.new_book_button.setContextMenuPolicy(Qt.CustomContextMenu)
            self.view.content.new_book_button.customContextMenuRequested.connect(
                lambda pos, b=self.view.content.new_book_button: self._show_button_context_menu(pos, b)
            )

        for btn in self.view.content.buttons:  # Iterate over newly built buttons
            if getattr(btn, "is_new_button", False):  # Should not happen if new_book_button is separate
                continue

            try:
                btn.clicked.disconnect()  # Clear any previous connections
            except RuntimeError:
                pass  # No connections to remove

            if btn.is_folder:
                # Connect to controller's method to decide if toggle should happen
                btn.clicked.connect(lambda checked=False, b=btn: self._handle_folder_click(b))
            elif hasattr(btn, 'path') and btn.path:
                btn.clicked.connect(lambda checked=False, p=btn.path: self._open_wordbook(p))

            btn.nameChangedNeedsLayoutSave.connect(self.save_current_layout)
            btn.setContextMenuPolicy(Qt.CustomContextMenu)
            btn.customContextMenuRequested.connect(lambda pos, b=btn: self._show_button_context_menu(pos, b))

            self.view.add_wordbook_button(btn)  # Adds to CoverContent's visual hierarchy

        layout_data = self.ls.load()
        if layout_data:
            # apply_layout reorders/reconstructs self.view.content.buttons
            self.fs.apply_layout(layout_data, self.view.content.buttons)

        self.view.content.update_button_positions()

    def _handle_folder_click(self, button: WordBookButton):
        if not self.edit_mode and button.is_folder:
            self.view.content.toggle_folder(button)
        # If in edit mode, clicking a folder does nothing (drag is primary interaction)

    def _show_button_context_menu(self, pos, button: WordBookButton):
        is_the_new_book_btn_widget = hasattr(self.view.content, 'new_book_button') and \
                                     button is self.view.content.new_book_button

        if is_the_new_book_btn_widget and not self.edit_mode:
            return

        menu = QMenu(self.view)
        if self.edit_mode and not is_the_new_book_btn_widget:
            rename_action = menu.addAction("重命名")
            rename_action.triggered.connect(lambda: self._rename_button(button))

        if not is_the_new_book_btn_widget:
            delete_action = menu.addAction("删除")
            delete_action.triggered.connect(lambda: self.delete_word_book(button))

        if not button.is_folder and hasattr(button, 'path') and button.path and not is_the_new_book_btn_widget:
            open_folder_action = menu.addAction("打开文件位置")
            open_folder_action.triggered.connect(lambda: self._open_book_location(button))

        if menu.actions():
            menu.exec_(button.mapToGlobal(pos))

    def _rename_button(self, button: WordBookButton):
        button.rename_source = "context_menu"
        button.start_name_edit()

    def _open_book_location(self, button: WordBookButton):
        if button.path and os.path.exists(button.path):
            QDesktopServices.openUrl(QUrl.fromLocalFile(button.path))
        else:
            QMessageBox.warning(self.view, "错误", "找不到单词本文件夹路径。")

    def delete_word_book(self, button_to_delete: WordBookButton):
        if button_to_delete.text() == "总单词册" and not button_to_delete.is_sub_button:
            QMessageBox.information(self.view, "提示", "『总单词册』是主单词册，无法删除！")
            return

        confirm = QMessageBox.question(self.view, "确认删除",
                                       f"确定要删除 '{button_to_delete.text()}' 吗？\n此操作不可恢复！",
                                       QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No,
                                       QMessageBox.StandardButton.No)
        if confirm == QMessageBox.StandardButton.No: return

        content = self.view.content

        if button_to_delete.is_sub_button and button_to_delete.parent_folder:
            parent = button_to_delete.parent_folder
            if button_to_delete in parent.sub_buttons:
                parent.sub_buttons.remove(button_to_delete)
            try:
                # Assuming db_delete_word_directly handles cases where book/color might not exist
                db_delete_word_directly(button_to_delete.text(), button_to_delete.color, "%")  # Deletes all words
                if button_to_delete.path and os.path.isdir(button_to_delete.path):
                    shutil.rmtree(button_to_delete.path)
            except Exception as e:
                QMessageBox.warning(self.view, "删除子项文件失败", f"删除 '{button_to_delete.text()}' 的文件失败: {e}")

            button_to_delete.deleteLater()
            parent.update_folder_icon()

            from UI.folder_ui._operations import _internal_check_and_remove_folder_if_needed
            _internal_check_and_remove_folder_if_needed(parent, content.buttons, content.scroll_content)

        else:  # Main button (folder or wordbook)
            if button_to_delete in content.buttons:
                content.buttons.remove(button_to_delete)

            if button_to_delete.is_folder:
                for sub_btn in button_to_delete.sub_buttons:
                    try:
                        db_delete_word_directly(sub_btn.text(), sub_btn.color, "%")
                        if sub_btn.path and os.path.isdir(sub_btn.path):
                            shutil.rmtree(sub_btn.path)
                    except Exception as e:
                        QMessageBox.warning(self.view, "删除子项文件失败",
                                            f"删除文件夹内 '{sub_btn.text()}' 的文件失败: {e}")
                    sub_btn.deleteLater()
            else:  # Single wordbook
                try:
                    db_delete_word_directly(button_to_delete.text(), button_to_delete.color, "%")
                    if button_to_delete.path and os.path.isdir(button_to_delete.path):
                        shutil.rmtree(button_to_delete.path)
                except Exception as e:
                    QMessageBox.warning(self.view, "删除文件失败", f"删除 '{button_to_delete.text()}' 的文件失败: {e}")

            if hasattr(button_to_delete, 'background_frame') and button_to_delete.background_frame:
                button_to_delete.background_frame.deleteLater()
            button_to_delete.deleteLater()

        content.update_button_positions()
        self.save_current_layout()
        self._build_word_index()

    def _build_word_index(self) -> None:
        self.word_index: dict[str, list[tuple[str, str]]] = {}  # word_text_lc -> [(path, book_display_name)]

        buttons_to_index = []
        for btn_or_folder in self._get_content_buttons():  # Use current buttons from content
            if getattr(btn_or_folder, 'is_new_button', False): continue
            if btn_or_folder.is_folder:
                buttons_to_index.extend(b for b in btn_or_folder.sub_buttons if hasattr(b, 'path') and b.path)
            elif hasattr(btn_or_folder, 'path') and btn_or_folder.path:
                buttons_to_index.append(btn_or_folder)

        from services import WordBookService  # Local import
        for btn in buttons_to_index:
            if not (hasattr(btn, 'text') and hasattr(btn, 'color') and btn.path): continue
            try:
                words_in_book = WordBookService.list_words(btn.text(), btn.color)
                for w_data in words_in_book:
                    word_text = str(w_data.get("单词", "")).strip().lower()
                    if not word_text: continue
                    self.word_index.setdefault(word_text, []).append((btn.path, btn.text()))
            except Exception:  # pylint: disable=broad-except
                # Log error if necessary, but continue building index
                # print(f"Error indexing book {btn.text()}: {e}")
                pass

    def _on_search_text(self, text: str) -> None:
        text_l = text.strip().lower()
        self.fs.highlight_search(text, self._get_content_buttons())  # Pass current buttons

        if not text_l:
            self.view.hide_suggestions()
            return
        matches = [w for w in self.word_index if text_l in w][:50]
        self.view.show_suggestions(matches)

    def _open_word_by_text(self, word: str) -> None:
        path_bookname_pairs = self.word_index.get(word.lower(), [])
        if not path_bookname_pairs: return

        if len(path_bookname_pairs) == 1:
            self._open_wordbook(path_bookname_pairs[0][0], target_word=word)
            return

        menu = QMenu(self.view)
        for path_to_open, book_display_name in path_bookname_pairs:
            act = menu.addAction(f"在 '{book_display_name}' 中打开")
            act.triggered.connect(lambda checked=False, p=path_to_open, t=word: self._open_wordbook(p, target_word=t))

        global_pos = self.view.search_bar.mapToGlobal(self.view.search_bar.rect().bottomLeft())
        menu.exec_(global_pos)

    @Slot()
    def save_current_layout(self):
        layout_to_save = self.fs.export_layout(self._get_content_buttons())
        self.ls.save(layout_to_save)

    def _set_edit_mode(self, entering: bool) -> None:
        self.edit_mode = entering
        self.view.content.edit_mode = entering

        all_main_buttons = self._get_content_buttons()

        # Handle jitter for main buttons and the "New Book" button
        buttons_for_main_jitter = all_main_buttons[:]
        if hasattr(self.view.content, 'new_book_button'):
            buttons_for_main_jitter.append(self.view.content.new_book_button)

        for b in buttons_for_main_jitter:
            if entering:
                b.start_jitter()
            else:
                b.stop_jitter()

        if entering:
            # Expand all folders and then handle sub-button jitter
            for btn in all_main_buttons:
                if btn.is_folder:
                    if not btn.is_expanded:
                        # toggle_folder sets btn.is_expanded to True (target state)
                        self.view.content.toggle_folder(btn)
                    # Jitter sub-buttons if the folder is (or will be) expanded
                    # Need to check is_expanded *after* toggle_folder might have changed it
                    # and its animation starts. A slight delay might be needed if toggle_folder
                    # is fully async for state change.
                    # However, toggle_folder in FolderAnimationMixin sets is_expanded synchronously.
                    if btn.is_expanded:  # Check the target state
                        for sub_b in btn.sub_buttons:
                            sub_b.start_jitter()
        else:  # Exiting edit mode
            if hasattr(self.view.content, 'collapse_all_folders'):
                self.view.content.collapse_all_folders()

            # Stop jitter for all sub-buttons, regardless of folder state
            for btn in all_main_buttons:
                if btn.is_folder:
                    for sub_b in btn.sub_buttons:
                        sub_b.stop_jitter()

            self.save_current_layout()

    def _create_wordbook(self) -> None:
        success, book_name, book_color = self.fs.show_new_wordbook_dialog()
        if success and book_name and book_color:
            base_dir = os.path.dirname(os.path.abspath(sys.argv[0]))
            books_dir = os.path.join(base_dir, "books")
            new_book_folder_name = f"books_{book_name}_{book_color}"
            new_book_path = os.path.join(books_dir, new_book_folder_name)

            if os.path.exists(new_book_path):
                QMessageBox.warning(self.view, "创建失败", f"名为 '{book_name}' 的单词本已存在。")
                return
            try:
                os.makedirs(new_book_path, exist_ok=True)
                db_init_db(os.path.join(new_book_path, "wordbook.db"))
            except Exception as e:
                QMessageBox.warning(self.view, "创建失败", f"创建单词本目录或数据库失败: {e}")
                return

            self._load_buttons_and_layout()  # Reload everything to include the new book
            self._build_word_index()  # Rebuild index
            self.save_current_layout()  # Save new layout with the new book

    def _open_wordbook(self, path: str, target_word: str | None = None) -> None:
        # Allow opening folders even in edit mode for inspection (though not typical interaction)
        # Main check is usually on WordBookButton's click handler for non-folder items.
        # If self.edit_mode is True, WordBookButton's own click (if connected to this) might be blocked
        # by its own logic if it's not a folder.

        # This method is primarily for non-folder buttons or when programmatically opening.
        if self.edit_mode:
            # Check if the button associated with this path is a folder
            # This is a bit indirect. Better to check on the button itself.
            # For now, assume if _open_wordbook is called directly, we intend to open.
            pass  # Allow opening for now, WordBookButton click handles edit mode prevention better

        win = WordBookWindow(path, target_word=target_word)
        self._child_windows.append(win)
        win.setAttribute(Qt.WA_DeleteOnClose)
        win.destroyed.connect(lambda obj=win: self._child_windows.remove(obj) if obj in self._child_windows else None)
        win.show()

    def eventFilter(self, obj, event: QEvent) -> bool:
        if obj is self.view.scroll_area.viewport() and event.type() == QEvent.Type.Resize:
            if hasattr(self.view.content, 'update_button_positions'):
                # Use a QTimer to avoid potential resize loops or acting on intermediate sizes
                QTimer.singleShot(0, self.view.content.update_button_positions)
        return super().eventFilter(obj, event)

# controllers/cover_controller.py结束