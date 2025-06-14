# controllers/cover_controller.py
from __future__ import annotations
import os
import sys
from PySide6.QtCore import QObject, QEvent, Slot, Qt, QUrl, QTimer
from PySide6.QtWidgets import QMenu, QMessageBox
from PySide6.QtGui import QDesktopServices

from UI.word_book_cover.cover_view import CoverView
from services.folder_service import FolderService
from services.cover_layout_service import CoverLayoutService
from UI.word_book_button import WordBookButton  # This now points to the enhanced WordBookButtonView
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

        import weakref
        ctrl_ref = weakref.ref(self)

        def _cleanup(*_):
            ctrl = ctrl_ref()
            vp = view.scroll_area.viewport() if view.scroll_area else None
            if ctrl and vp:
                vp.removeEventFilter(ctrl)

        view.destroyed.connect(_cleanup)

    def _get_content_buttons(self) -> list[WordBookButton]:
        if hasattr(self.view.content, 'buttons'):
            return self.view.content.buttons
        return []

    def _load_buttons_and_layout(self) -> None:
        self.view.clear_wordbook_buttons()

        scanned_buttons = self.fs.build_buttons(self.view.content)  # This populates self.view.content.buttons

        nb = self.view.content.new_book_button
        # The 'clicked' signal for the main "new_book_button" is special and leads to _create_wordbook
        # Other buttons' 'openRequested' is for opening existing wordbooks.
        try:
            nb.clicked.disconnect()  # Standard QPushButton signal
        except (RuntimeError, TypeError):
            pass
        nb.clicked.connect(self._create_wordbook)
        self._wire_button_signals(nb)  # Wire other common signals

        current_buttons_in_content = self.view.content.buttons  # Get the list populated by build_buttons
        for btn in current_buttons_in_content:
            self._wire_button_signals(btn)

        layout = self.ls.load()
        if layout:
            self.fs.apply_layout(layout, current_buttons_in_content)
            # apply_layout might change the order or structure within self.view.content.buttons
            # Re-wire signals for buttons that might have been re-instantiated or reconfigured by apply_layout
            # This is a bit tricky. Ideally, apply_layout should return the final list or ensure signals remain.
            # For now, assume apply_layout works with existing instances mostly.
            # If apply_layout creates NEW button instances, those also need wiring.
            # A simpler approach: wire after apply_layout if it returns the definitive list.
            # current_buttons_in_content = self.view.content.buttons # Refresh after apply_layout
            # for btn in current_buttons_in_content:
            #     self._wire_button_signals(btn)

        self.view.content.update_button_positions()

    def _wire_button_signals(self, btn: WordBookButton):
        """Helper to connect signals for a given button."""
        self._wire_context_menu(btn)

        # ViewModel style connections for rename/delete actions
        if hasattr(btn, 'renameRequested'):
            try:
                btn.renameRequested.disconnect(self._handle_button_rename)
            except (TypeError, RuntimeError):
                pass
            btn.renameRequested.connect(self._handle_button_rename)

        if hasattr(btn, 'deleteRequested'):
            handler = getattr(btn, "_del_handler", None)
            if handler:
                try:
                    btn.deleteRequested.disconnect(handler)
                except (TypeError, RuntimeError):
                    pass
            handler = lambda b=btn: self.delete_word_book(b)
            btn._del_handler = handler
            btn.deleteRequested.connect(handler)

        # For opening regular wordbooks (not folders, not the new_book_button)
        if hasattr(btn, 'openRequested') and not btn.is_folder and not getattr(btn, 'is_new_button', False):
            try:
                btn.openRequested.disconnect()
            except (TypeError, RuntimeError):
                pass
            btn.openRequested.connect(lambda p=btn.path: self._open_wordbook(p) if p else None)

        # For saving layout after name change via inline edit
        if hasattr(btn, 'nameChangedNeedsLayoutSave'):
            try:
                btn.nameChangedNeedsLayoutSave.disconnect(self.save_current_layout)
            except (TypeError, RuntimeError):
                pass
            btn.nameChangedNeedsLayoutSave.connect(self.save_current_layout)

    def _handle_button_rename(self, new_name: str):
        # This slot receives new_name from button's renameRequested signal
        # The sender() is the button itself
        button_renamed = self.sender()
        if not isinstance(button_renamed, WordBookButton):
            return

        old_name = button_renamed.text()  # Actual current text before service rename
        old_path = button_renamed.path

        if not new_name or new_name == old_name:
            return  # No actual change

        try:
            if not button_renamed.is_folder:
                # For wordbooks, the button's internal rename_wordbook_directory handles filesystem
                # This is a bit of a violation of single responsibility, ideally service layer handles fs.
                # For now, let's assume button's internal logic is called by it,
                # or we call a service method here.
                # If the button itself calls rename_wordbook_directory upon successful name change by user:
                new_path = button_renamed.rename_wordbook_directory(old_name, new_name)
                button_renamed.path = new_path

            button_renamed.setText(new_name)  # Update text on the button widget

            if button_renamed.is_folder:
                button_renamed.update_folder_icon()
            elif button_renamed.is_sub_button and button_renamed.parent_folder:
                button_renamed.parent_folder.update_folder_icon()

            # Reconnect openRequested signal if path changed for a wordbook
            if not button_renamed.is_folder and not getattr(button_renamed, 'is_new_button', False) and hasattr(
                    self.view.content, "show_word_book") and button_renamed.path:
                try:
                    button_renamed.openRequested.disconnect()
                except(RuntimeError, TypeError):
                    pass
                button_renamed.openRequested.connect(
                    lambda p=button_renamed.path: self.view.content.show_word_book(p) if p else None)

            self.view.content.update_button_positions()  # Update visual layout
            self.save_current_layout()  # Persist change
            self._build_word_index()  # Rebuild search index

        except Exception as e:
            QMessageBox.warning(self.view, "重命名失败", f"重命名 '{old_name}' 失败: {e}")
            # Revert UI changes if service call failed
            button_renamed.setText(old_name)
            if not button_renamed.is_folder:
                button_renamed.path = old_path
            # Potentially revert icon too if needed
            return

    def _wire_context_menu(self, btn: WordBookButton) -> None:
        try:
            btn.customContextMenuRequested.disconnect()
        except (RuntimeError, TypeError):
            pass
        btn.setContextMenuPolicy(Qt.CustomContextMenu)
        btn.customContextMenuRequested.connect(
            lambda pos, b=btn: self._show_button_context_menu(pos, b)
        )

    def _show_button_context_menu(self, pos, button: WordBookButton):
        # Check if it's the specific new_book_button instance from CoverContent
        is_the_main_new_book_btn = hasattr(self.view.content, 'new_book_button') and \
                                   button is self.view.content.new_book_button

        if is_the_main_new_book_btn and not self.edit_mode:  # No menu for new_book_button in non-edit mode
            return

        menu = QMenu(self.view)
        # Rename for any button (except the main new_book_button) in edit mode
        if self.edit_mode and not is_the_main_new_book_btn:
            rename_action = menu.addAction("重命名")
            rename_action.triggered.connect(lambda b=button: self._rename_button_from_context(b))

        # Delete for any button (except the main new_book_button)
        if not is_the_main_new_book_btn:
            delete_action = menu.addAction("删除")
            # delete_action.triggered.connect(lambda b=button: self.delete_word_book(b))
            # Connect to button's deleteRequested signal which is already wired to self.delete_word_book
            delete_action.triggered.connect(button.deleteRequested)

        # Open location for non-folders, non-main_new_book_button
        if not button.is_folder and button.path and not is_the_main_new_book_btn:
            open_folder_action = menu.addAction("打开文件位置")
            open_folder_action.triggered.connect(lambda b=button: self._open_book_location(b))

        if menu.actions():
            menu.exec_(button.mapToGlobal(pos))

    def _rename_button_from_context(self, button: WordBookButton):
        button.rename_source = "context_menu"  # Set source for finish_name_edit
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

            # Delete associated data and folder
            try:
                if button_to_delete.path and os.path.isdir(button_to_delete.path):
                    # First, delete DB entries related to this specific book path
                    # This requires knowing book_name and color from the sub-button
                    book_name_to_del = button_to_delete.text()
                    color_to_del = button_to_delete.color_str  # Use color_str
                    db_delete_word_directly(book_name_to_del, color_to_del, "%")  # Deletes all words from its DB
                    shutil.rmtree(button_to_delete.path)  # Then remove folder
            except Exception as e:
                QMessageBox.warning(self.view, "删除子项文件失败", f"删除 '{button_to_delete.text()}' 的文件失败: {e}")

            button_to_delete.hide()
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
                        if sub_btn.path and os.path.isdir(sub_btn.path):
                            db_delete_word_directly(sub_btn.text(), sub_btn.color_str, "%")
                            shutil.rmtree(sub_btn.path)
                    except Exception as e:
                        QMessageBox.warning(self.view, "删除子项文件失败",
                                            f"删除文件夹内 '{sub_btn.text()}' 的文件失败: {e}")
                    sub_btn.hide()
                    sub_btn.deleteLater()
            else:  # Single wordbook (not a folder)
                try:
                    if button_to_delete.path and os.path.isdir(button_to_delete.path):
                        db_delete_word_directly(button_to_delete.text(), button_to_delete.color_str, "%")
                        shutil.rmtree(button_to_delete.path)
                except Exception as e:
                    QMessageBox.warning(self.view, "删除文件失败", f"删除 '{button_to_delete.text()}' 的文件失败: {e}")

            if hasattr(button_to_delete, 'background_frame') and button_to_delete.background_frame:
                button_to_delete.background_frame.deleteLater()
            button_to_delete.hide()
            button_to_delete.deleteLater()

        content.update_button_positions()
        self.save_current_layout()
        self._build_word_index()

    def _build_word_index(self) -> None:
        self.word_index: dict[str, list[tuple[str, str]]] = {}

        buttons_to_index = []
        for btn_or_folder in self._get_content_buttons():
            if getattr(btn_or_folder, 'is_new_button', False): continue  # Skip the "new book" button itself
            if btn_or_folder.is_folder:
                buttons_to_index.extend(b for b in btn_or_folder.sub_buttons if hasattr(b, 'path') and b.path)
            elif hasattr(btn_or_folder, 'path') and btn_or_folder.path:
                buttons_to_index.append(btn_or_folder)

        from services import WordBookService
        for btn in buttons_to_index:
            if not (hasattr(btn, 'text') and hasattr(btn, 'color_str') and btn.path): continue
            try:
                words_in_book = WordBookService.list_words(btn.text(), btn.color_str)  # Use color_str
                for w_data in words_in_book:
                    word_text = str(w_data.get("单词", "")).strip().lower()
                    if not word_text: continue
                    self.word_index.setdefault(word_text, []).append((btn.path, btn.text()))
            except Exception:
                pass

    def _on_search_text(self, text: str) -> None:
        text_l = text.strip().lower()
        self.fs.highlight_search(text, self._get_content_buttons())

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
        # Ensure CoverContent's buttons list is up-to-date before exporting
        if hasattr(self.view.content, 'update_button_positions'):
            self.view.content.update_button_positions()  # Ensure positions are current

        layout_to_save = self.fs.export_layout(self._get_content_buttons())
        self.ls.save(layout_to_save)

    def _set_edit_mode(self, entering: bool) -> None:
        self.edit_mode = entering
        self.view.content.edit_mode = entering

        all_buttons_for_jitter = self._get_content_buttons()[:]  # Operate on a copy
        if hasattr(self.view.content, 'new_book_button'):
            all_buttons_for_jitter.append(self.view.content.new_book_button)

        for b in all_buttons_for_jitter:
            if entering:
                b.start_jitter()
            else:
                b.stop_jitter()

        if entering:
            # Expand folders and jitter sub-buttons
            for btn in self._get_content_buttons():  # Iterate original list for folder operations
                if btn.is_folder:
                    if not btn.is_expanded:
                        self.view.content.toggle_folder(btn)  # This will trigger animations
                    # Jitter sub-buttons *after* the folder is set to be expanded
                    # The toggle_folder method should ensure sub_buttons are visible for jitter if expanding
                    # A slight delay might be needed if animations are long, but start_jitter itself is visual.
                    # Let's assume toggle_folder makes them available for jittering quickly enough.
                    QTimer.singleShot(50, lambda b_folder=btn: [sub.start_jitter() for sub in b_folder.sub_buttons if
                                                                b_folder.is_expanded])

        else:  # Exiting edit mode
            if hasattr(self.view.content, 'collapse_all_folders'):
                self.view.content.collapse_all_folders()  # This will animate

            # Stop jitter for all sub-buttons after a delay to allow collapse animation to start/finish
            def stop_all_sub_jitters():
                for btn_main in self._get_content_buttons():
                    if btn_main.is_folder:
                        for sub_b in btn_main.sub_buttons:
                            sub_b.stop_jitter()

            QTimer.singleShot(600, stop_all_sub_jitters)  # Adjust delay as needed based on collapse anim duration

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

            self._load_buttons_and_layout()
            self._build_word_index()
            self.save_current_layout()

    def _open_wordbook(self, path: str | None, target_word: str | None = None) -> None:
        if not path:
            # This might happen if a button without a path somehow tries to open
            # print("Warning: Attempted to open wordbook with no path.")
            return

        if self.edit_mode:  # Generally, don't open wordbooks in edit mode
            # print("Edit mode active, opening wordbook prevented by controller.")
            return

        win = WordBookWindow(path, target_word=target_word)
        self._child_windows.append(win)
        win.setAttribute(Qt.WA_DeleteOnClose)
        win.destroyed.connect(lambda obj=win: self._child_windows.remove(obj) if obj in self._child_windows else None)
        win.show()

    def eventFilter(self, obj, event: QEvent) -> bool:
        if obj is self.view.scroll_area.viewport() and event.type() == QEvent.Type.Resize:
            if hasattr(self.view.content, 'update_button_positions'):
                QTimer.singleShot(0, self.view.content.update_button_positions)
        return super().eventFilter(obj, event)