# UI/new_wordbook_dialog.py
from PySide6.QtWidgets import (
    QDialog, QVBoxLayout, QLineEdit, QColorDialog, QMessageBox, QHBoxLayout
)
from PySide6.QtGui import QColor
from PySide6.QtCore import Qt
from UI.glass_effect import R2WindowMixin, R2PushButton
from UI.styles import (
    LINE_EDIT_STYLE,
    PRIMARY_BUTTON_STYLE,
    SECONDARY_BUTTON_STYLE,
)
from UI.title_bar import TitleBar


class NewWordBookDialog(R2WindowMixin, QDialog):
    """输入『名称 + 颜色』的简单对话框"""

    def __init__(self, parent=None):
        super().__init__(parent)
        self.setWindowTitle("新建单词本")
        self.setWindowFlags(Qt.FramelessWindowHint | Qt.Window)
        self.resize(320, 150)
        self.book_color: str = "#a3d2ca"   # 默认色
        self._init_r2()

        self._build_ui()
        self.book_name: str | None = None

    # ------------------------------------------------------------
    def _build_ui(self):
        root = QVBoxLayout(self)
        root.setContentsMargins(0, 0, 0, 0)
        root.setSpacing(0)
        root.addWidget(TitleBar(self, "新建单词本"))

        lay = QVBoxLayout()
        lay.setContentsMargins(20, 20, 20, 20)
        lay.setSpacing(12)
        root.addLayout(lay)

        self.name_edit = QLineEdit(placeholderText="单词本名称")
        self.name_edit.setStyleSheet(LINE_EDIT_STYLE)
        lay.addWidget(self.name_edit)

        self.color_btn = R2PushButton("选择颜色 (#a3d2ca)", radius=12)
        # setStyleSheet accepts a single string; join all rules into one
        self.color_btn.setStyleSheet(
            f"background-color: {self.book_color}; "
            "color: white; border: none; border-radius: 12px; "
            "padding: 8px 16px; font-size: 14px;"
        )
        self.color_btn.clicked.connect(self._choose_color)
        lay.addWidget(self.color_btn)

        btn_row = QHBoxLayout()
        ok_btn = R2PushButton("确定", radius=12)
        ok_btn.setStyleSheet(PRIMARY_BUTTON_STYLE)
        cancel_btn = R2PushButton("取消", radius=12)
        cancel_btn.setStyleSheet(SECONDARY_BUTTON_STYLE)
        ok_btn.clicked.connect(self._accept)
        cancel_btn.clicked.connect(self.reject)
        btn_row.addWidget(ok_btn)
        btn_row.addWidget(cancel_btn)
        lay.addLayout(btn_row)

    # ------------------------------------------------------------
    def _choose_color(self):
        c = QColorDialog.getColor(QColor(self.book_color), self, "选择颜色")
        if c.isValid():
            self.book_color = c.name()
            self.color_btn.setText(f"选择颜色 ({self.book_color})")
            self.color_btn.setStyleSheet(
                f"background-color: {self.book_color}; "
                "color: white; border: none; border-radius: 12px; "
                "padding: 8px 16px; font-size: 14px;"
            )

    def _accept(self):
        name = self.name_edit.text().strip()
        if not name:
            QMessageBox.warning(self, "错误", "名称不能为空！")
            return
        self.book_name = name
        self.accept()
