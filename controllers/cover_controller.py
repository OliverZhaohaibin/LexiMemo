# controllers/cover_controller.py
from __future__ import annotations

import os, sys
from PySide6.QtCore import QObject, QEvent
from PySide6.QtWidgets import QMenu
from UI.cover_view import CoverView
from services.folder_service import FolderService
from services.cover_layout_service    import CoverLayoutService
from WordBookButton          import WordBookButton
from UI.word_book_inside.word_book_window import WordBookWindow
from db import load_words


class CoverController(QObject):
    """连接 CoverView ↔︎ 业务层；支持全局搜索 + 二级菜单"""

    def __init__(self, view: CoverView) -> None:
        super().__init__()
        self.view      = view
        self.fs        = FolderService()
        self.ls        = CoverLayoutService()
        self.edit_mode = False
        self._child_windows: list[WordBookWindow] = []

        # —— UI 信号 —— #
        v = self.view
        v.editToggled.connect(self._set_edit_mode)
        v.searchTextChanged.connect(self._on_search_text)
        v.suggestionSelected.connect(self._open_word_by_text)

        # —— 构建按钮 —— #
        self._load_buttons()
        self._restore_layout()
        # ⭐ 删除了 fs.layout_buttons —— CoverContent 会自行排版

        # —— 构建全局索引 —— #
        self._build_word_index()

        # —— 监听 viewport 宽度变化 —— #
        v.scroll_area.viewport().installEventFilter(self)

    # ============================================================
    #                    初始构建
    # ============================================================
    def _load_buttons(self) -> None:
        """重新扫描 books/ 并把按钮挂到 CoverContent 上"""
        self.view.clear_wordbook_buttons()
        self.buttons: list[WordBookButton] = self.fs.build_buttons(self.view.content)

        for btn in self.buttons:
            # —— 关键修改：不要再把 app 指到 Controller ——★
            # btn.app = self               ← 这一行整段删掉

            if getattr(btn, "is_new_button", False):
                btn.clicked.connect(self._create_wordbook)
            else:
                btn.clicked.connect(lambda _, p=btn.path: self._open_wordbook(p))

            self.view.add_wordbook_button(btn)

    def _restore_layout(self) -> None:
        layout = self.ls.load()
        if layout:
            self.fs.apply_layout(layout, self.buttons)

    # ============================================================
    #                     全局搜索
    # ============================================================
    def _build_word_index(self) -> None:
        """word_lower → [book_path, …]"""
        self.word_index: dict[str, list[str]] = {}
        for btn in self.buttons:
            if getattr(btn, "is_new_button", False):
                continue
            _, book_name, color = os.path.basename(btn.path).split("_", 2)
            try:
                for w in load_words(book_name, color):
                    key = str(w["单词"]).strip().lower()
                    if not key:
                        continue
                    self.word_index.setdefault(key, []).append(btn.path)
            except Exception as e:
                print("读取单词本失败:", e)

    def _on_search_text(self, text: str) -> None:
        text_l = text.strip().lower()
        self.fs.highlight_search(text, self.buttons)      # 按钮高亮

        if not text_l:
            self.view.hide_suggestions()
            return
        matches = [w for w in self.word_index if text_l in w][:50]
        self.view.show_suggestions(matches)

    # ============================================================
    #         建立二级菜单：同词存在于多个单词册
    # ============================================================
    def _open_word_by_text(self, word: str) -> None:
        paths = self.word_index.get(word.lower(), [])
        if not paths:
            return

        # —— 仅 1 本：直接打开 —— #
        if len(paths) == 1:
            self._open_wordbook(paths[0], target_word=word)
            return

        # —— 多本：弹二级菜单 —— #
        menu = QMenu(self.view)
        for p in paths:
            _, book_name, _ = os.path.basename(p).split("_", 2)
            act = menu.addAction(book_name)
            act.triggered.connect(lambda _, path=p: self._open_wordbook(path, target_word=word))

        # 菜单位置：紧贴搜索框下方
        global_pos = self.view.search_bar.mapToGlobal(self.view.search_bar.rect().bottomLeft())
        menu.exec_(global_pos)

    # ============================================================
    #                编辑模式 / 新建 / 搜索高亮
    # ============================================================
    def _set_edit_mode(self, entering: bool) -> None:
        """
        开关编辑模式：直接写入 CoverContent.edit_mode，
        停止使用 FolderService.set_edit_mode。
        """
        self.edit_mode = entering
        self.view.content.edit_mode = entering

        # 启动 / 停止按钮抖动
        for b in self.buttons:
            (b.start_jitter() if entering else b.stop_jitter())
        self.view.content.new_book_button.start_jitter() if entering else self.view.content.new_book_button.stop_jitter()

        if not entering:
            # 保存最新布局
            self.ls.save(self.fs.export_layout(self.buttons))

    def _create_wordbook(self) -> None:
        if self.fs.show_new_wordbook_dialog():
            self._load_buttons()
            self._restore_layout()
            self.fs.layout_buttons(self.view.content, self.buttons)
            self._build_word_index()           # 新单词本 → 重建索引

    # ============================================================
    #                     打开窗口
    # ============================================================
    def _open_wordbook(self, path: str, target_word: str | None = None) -> None:
        win = WordBookWindow(path, target_word=target_word)
        self._child_windows.append(win)   # 防 GC
        win.show()

    # ============================================================
    #          viewport Resize → 重新排版按钮
    # ============================================================
    def eventFilter(self, obj, event):
        """
        viewport 尺寸变化 → 让 CoverContent 重新排版
        """
        if event.type() == QEvent.Resize and obj is self.view.scroll_area.viewport():
            self.view.content.update_button_positions()
        return super().eventFilter(obj, event)