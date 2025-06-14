from __future__ import annotations

from collections import OrderedDict

from PySide6.QtWidgets import (
    QWidget, QVBoxLayout, QLabel, QTextEdit, QPushButton, QTabWidget, QFrame,
)
from PySide6.QtCore import Signal, Qt

from styles import PRIMARY_BUTTON_STYLE, TEXT_EDIT_STYLE, LINE_EDIT_STYLE, TAG_LABEL_STYLE
from font import (
    meaning_font,
    main_word_font,
    sentence_font,
    sentence_font_platte,
    list_word_font,
    normal_font,
)

class WordDetailPanel(QWidget):
    """右侧只读详情视图。"""

    edit_requested = Signal(dict)   # 当用户点击“编辑”

    def __init__(self, parent: QWidget | None = None):
        super().__init__(parent)
        self._build_ui()
        self._current_word: dict | None = None

    # ------------------------------------------------------------------
    def _build_ui(self):
        self.layout = QVBoxLayout(self)
        self.word_label = QLabel()
        self.word_label.setFont(main_word_font)
        self.word_label.setAlignment(Qt.AlignCenter)
        self.layout.addWidget(self.word_label)

        self.tab = QTabWidget()
        self.layout.addWidget(self.tab, 1)

        # 占位——无数据时
        self.placeholder = QLabel("请选择左侧单词…", alignment=Qt.AlignCenter)
        self.layout.addWidget(self.placeholder)

    # ------------------------------------------------------------------
    def show_word(self, word: dict):
        self._current_word = word
        self.placeholder.hide()
        self.word_label.setText(str(word["单词"]))

        # 清空旧 tab
        while self.tab.count():
            self.tab.removeTab(0)

        # 构建『释义 & 例句』
        self._build_meaning_example_tab(word)
        # 备注
        self._build_note_tab(word)
        # 标签
        self._build_tag_tab(word)
        # 相关单词
        self._build_related_tab(word)

        # 编辑按钮
        if not hasattr(self, "_btn_edit"):
            self._btn_edit = QPushButton("编辑")
            self._btn_edit.setStyleSheet(PRIMARY_BUTTON_STYLE)
            self._btn_edit.clicked.connect(lambda: self.edit_requested.emit(self._current_word))
            self.layout.addWidget(self._btn_edit)

    # ------------------------------------------------------------------
    def _build_meaning_example_tab(self, w: dict):
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
        self.tab.addTab(wid, "释义 & 例句")

    def _build_note_tab(self, w: dict):
        wid = QWidget(); lay = QVBoxLayout(wid)
        self._add_row(lay, "备注:", w.get("备注", "无备注"), multiline=True)
        self.tab.addTab(wid, "备注")

    def _build_tag_tab(self, w: dict):
        wid = QWidget(); lay = QVBoxLayout(wid)
        tags = w.get("标签", [])
        if tags:
            row = QHBoxLayout()
            lbl = QLabel("标签:")
            lbl.setFont(normal_font)
            row.addWidget(lbl)
            for t in tags:
                tag_lbl = QLabel(str(t))
                tag_lbl.setStyleSheet(TAG_LABEL_STYLE)
                row.addWidget(tag_lbl)
            row.addStretch(1)
            lay.addLayout(row)
        else:
            self._add_row(lay, "标签:", "无标签")
        self.tab.addTab(wid, "标签")

    def _build_related_tab(self, w: dict):
        rel = w.get("相关单词", [])
        txt = ", ".join(rel) if rel else "无"
        wid = QWidget(); lay = QVBoxLayout(wid)
        self._add_row(lay, "关联单词:", txt)
        self.tab.addTab(wid, "相关")

    # ------------------------------------------------------------------
    def _add_row(self, layout: QVBoxLayout, label_text: str, content: str, *, multiline=False, bold=False):
        lbl = QLabel(label_text)
        lbl.setFont(meaning_font if bold else normal_font)
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
            val.setFont(normal_font)
            layout.addWidget(val)
