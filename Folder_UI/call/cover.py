#cover.py
print("开始导入模块")
import os
print("导入os模块成功")
import shutil
print("导入shutil模块成功")
import sys
print("导入sys模块成功")

print("开始导入PySide6模块")
from PySide6.QtCore import Qt
print("导入Qt成功")
from PySide6.QtWidgets import (
    QApplication, QWidget, QVBoxLayout, QColorDialog,
    QLineEdit, QDialog, QLabel, QScrollArea, QGridLayout, QMessageBox, QMenu, QPushButton
)
print("导入PySide6.QtWidgets组件成功")

print("开始导入自定义模块")
from WordBookButton import WordBookButton
print("导入WordBookButton成功")
from font import normal_font
print("导入normal_font成功")

print("导入WordBookApp成功")

class NewWordBookDialog(QDialog):
    def __init__(self):
        super().__init__()
        print("初始化 NewWordBookDialog")
        self.setWindowTitle("新建单词本")
        self.resize(300, 150)
        self.selected_color = None

        layout = QVBoxLayout()
        self.name_label = QLabel("单词本名称:")
        self.name_input = QLineEdit()
        self.color_label = QLabel("选择颜色:")
        self.color_button = QPushButton("选择")
        self.color_button.clicked.connect(self.choose_color)
        self.create_button = QPushButton("创建")
        self.create_button.clicked.connect(self.create_word_book)

        layout.addWidget(self.name_label)
        layout.addWidget(self.name_input)
        layout.addWidget(self.color_label)
        layout.addWidget(self.color_button)
        layout.addWidget(self.create_button)
        self.setLayout(layout)
        print("NewWordBookDialog 初始化完成")

    def choose_color(self):
        print("选择颜色对话框打开")
        color = QColorDialog.getColor()
        if color.isValid():
            self.selected_color = color.name()
            self.color_button.setStyleSheet(f"background-color: {self.selected_color};")
            print(f"已选择颜色: {self.selected_color}")
        else:
            print("未选择颜色")

    def create_word_book(self):
        print("开始创建单词本")
        name = self.name_input.text().strip()
        if not self.selected_color:
            print("警告: 未选择颜色")
            QMessageBox.warning(self, "警告", "请选择颜色！", QMessageBox.Ok)
            return
        if not name:
            print("警告: 未输入单词本名称")
            QMessageBox.warning(self, "警告", "请输入单词本名称！", QMessageBox.Ok)
            return

        base_dir = os.path.dirname(os.path.abspath(sys.argv[0]))
        directory = os.path.join(base_dir, "books")
        print(f"单词本目录: {directory}")
        os.makedirs(directory, exist_ok=True)

        for filename in os.listdir(directory):
            parts = filename.split('_')
            if len(parts) > 1 and parts[1] == name:
                print(f"警告: 单词本 '{name}' 已存在")
                QMessageBox.warning(self, "警告", "单词本已存在！", QMessageBox.Ok)
                return

        folder_name = f"books_{name}_{self.selected_color}"
        path = os.path.join(directory, folder_name)
        os.makedirs(path, exist_ok=True)
        print(f"成功创建单词本: {path}")
        self.accept()


