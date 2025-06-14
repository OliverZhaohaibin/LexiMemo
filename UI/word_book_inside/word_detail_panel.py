from __future__ import annotations

from collections import OrderedDict

from PySide6.QtWidgets import (
    QWidget, QVBoxLayout, QLabel, QTextEdit, QPushButton,
    QTabBar, QScrollArea, QFrame,
)
from PySide6.QtCore import Signal, Qt

from styles import PRIMARY_BUTTON_STYLE, TEXT_EDIT_STYLE, LINE_EDIT_STYLE, TAG_LABEL_STYLE
from font import meaning_font, main_word_font, sentence_font, sentence_font_platte, list_word_font

class WordDetailPanel(QWidget):
    """右侧只读详情视图。"""

    edit_requested = Signal(dict)   # 当用户点击“编辑”

    def __init__(self, parent: QWidget | None = None):
        super().__init__(parent)
        self._section_widgets: dict[str, QWidget] = {}
        self._build_ui()
        self._current_word: dict | None = None

    # ------------------------------------------------------------------
    def _build_ui(self):
        self.layout = QVBoxLayout(self)
        self.word_label = QLabel()
        self.word_label.setFont(main_word_font)
        self.word_label.setAlignment(Qt.AlignCenter)
        self.layout.addWidget(self.word_label)

        # 顶部标签栏（仅用于跳转）
        self.tab_bar = QTabBar(movable=False)
        self.tab_bar.tabBarClicked.connect(self._jump_to_section)
        self.layout.addWidget(self.tab_bar)

        # ScrollArea 容纳所有内容
        self.scroll = QScrollArea()
        self.scroll.setWidgetResizable(True)
        self.scroll_widget = QWidget()
        self.scroll_layout = QVBoxLayout(self.scroll_widget)
        self.scroll.setWidget(self.scroll_widget)
        self.layout.addWidget(self.scroll, 1)

        # 占位——无数据时
        self.placeholder = QLabel("请选择左侧单词…", alignment=Qt.AlignCenter)
        self.scroll_layout.addWidget(self.placeholder)

        self._btn_edit = None

    # ------------------------------------------------------------------
    def show_word(self, word: dict):
        self._current_word = word
        self.placeholder.hide()
        self.word_label.setText(str(word["单词"]))

        # 清空旧内容
        self._section_widgets.clear()
        while self.tab_bar.count():
            self.tab_bar.removeTab(0)
        for i in reversed(range(self.scroll_layout.count())):
            item = self.scroll_layout.itemAt(i)
            w = item.widget()
            if w and w is not self.placeholder:
                w.setParent(None)
                w.deleteLater()
        self.scroll_layout.removeWidget(self.placeholder)
        self.scroll_layout.insertWidget(0, self.placeholder)
        self.placeholder.hide()

        # 构建『释义 & 例句』
        self._build_meaning_example_section(word)
        # 备注
        self._build_note_section(word)
        # 标签
        self._build_tag_section(word)
        # 相关单词
        self._build_related_section(word)

        self.scroll_layout.addStretch(1)

        # 编辑按钮
        if self._btn_edit is None:
            self._btn_edit = QPushButton("编辑")
            self._btn_edit.setStyleSheet(PRIMARY_BUTTON_STYLE)
            self._btn_edit.clicked.connect(lambda: self.edit_requested.emit(self._current_word))
            self.layout.addWidget(self._btn_edit)

    # ------------------------------------------------------------------
    def _jump_to_section(self, index: int):
        text = self.tab_bar.tabText(index)
        widget = self._section_widgets.get(text)
        if widget:
            self.scroll.ensureWidgetVisible(widget)

    # ------------------------------------------------------------------
    def _build_meaning_example_section(self, w: dict):
        wid = QWidget(); lay = QVBoxLayout(wid)
        meanings, examples = w.get("释义", []), w.get("例句", [])
        if len(examples) < len(meanings):
            examples += [""] * (len(meanings) - len(examples))
        grouped: OrderedDict[str, list[str]] = OrderedDict()
        for m, e in zip(meanings, examples):
            grouped.setdefault(str(m).strip(), [])
            if e:
                grouped[str(m).strip()].append(e)

        for idx, (m, exs) in enumerate(grouped.items(), start=1):
            self._add_row(lay, f"释义{idx}:", m, multiline=False, bold=True)
            if exs:
                for j, ex in enumerate(exs, start=1):
                    self._add_row(lay, f"例句{idx}.{j}:", ex, multiline=True)
            else:
                self._add_row(lay, f"例句{idx}.1:", "", multiline=True)
            if idx < len(grouped):
                sep = QFrame(); sep.setFrameShape(QFrame.HLine); sep.setFrameShadow(QFrame.Sunken)
                lay.addWidget(sep)
        self.scroll_layout.addWidget(wid)
        self.tab_bar.addTab("释义 & 例句")
        self._section_widgets["释义 & 例句"] = wid

    def _build_note_section(self, w: dict):
        wid = QWidget(); lay = QVBoxLayout(wid)
        self._add_row(lay, "备注:", w.get("备注", "无备注"), multiline=True)
        self.scroll_layout.addWidget(wid)
        self.tab_bar.addTab("备注")
        self._section_widgets["备注"] = wid

    def _build_tag_section(self, w: dict):
        wid = QWidget(); lay = QVBoxLayout(wid)
        tags = w.get("标签", [])
        txt = ", ".join(tags) if tags else "无标签"
        self._add_row(lay, "标签:", txt)
        self.scroll_layout.addWidget(wid)
        self.tab_bar.addTab("标签")
        self._section_widgets["标签"] = wid

    def _build_related_section(self, w: dict):
        rel = w.get("相关单词", [])
        txt = ", ".join(rel) if rel else "无"
        wid = QWidget(); lay = QVBoxLayout(wid)
        self._add_row(lay, "关联单词:", txt)
        self.scroll_layout.addWidget(wid)
        self.tab_bar.addTab("相关")
        self._section_widgets["相关"] = wid

    # ------------------------------------------------------------------
    def _add_row(self, layout: QVBoxLayout, label_text: str, content: str, *, multiline=False, bold=False):
        lbl = QLabel(label_text)
        if bold:
            lbl.setFont(meaning_font)
        layout.addWidget(lbl)
        if multiline:
            te = QTextEdit()
            te.setReadOnly(True)
            te.setStyleSheet(TEXT_EDIT_STYLE)
            te.setPlainText(str(content))
            te.setFixedHeight(90)
            layout.addWidget(te)
        else:
            val = QLabel(str(content))
            layout.addWidget(val)
