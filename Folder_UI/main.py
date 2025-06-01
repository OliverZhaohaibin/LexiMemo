import sys
from PySide6.QtWidgets import QApplication
from app import DraggableFolderApp


if __name__ == "__main__":
    app = QApplication(sys.argv)
    window = DraggableFolderApp()
    window.show()
    sys.exit(app.exec())