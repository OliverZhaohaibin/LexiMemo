# ui/cover_view.py
from __future__ import annotations

from PySide6.QtCore    import Qt, Signal, QEvent

from PySide6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QScrollArea,
    QPushButton, QLineEdit, QListWidget, QLabel
)
from UI.word_book_cover.cover_content import CoverContent
from UI.styles import SECONDARY_BUTTON_STYLE, TEXT_EDIT_STYLE


class CoverView(QWidget):
    """
    纯 UI：标题栏 = 编辑按钮 + 全局搜索框
    中部 = ScrollArea，内部由 Controller 绝对定位各 WordBookButton
    """

    editToggled         = Signal(bool)
    searchTextChanged   = Signal(str)
    suggestionSelected  = Signal(str)     # 用户点击 / 回车确定的词

    # ------------------------------------------------------------
    def __init__(self) -> None:
        super().__init__()
        self.setWindowTitle("背单词程序")
        self.resize(660, 720)

        # ========= ① 头部 =========
        self.edit_btn = QPushButton("编辑")
        self.edit_btn.setFixedSize(60, 30)
        self.edit_btn.setStyleSheet(SECONDARY_BUTTON_STYLE)

        self.search_bar = QLineEdit()
        self.search_bar.setPlaceholderText("在全部单词册内搜索 …")
        self.search_bar.setFixedHeight(33)
        self.search_bar.setStyleSheet(TEXT_EDIT_STYLE)
        self.search_bar.installEventFilter(self)

        head = QHBoxLayout()
        head.setContentsMargins(0, 0, 0, 0)
        head.addWidget(self.edit_btn)
        head.addWidget(self.search_bar, 1)

        # ========= ② ScrollArea =========
        self.scroll_area = QScrollArea()
        self.scroll_area.setWidgetResizable(True)

        # ⭐ 改用 CoverContent（自带文件夹功能）
        self.content = CoverContent(self.scroll_area)
        self.scroll_area.setWidget(self.content)

        # —— 初次启动提示 —— #
        self.empty_hint = QLabel("还没有单词本，点击下面的『新建单词本』按钮开始吧！", self.content)
        self.empty_hint.setAlignment(Qt.AlignCenter)

        # ========= ③ 根布局 =========
        root = QVBoxLayout(self)
        root.addLayout(head)
        root.addWidget(self.scroll_area)

        # ========= ④ 下拉建议列表 =========
        self.suggestions_list = QListWidget()
        self.suggestions_list.setWindowFlags(
            Qt.FramelessWindowHint
            | Qt.WindowStaysOnTopHint
            | Qt.NoDropShadowWindowHint
        )
        self.suggestions_list.setAttribute(Qt.WA_ShowWithoutActivating, True)
        self.suggestions_list.setFocusPolicy(Qt.NoFocus)
        self.suggestions_list.itemClicked.connect(self._on_suggestion_clicked)
        self.suggestions_list.hide()

        # ========= ⑤ 信号外发 =========
        self.edit_btn.clicked.connect(self._toggle_edit)
        self.search_bar.textChanged.connect(self.searchTextChanged)


    # ------------------------------------------------------------
    #               Controller 调用的 UI API
    # ------------------------------------------------------------
    def _toggle_edit(self) -> None:
        entering = self.edit_btn.text() == "编辑"
        self.edit_btn.setText("退出" if entering else "编辑")
        self.editToggled.emit(entering)

    # —— 清空 / 添加按钮 —— #
    def clear_wordbook_buttons(self) -> None:
        """
        删除当前所有单词本按钮，但保留“新建单词本”按钮，
        并让 CoverContent 自己维护 buttons 列表。
        """
        # CoverContent 在 build_buttons 时挂载了 .buttons
        for btn in list(getattr(self.content, "buttons", [])):
            if getattr(btn, "is_new_button", False):
                continue
            btn.setParent(None)
            btn.deleteLater()
            self.content.buttons.remove(btn)
        self.empty_hint.show()
    def add_wordbook_button(self, button: QPushButton) -> None:
        self.empty_hint.hide()
        button.setParent(self.content)
        button.show()

    # ------------------------------------------------------------
    #           下拉建议：由 Controller 调用
    # ------------------------------------------------------------
    def show_suggestions(self, words: list[str]) -> None:
        if not words:
            self.suggestions_list.hide()
            return

        self.suggestions_list.clear()
        self.suggestions_list.addItems(words)

        # 确定大小 & 位置
        row_h   = self.suggestions_list.sizeHintForRow(0) or 24
        max_row = min(8, len(words))
        self.suggestions_list.setFixedSize(
            self.search_bar.width(),
            max_row * row_h + 2
        )
        global_pos = self.search_bar.mapToGlobal(self.search_bar.rect().bottomLeft())
        self.suggestions_list.move(global_pos)
        self.suggestions_list.show()
        self.suggestions_list.setCurrentRow(0)

    def hide_suggestions(self) -> None:
        self.suggestions_list.hide()

    def _on_suggestion_clicked(self, item) -> None:
        word = item.text()
        self.hide_suggestions()
        self.search_bar.setText(word)
        self.suggestionSelected.emit(word)

    # ------------------------------------------------------------
    #      让 ↑ ↓ ↵ 在搜索框里直接操作建议列表
    # ------------------------------------------------------------
    def eventFilter(self, obj, event):
        if obj is self.search_bar and event.type() == QEvent.KeyPress:
            if not self.suggestions_list.isVisible():
                return super().eventFilter(obj, event)

            key = event.key()
            row = self.suggestions_list.currentRow()
            count = self.suggestions_list.count()

            if key == Qt.Key_Down:
                row = 0 if row < 0 else min(row + 1, count - 1)
                self.suggestions_list.setCurrentRow(row)
                return True
            elif key == Qt.Key_Up:
                row = count - 1 if row < 0 else max(row - 1, 0)
                self.suggestions_list.setCurrentRow(row)
                return True
            elif key in (Qt.Key_Return, Qt.Key_Enter):
                item = self.suggestions_list.currentItem()
                if item:
                    self._on_suggestion_clicked(item)
                return True

        return super().eventFilter(obj, event)
