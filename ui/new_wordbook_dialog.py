# ui/new_wordbook_dialog.py
from PySide6.QtWidgets import (
    QDialog, QVBoxLayout, QLineEdit, QPushButton, QDialogButtonBox,
    QColorDialog, QMessageBox
)
from PySide6.QtGui import QColor


class NewWordBookDialog(QDialog):
    """输入『名称 + 颜色』的简单对话框"""

    def __init__(self, parent=None):
        super().__init__(parent)
        self.setWindowTitle("新建单词本")
        self.resize(320, 150)

        self._build_ui()
        self.book_name: str | None = None
        self.book_color: str = "#a3d2ca"   # 默认色

    # ------------------------------------------------------------
    def _build_ui(self):
        lay = QVBoxLayout(self)

        self.name_edit = QLineEdit(placeholderText="单词本名称")
        lay.addWidget(self.name_edit)

        self.color_btn = QPushButton("选择颜色 (#a3d2ca)")
        self.color_btn.clicked.connect(self._choose_color)
        lay.addWidget(self.color_btn)

        btns = QDialogButtonBox(QDialogButtonBox.Ok | QDialogButtonBox.Cancel)
        btns.accepted.connect(self._accept)
        btns.rejected.connect(self.reject)
        lay.addWidget(btns)

    # ------------------------------------------------------------
    def _choose_color(self):
        c = QColorDialog.getColor(QColor(self.book_color), self, "选择颜色")
        if c.isValid():
            self.book_color = c.name()
            self.color_btn.setText(f"选择颜色 ({self.book_color})")
            self.color_btn.setStyleSheet(f"background:{self.book_color}")

    def _accept(self):
        name = self.name_edit.text().strip()
        if not name:
            QMessageBox.warning(self, "错误", "名称不能为空！")
            return
        self.book_name = name
        self.accept()