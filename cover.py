# word_book_cover.py – 程序入口
import sys
from PySide6.QtWidgets import QApplication
from UI.font import normal_font
from UI.word_book_cover.cover_view import CoverView
from controllers.cover_controller import CoverController   # ← 路径未变

def main() -> None:
    app  = QApplication(sys.argv)
    app.setFont(normal_font)
    view = CoverView()
    CoverController(view)   # 保持引用即可
    view.show()
    sys.exit(app.exec())

if __name__ == "__main__":
    main()
