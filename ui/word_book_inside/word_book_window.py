from __future__ import annotations

import os
from PySide6.QtWidgets import QSplitter, QWidget, QVBoxLayout, QApplication
from PySide6.QtCore import Qt

from ui.word_book_inside.word_list_panel import WordListPanel
from ui.word_book_inside.word_detail_panel import WordDetailPanel
from ui.word_book_inside.word_edit_panel import WordEditPanel
from services.wordbook_service import WordBookService as WS


class WordBookWindow(QWidget):
    """顶层壳（替代原 inside.WordBookApp）。"""

    def __init__(self, path: str, target_word: str | None = None):
        super().__init__()
        self.path = path
        self.book_name = os.path.basename(path).split("_")[1]
        self.book_color = os.path.basename(path).split("_")[2]
        self.setWindowTitle(f"单词本 - {self.book_name}")
        self.resize(1200, 800)

        self._build_ui()
        if target_word:
            self._jump_to_word(target_word)

    # ------------------------------------------------------------------
    def _build_ui(self):
        lay = QVBoxLayout(self)
        self.split = QSplitter(Qt.Horizontal)
        self.list_panel = WordListPanel(self.book_name, self.book_color)
        self.list_panel.word_selected.connect(self._on_word_selected)
        self.list_panel.add_word_click.connect(self._on_add_word)
        self.list_panel.memory_click.connect(self._on_memory)
        self.split.addWidget(self.list_panel)

        self.detail_panel = WordDetailPanel()
        self.detail_panel.edit_requested.connect(self._enter_edit_mode)
        self.split.addWidget(self.detail_panel)
        self.split.setSizes([350, 850])
        lay.addWidget(self.split)

        self._current_word: dict | None = None
        self._dlg_add = None  # 保留对话框引用，避免被 GC

    # ------------------------------------------------------------------
    # 交互
    # ------------------------------------------------------------------
    def _on_word_selected(self, word: dict):
        self._current_word = word
        self.detail_panel.show_word(word)

    def _on_add_word(self):
        from add_new_word import WordEntryUI
        # 保持引用，避免立即被销毁
        self._dlg_add = WordEntryUI(self.path)
        self._dlg_add.save_successful.connect(lambda *_: self.list_panel.reload_words())
        self._dlg_add.show()

    def _on_memory(self):
        from memory_curve import MemoryCurveApp
        self._mem = MemoryCurveApp(self.path)
        self._mem.show()

    # ------------------------------------------------------------------
    # 编辑
    # ------------------------------------------------------------------
    def _enter_edit_mode(self, word: dict):
        self._edit_panel = WordEditPanel(word, self.book_name, self.book_color)
        self._edit_panel.edit_saved.connect(self._save_edit)
        self._edit_panel.cancelled.connect(self._exit_edit_mode)
        self.split.replaceWidget(1, self._edit_panel)

    def _save_edit(self, updated: dict):
        try:
            WS.save_word(self.book_name, self.book_color, updated)
            self.list_panel.reload_words()
            self._current_word = updated
        except Exception as exc:
            from PySide6.QtWidgets import QMessageBox
            QMessageBox.warning(self, "错误", str(exc))
            return
        self._exit_edit_mode()

    def _exit_edit_mode(self):
        self.split.replaceWidget(1, self.detail_panel)
        if self._current_word:
            self.detail_panel.show_word(self._current_word)

    # ------------------------------------------------------------------
    def _jump_to_word(self, word_name: str):
        for w in WS.list_words(self.book_name, self.book_color):
            if str(w["单词"]).strip().lower() == str(word_name).strip().lower():
                self._on_word_selected(w)
                break


if __name__ == "__main__":
    import sys

    if len(sys.argv) < 2:
        print("需要传入 books_... 文件夹路径！")
        sys.exit(1)

    app = QApplication(sys.argv)
    win = WordBookWindow(sys.argv[1])
    win.show()
    sys.exit(app.exec())
