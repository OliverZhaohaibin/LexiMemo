from __future__ import annotations

from datetime import datetime
from typing import List, Tuple

from PySide6.QtWidgets import (
    QWidget, QVBoxLayout, QGridLayout, QLineEdit, QTextEdit, QLabel, QPushButton, QHBoxLayout, QMessageBox
)
from PySide6.QtCore import Signal, Qt

from styles import (
    GREEN_BUTTON_STYLE, RED_BUTTON_STYLE, LINE_EDIT_STYLE, TEXT_EDIT_STYLE,
    PRIMARY_BUTTON_STYLE, SECONDARY_BUTTON_STYLE
)
from font import meaning_font, sentence_font, sentence_font_platte
from MultiSelectComboBox import MultiSelectComboBox
from utils import get_tags_path


class WordEditPanel(QWidget):
    """右侧：编辑模式。传入原 word dict 的副本进行编辑。"""

    edit_saved = Signal(dict)  # 发射保存后的完整 word dict
    cancelled = Signal()

    def __init__(self, word: dict, book_name: str, book_color: str, parent: QWidget | None = None):
        super().__init__(parent)
        self.book_name, self.book_color = book_name, book_color
        self.original = word.copy()
        self._build_ui()

    # ------------------------------------------------------------------
    # 构建界面
    # ------------------------------------------------------------------
    def _build_ui(self):
        self.layout = QVBoxLayout(self)
        # 释义-例句区
        self.meaning_grid = QGridLayout(); self.layout.addLayout(self.meaning_grid)
        self._rows: List[Tuple[QLineEdit, QTextEdit, QLabel, QLabel]] = []
        for idx, (m, e) in enumerate(zip(self.original.get("释义", []), self.original.get("例句", []))):
            self._rows.append(self._add_row(idx, m, e))
        if not self._rows:
            self._rows.append(self._add_row(0))

        ctrl = QHBoxLayout()
        btn_add = QPushButton("+"); btn_add.setFixedSize(30, 30); btn_add.setStyleSheet(GREEN_BUTTON_STYLE)
        btn_add.clicked.connect(self._add_row_clicked)
        btn_rm = QPushButton("-"); btn_rm.setFixedSize(30, 30); btn_rm.setStyleSheet(RED_BUTTON_STYLE)
        btn_rm.clicked.connect(self._remove_row_clicked)
        ctrl.addWidget(btn_add); ctrl.addWidget(btn_rm)
        self.layout.addLayout(ctrl)

        # 备注
        self.note_edit = QTextEdit(); self.note_edit.setPlainText(self.original.get("备注", ""))
        self.note_edit.setStyleSheet(TEXT_EDIT_STYLE)
        self.layout.addWidget(QLabel("备注:")); self.layout.addWidget(self.note_edit)

        # 标签多选
        self.tag_combo = MultiSelectComboBox(book_name=self.book_name, book_color=self.book_color)
        for t in self.tag_combo.allItems():
            self.tag_combo.addItem(t, t in self.original.get("标签", []))
        self.layout.addWidget(QLabel("标签:")); self.layout.addWidget(self.tag_combo)

        # 按钮
        btn_row = QHBoxLayout()
        btn_save = QPushButton("保存"); btn_save.setStyleSheet(SECONDARY_BUTTON_STYLE); btn_save.clicked.connect(self._on_save)
        btn_cancel = QPushButton("取消"); btn_cancel.setStyleSheet(RED_BUTTON_STYLE); btn_cancel.clicked.connect(lambda: self.cancelled.emit())
        btn_row.addWidget(btn_save); btn_row.addWidget(btn_cancel)
        self.layout.addLayout(btn_row)

    # ------------------------------------------------------------------
    # 行操作
    # ------------------------------------------------------------------
    def _add_row_clicked(self):
        idx = len(self._rows)
        self._rows.append(self._add_row(idx))

    def _remove_row_clicked(self):
        if len(self._rows) <= 1:
            return
        row_idx = len(self._rows) - 1
        base = row_idx * 2
        for r in (base, base + 1):
            for c in range(4):
                item = self.meaning_grid.itemAtPosition(r, c)
                if item and item.widget():
                    item.widget().deleteLater()
        self._rows.pop()

    def _add_row(self, row: int, meaning: str = "", example: str = ""):
        base_row = row * 2
        err_m = QLabel("", styleSheet="color:red;"); err_e = QLabel("", styleSheet="color:red;")
        err_m.hide(); err_e.hide()
        self.meaning_grid.addWidget(err_m, base_row, 1); self.meaning_grid.addWidget(err_e, base_row, 3)

        lab_m = QLabel(f"释义{row + 1}:"); lab_m.setFont(meaning_font)
        inp_m = QLineEdit(meaning); inp_m.setStyleSheet(LINE_EDIT_STYLE)
        lab_e = QLabel(f"例句{row + 1}:")
        lab_e.setFont(sentence_font); lab_e.setPalette(sentence_font_platte)
        inp_e = QTextEdit(); inp_e.setFixedHeight(90); inp_e.setStyleSheet(TEXT_EDIT_STYLE); inp_e.setPlainText(example)

        self.meaning_grid.addWidget(lab_m, base_row + 1, 0)
        self.meaning_grid.addWidget(inp_m, base_row + 1, 1)
        self.meaning_grid.addWidget(lab_e, base_row + 1, 2)
        self.meaning_grid.addWidget(inp_e, base_row + 1, 3)
        return inp_m, inp_e, err_m, err_e

    # ------------------------------------------------------------------
    # 保存逻辑
    # ------------------------------------------------------------------
    def _on_save(self):
        pairs: List[Tuple[str, str, QLabel, QLabel]] = []
        for inp_m, inp_e, err_m, err_e in self._rows:
            err_m.hide(); err_m.setText("")
            err_e.hide(); err_e.setText("")
            pairs.append((inp_m.text().strip(), inp_e.toPlainText().strip(), err_m, err_e))

        valid, has_pair = True, False
        for m, e, em, ee in pairs:
            if m and e:
                has_pair = True
            elif m and not e:
                ee.setText("*必填"); ee.show(); valid = False
            elif e and not m:
                em.setText("*必填"); em.show(); valid = False
        if not has_pair:
            QMessageBox.warning(self, "错误", "至少填写一对释义+例句！")
            return
        if not valid:
            return

        meanings, examples = [], []
        for m, e, *_ in pairs:
            if m and e:
                meanings.append(m); examples.append(e)

        updated = self.original.copy()
        updated.update({
            "释义": meanings,
            "例句": examples,
            "备注": self.note_edit.toPlainText().strip(),
            "标签": self.tag_combo.selectedItems(),
            "时间": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
        })
        self.edit_saved.emit(updated)
