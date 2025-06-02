from __future__ import annotations

from PySide6.QtWidgets import (
    QWidget, QVBoxLayout, QLineEdit, QLabel, QPushButton,
    QScrollArea, QHBoxLayout
)
from PySide6.QtCore import Signal, Qt, QTimer

from UI.MultiSelectComboBox import MultiSelectComboBox
from services.wordbook_service import WordBookService as WS
from styles import PRIMARY_BUTTON_STYLE, SECONDARY_BUTTON_STYLE, LINE_EDIT_STYLE
from font import list_word_font
from utils import get_tags_path


class WordListPanel(QWidget):
    """左侧：搜索框 + 标签过滤 + 单词列表"""

    # --- 对外信号 --- #
    word_selected = Signal(dict)   # 单词按钮被点击，发射完整单词 dict
    add_word_click = Signal()      # "添加新单词" 按钮
    memory_click = Signal()        # "背单词" 按钮

    def __init__(self, book_name: str, book_color: str, parent: QWidget | None = None):
        super().__init__(parent)
        self.book_name = book_name
        self.book_color = book_color
        self._timer: QTimer | None = None
        self.full_words: list[dict] = []
        self._build_ui()
        self._load_tags_to_filter()
        self.reload_words()

    # ------------------------------------------------------------------
    # UI
    # ------------------------------------------------------------------
    def _build_ui(self):
        lay = QVBoxLayout(self)

        # ---- 搜索框 ---- #
        self.search_bar = QLineEdit()
        self.search_bar.setPlaceholderText("查找…")
        self.search_bar.setStyleSheet(LINE_EDIT_STYLE)
        self.search_bar.textChanged.connect(self._debounce_filter)
        lay.addWidget(self.search_bar)

        # ---- 标签过滤 ---- #
        tag_row = QHBoxLayout()
        tag_row.addWidget(QLabel("过滤标签:"))
        self.tag_filter_combo = MultiSelectComboBox(book_name=self.book_name, book_color=self.book_color)
        self.tag_filter_combo.model().itemChanged.connect(self.filter_words)
        tag_row.addWidget(self.tag_filter_combo)
        lay.addLayout(tag_row)

        # ---- 控制按钮 ---- #
        btn_add = QPushButton("添加新单词")
        btn_add.setStyleSheet(PRIMARY_BUTTON_STYLE)
        btn_add.clicked.connect(self.add_word_click)
        lay.addWidget(btn_add)

        btn_mem = QPushButton("背单词")
        btn_mem.setStyleSheet(SECONDARY_BUTTON_STYLE)
        btn_mem.clicked.connect(self.memory_click)
        lay.addWidget(btn_mem)

        # ---- 列表区 ---- #
        self._list_container = QWidget()
        self._list_layout = QVBoxLayout(self._list_container)
        self._list_layout.setAlignment(Qt.AlignTop)

        scroll = QScrollArea()
        scroll.setWidgetResizable(True)
        scroll.setWidget(self._list_container)
        lay.addWidget(scroll, 1)  # stretch

    # ------------------------------------------------------------------
    # 数据加载
    # ------------------------------------------------------------------
    def reload_words(self):
        self.full_words = WS.list_words(self.book_name, self.book_color)
        self._display_words(self.full_words)

    def _display_words(self, words: list[dict]):
        # 清空旧
        while self._list_layout.count():
            w = self._list_layout.takeAt(0).widget()
            if w:
                w.deleteLater()

        for wd in words:
            btn = QPushButton(str(wd["单词"]))
            btn.setFont(list_word_font)
            btn.clicked.connect(lambda _, d=wd: self.word_selected.emit(d))
            self._list_layout.addWidget(btn)

        self._list_layout.addStretch(1)

    # ------------------------------------------------------------------
    # 过滤逻辑
    # ------------------------------------------------------------------
    def _debounce_filter(self):
        if self._timer is None:
            self._timer = QTimer(self)
            self._timer.setSingleShot(True)
            self._timer.timeout.connect(self.filter_words)
        self._timer.start(300)

    def filter_words(self):
        kw = self.search_bar.text().strip().lower()
        tags = self.tag_filter_combo.selectedItems()

        def ok(w: dict):
            has_kw = kw in str(w["单词"]).lower()
            has_tag = not tags or any(t in w.get("标签", []) for t in tags)
            return has_kw and has_tag

        self._display_words([w for w in self.full_words if ok(w)])

    # ------------------------------------------------------------------
    # 初始化标签下拉
    # ------------------------------------------------------------------
    def _load_tags_to_filter(self):
        self.tag_filter_combo.clear()
        tags_path = get_tags_path(self.book_name, self.book_color)
        if not tags_path or not tags_path.endswith("tags.txt"):
            return
        try:
            with open(tags_path, "r", encoding="utf-8") as f:
                for t in f.read().splitlines():
                    self.tag_filter_combo.addItem(t)
        except FileNotFoundError:
            pass