class WordAppCover(QWidget):
    def __init__(self):
        super().__init__()
        print("初始化 WordAppCover")
        self.setWindowTitle("背单词程序")
        self.resize(600, 700)

        self.grid_layout = QGridLayout()
        self.grid_layout.setSpacing(10)  # 设置按钮间距
        self.word_book_buttons = []

        self.scroll_area = QScrollArea()
        self.scroll_area.setWidgetResizable(True)
        self.scroll_content = QWidget()
        self.scroll_content.setLayout(self.grid_layout)
        self.scroll_area.setWidget(self.scroll_content)

        main_layout = QVBoxLayout()
        main_layout.addWidget(self.scroll_area)
        self.setLayout(main_layout)

        self.new_book_button = WordBookButton("新建单词本", "#a3d2ca")
        self.new_book_button.button.clicked.connect(self.show_new_word_book_dialog)
        self.new_book_button.button.setStyleSheet("""
            QPushButton {
                background-color: transparent;
                border: none;
                font-size: 16px;
                text-align: center;
            }
            QPushButton::hover {
                background-color: #92b4a7;
                border-radius: 15px;  /* 设置圆角半径，可根据需要调整 */
            }
            QPushButton::pressed{
                background-color: #a3d2ca;
                border-radius: 15px;  /* 设置圆角半径，可根据需要调整 */
            }
        """)

        print("开始创建红色总单词册")
        self.create_red_word_book()  # 创建红色的总单词册
        print("开始加载单词本")
        self.load_word_books()
        print("WordAppCover 初始化完成")

    def create_red_word_book(self):
        base_dir = os.path.dirname(os.path.abspath(sys.argv[0]))
        directory = os.path.join(base_dir, "books")
        os.makedirs(directory, exist_ok=True)
        folder_name = "books_总单词册_#FF0000"
        path = os.path.join(directory, folder_name)
        if not os.path.exists(path):
            os.makedirs(path, exist_ok=True)
            print(f"创建总单词册: {path}")
        else:
            print("总单词册已存在")

    def load_word_books(self):
        print("加载单词本开始")
        base_dir = os.path.dirname(os.path.abspath(sys.argv[0]))
        directory = os.path.join(base_dir, "books")
        os.makedirs(directory, exist_ok=True)

        self.word_book_buttons = []

        word_books = []
        print(f"扫描目录: {directory}")
        for filename in os.listdir(directory):
            if filename.startswith("books"):
                parts = filename.split('_')
                name = parts[1]
                color = parts[2]
                print(f"发现单词本: {name}, 颜色: {color}")
                button = WordBookButton(name, color)
                button.button.clicked.connect(lambda _, p=os.path.join(directory, filename): self.show_word_book(p))
                if name != "总单词册":
                    button.button.setContextMenuPolicy(Qt.CustomContextMenu)
                    button.button.customContextMenuRequested.connect(
                        lambda pos, b=button: self.show_context_menu(pos, b))
                word_books.append((name, button))

        word_books.sort(key=lambda x: x[0] != "总单词册")
        self.word_book_buttons = [wb[1] for wb in word_books]
        print(f"加载了 {len(self.word_book_buttons)} 个单词本")

        self.update_grid_layout()
        print("单词本加载完成")

    def update_grid_layout(self):
        print("更新网格布局开始")
        for i in reversed(range(self.grid_layout.count())):
            widget = self.grid_layout.itemAt(i).widget()
            if widget:
                widget.setParent(None)

        row = 0
        col = 0
        max_cols = 3  # 每行最多显示3个按钮
        for button in self.word_book_buttons:
            self.grid_layout.addWidget(button, row, col, alignment=Qt.AlignCenter)
            col += 1
            if col >= max_cols:
                col = 0
                row += 1

        self.grid_layout.addWidget(self.new_book_button, row, col, alignment=Qt.AlignCenter)
        print(f"网格布局更新完成: {row+1}行 x {max_cols}列")

    def show_new_word_book_dialog(self):
        print("打开新建单词本对话框")
        dialog = NewWordBookDialog()
        if dialog.exec() == QDialog.Accepted:
            print("单词本创建成功，重新加载单词本")
            self.load_word_books()
        else:
            print("取消创建单词本")

    def show_word_book(self, path):
        print(f"打开单词本: {path}")

        self.word_book_app.show()

    def show_context_menu(self, pos, button):
        print(f"显示上下文菜单: {button.label.text()}")
        menu = QMenu(self)
        delete_action = menu.addAction("删除")
        delete_action.triggered.connect(lambda: self.delete_word_book(button))
        menu.exec_(self.mapToGlobal(pos))

    def delete_word_book(self, button):
        name = button.label.text()
        print(f"开始删除单词本: {name}")
        directory = "./books"
        for folder in os.listdir(directory):
            if folder.startswith(f"books_{name}_"):
                path = os.path.join(directory, folder)
                if os.path.exists(path):
                    print(f"删除目录: {path}")
                    shutil.rmtree(path)
        print("重新加载单词本")
        self.load_word_books()


if __name__ == '__main__':
    print("程序启动")
    app = QApplication(sys.argv)

    app.setFont(normal_font)
    print("设置字体完成")

    window = WordAppCover()
    window.show()
    print("主窗口显示")
    sys.exit(app.exec())
