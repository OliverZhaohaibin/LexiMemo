import os
import shutil
import sys
from PySide6.QtCore import Qt
from PySide6.QtWidgets import QApplication, QWidget, QVBoxLayout, QScrollArea, QMessageBox, QMenu, QPushButton, \
    QListWidget
from PySide6.QtWidgets import QGridLayout, QLabel, QDialog, QLineEdit, QColorDialog  # for the dialog
import json

from Folder_UI.common.folderUI_API import FolderOperationMixin, FolderLayoutMixin,FolderHintMixin,FolderAnimationMixin
from font import normal_font
from inside import WordBookApp  # presumably for opening a word book content window
from WordBookButton import WordBookButton  # use our modified WordBookButton
from Folder_UI.folder_background import update_all_folder_backgrounds
from Folder_UI.utils import calculate_button_distance, is_button_in_frame
from styles import SECONDARY_BUTTON_STYLE, RED_BUTTON_STYLE, LINE_EDIT_STYLE, TEXT_EDIT_STYLE


class NewWordBookDialog(QDialog):
    def __init__(self):
        super().__init__()
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

    def choose_color(self):
        color = QColorDialog.getColor()
        if color.isValid():
            self.selected_color = color.name()
            # Show selected color on the button as background
            self.color_button.setStyleSheet(f"background-color: {self.selected_color};")
        else:
            # No color selected
            pass

    def create_word_book(self):
        name = self.name_input.text().strip()
        if not self.selected_color:
            QMessageBox.warning(self, "警告", "请选择颜色！", QMessageBox.Ok)
            return
        if not name:
            QMessageBox.warning(self, "警告", "请输入单词本名称！", QMessageBox.Ok)
            return
        base_dir = os.path.dirname(os.path.abspath(sys.argv[0]))
        directory = os.path.join(base_dir, "books")
        os.makedirs(directory, exist_ok=True)
        # Ensure name is unique
        for filename in os.listdir(directory):
            parts = filename.split('_')
            if len(parts) > 1 and parts[1] == name:
                QMessageBox.warning(self, "警告", "单词本已存在！", QMessageBox.Ok)
                return
        # Create new wordbook directory
        folder_name = f"books_{name}_{self.selected_color}"
        path = os.path.join(directory, folder_name)
        os.makedirs(path, exist_ok=True)
        # Close dialog with Accepted status
        self.accept()

class WordAppCover(
        FolderAnimationMixin,
        FolderLayoutMixin,
        FolderHintMixin,
        FolderOperationMixin,
        QWidget
):
    def __init__(self):
        """
        Cover 主界面初始化：
        • 头部一排：编辑按钮 + 搜索框
        • 下方滚动区域：单词本栅格
        """
        # ---------- 常规导入 ----------
        from PySide6.QtWidgets import (
            QLineEdit, QListWidget, QGridLayout, QScrollArea, QWidget,
            QVBoxLayout, QHBoxLayout, QPushButton, QMenu
        )
        from PySide6.QtCore import Qt, QTimer

        super().__init__()
        self.setWindowTitle("背单词程序")
        self.resize(600, 700)

        # ---------- 主栅格（存放单词本按钮） ----------
        self.grid_layout = QGridLayout()
        self.grid_layout.setSpacing(10)

        self.scroll_area = QScrollArea()
        self.scroll_area.setWidgetResizable(True)

        self.scroll_content = QWidget()
        self.scroll_content.setLayout(self.grid_layout)
        self.scroll_area.setWidget(self.scroll_content)

        # —— 随滚动刷新文件夹背景 —— #
        self.scroll_area.verticalScrollBar().valueChanged.connect(
            lambda _: update_all_folder_backgrounds(self, self.button_width, self.button_height)
        )
        self.scroll_area.horizontalScrollBar().valueChanged.connect(
            lambda _: update_all_folder_backgrounds(self, self.button_width, self.button_height)
        )

        # ---------- 总体垂直布局 ----------
        main_layout = QVBoxLayout()

        # ============= ① 头部一行：编辑按钮 + 搜索框 =============
        header_layout = QHBoxLayout()
        header_layout.setContentsMargins(0, 0, 0, 0)
        header_layout.setSpacing(10)

        # —— 编辑按钮 —— #
        self.edit_button = QPushButton("编辑")
        self.edit_button.setStyleSheet(SECONDARY_BUTTON_STYLE)
        self.edit_button.setFixedSize(60, 30)
        self.edit_button.clicked.connect(self.toggle_edit_mode)
        header_layout.addWidget(self.edit_button)

        # —— 全局搜索框 —— #
        self.search_bar = QLineEdit()
        self.search_bar.setPlaceholderText("在全部单词册内搜索 …")
        self.search_bar.setStyleSheet(TEXT_EDIT_STYLE)
        self.search_bar.setFixedHeight(33)
        self.search_bar.textChanged.connect(self.update_search_results)
        header_layout.addWidget(self.search_bar, 1)          # stretch=1 充满剩余空间
        self.search_bar.installEventFilter(self)

        # —— 下拉建议列表（浮动不抢焦点） —— #
        self.suggestions_list = QListWidget()
        self.suggestions_list.setWindowFlags(
            Qt.FramelessWindowHint | Qt.WindowStaysOnTopHint | Qt.NoDropShadowWindowHint
        )
        self.suggestions_list.setAttribute(Qt.WA_ShowWithoutActivating, True)
        self.suggestions_list.setFocusPolicy(Qt.NoFocus)
        self.suggestions_list.hide()
        self.suggestions_list.itemClicked.connect(self.on_suggestion_clicked)
        self.suggestions_list.setMouseTracking(True)
        self.suggestions_list.itemEntered.connect(self.on_suggestion_hovered)

        # —— 把头部行加入主布局 —— #
        main_layout.addLayout(header_layout)

        # ============= ② 滚动区域 =============
        main_layout.addWidget(self.scroll_area)
        self.setLayout(main_layout)

        # ---------- 逻辑参数 ----------
        self.buttons = []
        self.edit_mode = False
        self.button_width = 120
        self.button_height = 150
        self.spacing = 10
        self.folder_extra_width = 150
        self.proximity_pair = None
        self.proximity_threshold = 80
        self.frame_visible = False

        # ---------- 提示框 ----------
        from Folder_UI.frame import ButtonFrame
        self.frame = ButtonFrame(
            self.scroll_content,
            "border: 2px dashed #3498db; background-color: rgba(52, 152, 219, 0.1);",
        )
        self.red_removal_frame = ButtonFrame(
            self.scroll_content,
            "border: 2px dashed red; background-color: rgba(255, 0, 0, 0.1);",
        )
        self.red_removal_frame.hide()
        self.blue_reorder_frame = ButtonFrame(
            self.scroll_content,
            "border: 2px dashed blue; background-color: rgba(0, 0, 255, 0.1);",
        )
        self.blue_reorder_frame.hide()

        # ---------- 新建单词本按钮 ----------
        self.new_book_button = WordBookButton(
            "新建单词本", "#a3d2ca", parent=self.scroll_content, app=self
        )
        self.new_book_button.is_new_button = True
        self.new_book_button.clicked.connect(self.show_new_word_book_dialog)
        font_tmp = self.new_book_button.font()
        font_tmp.setPointSize(16)
        self.new_book_button.setFont(font_tmp)

        # ---------- 初始化数据 ----------
        self.create_red_word_book()   # 保证“总单词册”存在
        self.load_word_books()        # 会在结尾自动 build_word_index()

        # —— 保持搜索框焦点 —— #
        self.search_bar.textChanged.connect(lambda _: QTimer.singleShot(0, self.search_bar.setFocus))

    """全局搜索框的逻辑
       全局单词索引 build_word_index
       搜索逻辑 update_search_results
       点击 / 悬停处理
        """

    def build_word_index(self):
        """
        构建索引:
        {word_lower: [(book_name, color, absolute_path), …]}
        """
        import os
        from db import load_words

        base_dir = os.path.dirname(os.path.abspath(sys.argv[0]))
        books_dir = os.path.join(base_dir, "books")
        self.word_index = {}

        for folder in os.listdir(books_dir):
            if not folder.startswith("books_"):
                continue
            parts = folder.split('_', 2)
            if len(parts) < 3:
                continue
            book_name, book_color = parts[1], parts[2]
            path = os.path.join(books_dir, folder)

            try:
                words = load_words(book_name, book_color)
            except Exception as e:
                print(f"加载单词失败 {book_name}: {e}")
                continue

            for w in words:
                key = str(w["单词"]).strip().lower()
                if not key:
                    continue
                self.word_index.setdefault(key, []).append((book_name, book_color, path))

    def update_search_results(self, text: str):
        """实时刷新下拉建议列表"""
        keyword = text.strip().lower()
        if not keyword:
            self.suggestions_list.hide()
            return

        if not hasattr(self, "word_index"):
            self.build_word_index()

        matches = [w for w in self.word_index if keyword in w]
        matches.sort()
        matches = matches[:50]  # 最多 50 条

        if not matches:
            self.suggestions_list.hide()
            return

        self.suggestions_list.clear()
        self.suggestions_list.addItems(matches)

        row_h = self.suggestions_list.sizeHintForRow(0) or 24
        popup_h = min(10, len(matches)) * row_h + 2
        self.suggestions_list.setFixedSize(self.search_bar.width(), popup_h)

        global_pos = self.search_bar.mapToGlobal(self.search_bar.rect().bottomLeft())
        self.suggestions_list.move(global_pos)
        self.suggestions_list.show()
        self.suggestions_list.setCurrentRow(-1) #  初始无选中
    # ---------------------------- 下拉点击 / 悬停 ---------------------------- #
    def on_suggestion_clicked(self, item):
        """点击下拉中的某个词条"""
        word = item.text()  # 保留原大小写
        books = self.word_index.get(word.lower(), [])
        self.suggestions_list.hide()

        if not books:
            return
        if len(books) == 1:  # 只有一本 → 直接跳
            _, _, path = books[0]
            self.show_word_book(path, target_word=word)
        else:  # 多本 → 让用户选
            self._show_book_submenu(item)

    def on_suggestion_hovered(self, item):
        """悬停时同样弹出二级菜单（多册时）"""
        self._show_book_submenu(item)

    def _show_book_submenu(self, item):
        """生成『该词存在于多本时』的二级菜单"""
        word = item.text()
        books = self.word_index.get(word.lower(), [])
        if len(books) <= 1:
            return

        submenu = QMenu(self)
        for book_name, _, path in books:
            act = submenu.addAction(book_name)
            # λ 中把词也带过去，打开后直接定位
            act.triggered.connect(lambda _, p=path, w=word: self.show_word_book(p, target_word=w))

        rect = self.suggestions_list.visualItemRect(item)
        pos = self.suggestions_list.mapToGlobal(rect.topRight())
        submenu.exec_(pos)

    # ---------------------------- 打开单词册 ---------------------------- #
    def show_word_book(self, path, target_word=None):
        """
        打开指定路径下的单词本。

        Args:
            path (str): 单词本文件夹绝对路径
            target_word (str|None): 进入后若需直接展示的单词
        """
        if self.edit_mode:  # 编辑态下禁止进入
            return

        print(f"打开单词本: {path} (目标单词: {target_word})")
        self.word_book_app = WordBookApp(path, target_word=target_word)
        self.word_book_app.show()

    # ------------------------------------------------------------------ #
    #  让 ↑ ↓ ↵ 在搜索框里直接操作下拉建议列表
    # ------------------------------------------------------------------ #
    def eventFilter(self, obj, event):
        from PySide6.QtCore import QEvent, Qt
        if obj is self.search_bar and event.type() == QEvent.KeyPress:
            if self.suggestions_list.isVisible():
                key = event.key()
                row = self.suggestions_list.currentRow()
                count = self.suggestions_list.count()

                # ↓ 向下
                if key == Qt.Key_Down:
                    row = 0 if row < 0 else min(row + 1, count - 1)
                    self.suggestions_list.setCurrentRow(row)
                    self.suggestions_list.scrollToItem(
                        self.suggestions_list.currentItem(),
                        QListWidget.PositionAtCenter
                    )
                    return True

                # ↑ 向上
                elif key == Qt.Key_Up:
                    row = count - 1 if row < 0 else max(row - 1, 0)
                    self.suggestions_list.setCurrentRow(row)
                    self.suggestions_list.scrollToItem(
                        self.suggestions_list.currentItem(),
                        QListWidget.PositionAtCenter
                    )
                    return True

                # ↵ / Enter 选中
                elif key in (Qt.Key_Return, Qt.Key_Enter):
                    item = self.suggestions_list.currentItem()
                    if item:
                        self.on_suggestion_clicked(item)
                    return True  # 吞掉事件

        # 其余默认处理
        return super().eventFilter(obj, event)

    def create_red_word_book(self):
        """Create a default red '总单词册' if it doesn't exist."""
        base_dir = os.path.dirname(os.path.abspath(sys.argv[0]))
        directory = os.path.join(base_dir, "books")
        os.makedirs(directory, exist_ok=True)
        folder_name = "books_总单词册_#FF0000"
        path = os.path.join(directory, folder_name)
        if not os.path.exists(path):
            os.makedirs(path, exist_ok=True)

    def check_button_proximity(self, dragged_button):
        """
        检查拖动的主界面按钮与其它主按钮的距离，决定是否显示蓝色合并提示框。

        规则：
        1. 子按钮或“新建单词本”按钮不参与检测；
        2. 若拖动源是文件夹（禁止文件夹嵌套），直接隐藏蓝框并退出；
        3. 若拖动源是普通按钮，目标可以是普通按钮或文件夹；
        4. 当距离小于 proximity_threshold 时显示蓝框，并记录 proximity_pair，
           供后续「合并成文件夹」或「加入现有文件夹」逻辑使用。
        """
        # —— ① 子按钮 / “新建单词本”按钮 —— #
        if dragged_button.is_sub_button or getattr(dragged_button, "is_new_button", False):
            return

        # —— ② 拖动源是文件夹 ⇒ 不显示蓝框 —— #
        if dragged_button.is_folder:
            self.hide_frame()
            self.proximity_pair = None
            return

        # —— ③ 计算最近可合并目标（普通按钮或文件夹） —— #
        closest_button = None
        min_distance = float('inf')
        for btn in self.buttons:
            if btn is dragged_button or btn.is_sub_button:
                continue  # 排除自己与子按钮

            distance = calculate_button_distance(
                dragged_button, btn,
                self.button_width, self.button_height
            )
            if distance < min_distance:
                min_distance = distance
                closest_button = btn

        # —— ④ 根据距离阈值显示 / 隐藏蓝框 —— #
        if closest_button and min_distance < self.proximity_threshold:
            self.show_frame(dragged_button, closest_button)
            self.proximity_pair = (dragged_button, closest_button)
        else:
            self.hide_frame()
            self.proximity_pair = None

    # ------------------------------------------------------------
    #  布局持久化：路径工具
    # ------------------------------------------------------------
    def get_layout_file_path(self) -> str:
        """返回 cover 布局 JSON 的绝对路径"""
        base_dir = os.path.dirname(os.path.abspath(sys.argv[0]))
        return os.path.join(base_dir, "cover_layout.json")

    # ------------------------------------------------------------
    #  保存当前布局 → JSON
    # ------------------------------------------------------------
    def save_layout_to_json(self) -> None:
        """
        把当前按钮顺序 & 文件夹结构写入 cover_layout.json
        调用时机：退出编辑模式 / 应用关闭前
        """
        layout_items = []
        for btn in self.buttons:
            if getattr(btn, "is_folder", False):
                layout_items.append({
                    "type": "folder",
                    "name": btn.text(),
                    "color": getattr(btn, "color", "#a3d2ca"),
                    "is_expanded": getattr(btn, "is_expanded", False),  # 保存展开状态
                    "sub_books": [sub.text() for sub in btn.sub_buttons]
                })
            else:                 # 普通单词本按钮
                layout_items.append({
                    "type": "wordbook",
                    "name": btn.text(),
                    "color": getattr(btn, "color", "#a3d2ca")
                })

        try:
            with open(self.get_layout_file_path(), "w", encoding="utf-8") as f:
                json.dump({"layout": layout_items}, f, ensure_ascii=False, indent=2)
            print("✅  Cover 布局已保存")
        except Exception as e:
            print(f"❌  保存 cover 布局失败: {e}")

    # ------------------------------------------------------------
    #  读取 JSON 布局并还原   ✅【修复：给文件夹子按钮补 click 绑定】
    # ------------------------------------------------------------
    def apply_saved_layout(self) -> None:
        """根据 cover_layout.json 重建按钮顺序 / 文件夹层级，并确保子按钮可点击打开单词册"""
        import os, sys, json

        path = self.get_layout_file_path()
        if not os.path.exists(path):
            return  # 首次运行，文件尚不存在

        # ---------- 1. 读取 JSON ----------
        try:
            with open(path, "r", encoding="utf-8") as f:
                data = json.load(f)
            layout_items = data.get("layout", [])
        except Exception as e:
            print(f"❌  读取 cover 布局失败: {e}")
            return

        # ---------- 2. 现有按钮索引 ----------
        name_to_btn = {btn.text(): btn for btn in self.buttons}
        new_buttons, used_names = [], set()

        # 供后续 click 绑定使用
        base_dir  = os.path.dirname(os.path.abspath(sys.argv[0]))
        books_dir = os.path.join(base_dir, "books")

        # ---------- 3. 逐项重构 ----------
        for item in layout_items:
            # —— 普通单词本按钮 —— #
            if item.get("type") == "wordbook":
                btn = name_to_btn.get(item["name"])
                if btn:
                    new_buttons.append(btn)
                    used_names.add(btn.text())

            # —— 文件夹及其子按钮 —— #
            elif item.get("type") == "folder":
                folder_btn = WordBookButton(
                    item["name"],
                    item.get("color", "#a3d2ca"),
                    parent=self.scroll_content,
                    app=self,
                )
                folder_btn.is_folder   = True
                folder_btn.is_expanded = False  # 初始状态为折叠
                folder_btn.sub_buttons = []

                # --- 处理子按钮 --- #
                for sub_name in item.get("sub_books", []):
                    src_btn = name_to_btn.get(sub_name)
                    if not src_btn:
                        continue

                    # 新建子按钮
                    sub_btn = WordBookButton(
                        src_btn.text(),
                        getattr(src_btn, "color", "#a3d2ca"),
                        parent=self.scroll_content,
                        app=self,
                    )
                    sub_btn.is_sub_button  = True
                    sub_btn.parent_folder  = folder_btn
                    sub_btn.hide()  # 初始状态隐藏子按钮
                    folder_btn.sub_buttons.append(sub_btn)

                    # ⭐ 关键：绑定点击事件使其能打开单词册
                    book_dir  = f"books_{sub_btn.text()}_{sub_btn.color}"
                    book_path = os.path.join(books_dir, book_dir)
                    sub_btn.clicked.connect(lambda _, p=book_path: self.show_word_book(p))

                    # 移除原按钮
                    src_btn.setParent(None)
                    src_btn.deleteLater()
                    name_to_btn.pop(sub_name, None)
                    used_names.add(sub_name)
                
                # ⭐️ 根据子按钮生成九宫格图标
                folder_btn.update_folder_icon()
                # 只添加一次文件夹按钮到新按钮列表
                new_buttons.append(folder_btn)

        # ---------- 4. JSON 中未出现的按钮追加在末尾 ----------
        for btn_name, btn in name_to_btn.items():
            if btn_name not in used_names:
                new_buttons.append(btn)

        # ---------- 5. 应用并刷新 ----------
        self.buttons = new_buttons
        print("✅  Cover 布局已按 JSON 还原并修复子按钮点击")
        
        # ---------- 6. 绑定右键菜单 ----------
        self.bind_delete_context()  # 确保所有子按钮都有右键菜单功能

    # ------------------------------------------------------------
    #  加载单词本（修改：套用已保存的布局 → 若仍在编辑模式则恢复动画）
    # ------------------------------------------------------------
    def load_word_books(self):
        """Load all word books from the 'books' directory and display them."""
        import os
        base_dir = os.path.dirname(os.path.abspath(sys.argv[0]))
        directory = os.path.join(base_dir, "books")
        os.makedirs(directory, exist_ok=True)

        # —— 清空旧按钮 —— #
        for btn in list(self.buttons):
            if btn.is_folder:
                for sub in btn.sub_buttons:
                    sub.setParent(None)
                    sub.deleteLater()
                if hasattr(btn, "background_frame"):
                    btn.background_frame.deleteLater()
            btn.setParent(None)
            btn.deleteLater()
        self.buttons.clear()

        # —— 扫描目录创建按钮 —— #
        word_books = []
        for filename in os.listdir(directory):
            if filename.startswith("books"):
                parts = filename.split("_", 2)
                if len(parts) >= 3:
                    name, color = parts[1], parts[2]
                    button = WordBookButton(name, color, parent=self.scroll_content, app=self)
                    button.clicked.connect(
                        lambda _, p=os.path.join(directory, filename): self.show_word_book(p)
                    )
                    if name != "总单词册":
                        button.setContextMenuPolicy(Qt.CustomContextMenu)
                        button.customContextMenuRequested.connect(
                            lambda pos, b=button: self.show_context_menu(pos, b)
                        )
                    word_books.append((name, button))

        # —— 新建按钮 —— #
        if self.new_book_button.parent() is None:
            self.new_book_button.setParent(self.scroll_content)

        # —— 排序并写回 —— #
        word_books.sort(key=lambda x: (x[0] != "总单词册", x[0]))
        self.buttons = [b for _, b in word_books]

        # —— 应用保存布局 & 刷新 —— #
        self.apply_saved_layout()
        for btn in self.buttons:
            btn.show()
        self.new_book_button.show()
        self.new_book_button.raise_()
        self.update_button_positions()
        self.bind_delete_context()

        # —— 重建全局索引 —— #
        self.build_word_index()

        # --------------------------------------------------------
        # ⭐ 若仍处于编辑模式，重新恢复抖动动画 / UI 状态
        # --------------------------------------------------------
        if getattr(self, "edit_mode", False):
            # 1) 启动抖动动画
            all_buttons = self.buttons + [
                sub for btn in self.buttons if btn.is_folder for sub in btn.sub_buttons
            ]
            for b in all_buttons:
                b.start_jitter()

            # 2) “编辑”按钮保持退出风格
            self.edit_button.setText("退出")
            self.edit_button.setStyleSheet(RED_BUTTON_STYLE)

            # 3) 刷新文件夹背景框（防止位置不对）
            update_all_folder_backgrounds(self, self.button_width, self.button_height)

    # ------------------------------------------------------------
    #  编辑模式切换（修改：退出时自动保存布局）
    # ------------------------------------------------------------
    def toggle_edit_mode(self):
        """切换编辑模式：
        • 进入时 → 动画展开所有文件夹 + 开启抖动
        • 退出时 → 动画折叠所有文件夹 + 停止抖动并持久化布局
        """
        # 1) 状态取反
        self.edit_mode = not self.edit_mode

        # 2) 统一控制所有（主按钮＋子按钮）的抖动
        all_buttons = self.buttons + [
            sub for btn in self.buttons if btn.is_folder for sub in btn.sub_buttons
        ]
        for b in all_buttons:
            (b.start_jitter() if self.edit_mode else b.stop_jitter())

        # 3) 进入编辑模式 —— 动画展开全部文件夹
        if self.edit_mode:
            self.edit_button.setText("退出")
            self.edit_button.setStyleSheet(RED_BUTTON_STYLE)

            for btn in self.buttons:
                if btn.is_folder and not btn.is_expanded:
                    self.toggle_folder(btn)          # ⭐️ 带动画展开
                # 进入编辑模式后，确保子按钮也开始抖动
                for sub in btn.sub_buttons:
                    sub.start_jitter()

            # 刷新布局 & 背景
            self.update_button_positions()
            update_all_folder_backgrounds(self, self.button_width, self.button_height)

        # 4) 退出编辑模式 —— 动画折叠全部文件夹并保存
        else:
            self.edit_button.setText("编辑")
            self.edit_button.setStyleSheet(SECONDARY_BUTTON_STYLE)

            self.collapse_all_folders()             # ⭐️ 带动画折叠
            self.update_button_positions()
            self.save_layout_to_json()



    def show_new_word_book_dialog(self):
        """Open the dialog to create a new word book."""
        dialog = NewWordBookDialog()
        if dialog.exec() == QDialog.Accepted:
            # 保存新建单词本按钮的引用
            new_book_btn = self.new_book_button
            # 如果新单词本创建成功，重新加载列表
            self.load_word_books()
            # 确保新建单词本按钮可见并位于最前
            self.new_book_button.show()
            self.new_book_button.raise_()
            # 确保所有按钮都可见
            for btn in self.buttons:
                btn.show()
            # 更新按钮位置
            self.update_button_positions()

    def show_word_book(self, path, target_word=None):
        """
        打开指定路径下的单词本窗口；可选地直接跳到 target_word 的详情页。

        Args:
            path (str): 单词本文件夹绝对路径
            target_word (str|None): 进入后要自动展示的单词
        """
        if self.edit_mode:  # 编辑模式下禁止进入，避免误操作
            return

        print(f"打开单词本: {path}  (目标单词: {target_word})")

        # 若已有窗口打开，先安全关闭（防止多实例占用数据库）
        try:
            if hasattr(self, "word_book_app") and self.word_book_app:
                self.word_book_app.close()
        except Exception:
            pass

        # 创建并传递 target_word
        self.word_book_app = WordBookApp(path, target_word=target_word)
        self.word_book_app.show()

    # ------------------------------------------------------------
    #  右键菜单：删除 / 重命名 单词本
    # ------------------------------------------------------------
    def show_context_menu(self, global_pos, button):
        """
        右键菜单：删除 / 重命名

        • 位置：严格跟随鼠标 (`global_pos`)
        • 隐藏：使用 `exec_(global_pos)` + `WA_DeleteOnClose`，
          点击任意处即可立即关闭（解决菜单残留 & 需多次点击问题）
        """
        menu = QMenu(self)
        menu.setAttribute(Qt.WA_DeleteOnClose)

        # —— 删除 —— #
        delete_action = menu.addAction("删除")
        delete_action.triggered.connect(lambda _, b=button: self.delete_word_book(b))

        # —— 重命名 —— #
        rename_action = menu.addAction("重命名")
        rename_action.triggered.connect(lambda _, b=button: self.rename_word_book(b))

        menu.exec_(global_pos)

    def rename_word_book(self, button):
        """
        右键菜单触发的“重命名”：
        • 不进入全局编辑模式
        • 用 QTimer.singleShot(0, …) 等待菜单完全关闭后再显示输入框
        """
        from PySide6.QtCore import QTimer
        if not button:
            return
        QTimer.singleShot(0, lambda b=button: b.start_name_edit())

    # ------------------------------------------------------------
    #  右键菜单：真正执行删除逻辑（已修复刷新 BUG）
    # ------------------------------------------------------------

    def delete_word_book(self, button):
        """
        删除选中的单词本 / 文件夹 / 文件夹子按钮，并保持编辑模式下的临时布局。

        • 删除文件夹 → 解散文件夹，子按钮全部保留并升级为顶层按钮。
        """
        import os, sys, json, shutil
        from PySide6.QtWidgets import QMessageBox

        name = button.text()

        # ---------- A. 主单词册保护 ----------
        if name == "总单词册":
            QMessageBox.information(self, "提示", "『总单词册』是主单词册，无法删除！")
            return

        # ---------- B. 用户确认 ----------
        if QMessageBox.question(
            self, "确认删除", f"确定要删除『{name}』吗？",
            QMessageBox.Yes | QMessageBox.No
        ) != QMessageBox.Yes:
            return

        # ---------- C. 删除磁盘目录 ----------
        base_dir  = os.path.dirname(os.path.abspath(sys.argv[0]))
        books_dir = os.path.join(base_dir, "books")
        if os.path.isdir(books_dir):
            for folder in os.listdir(books_dir):
                if folder.startswith(f"books_{name}_"):
                    shutil.rmtree(os.path.join(books_dir, folder), ignore_errors=True)

        # ---------- D. 更新 cover_layout.json ----------
        layout_path = self.get_layout_file_path()
        if os.path.exists(layout_path):
            try:
                with open(layout_path, "r", encoding="utf-8") as f:
                    data = json.load(f)
            except Exception as e:
                print(f"❌  读取布局失败: {e}")
                data = {}

            new_items = []
            for item in data.get("layout", []):
                itype, iname = item.get("type"), item.get("name")

                # —— 1. 删除整个文件夹 → 子按钮顶层化 —— #
                if itype == "folder" and iname == name:
                    for sub in item.get("sub_books", []):
                        new_items.append({
                            "type": "wordbook",
                            "name": sub,
                            "color": item.get("color", "#a3d2ca")
                        })
                    continue  # 跳过原文件夹条目

                # —— 2. 删除普通顶层按钮 —— #
                if itype == "wordbook" and iname == name:
                    continue

                # —— 3. 删除文件夹子按钮 —— #
                if itype == "folder" and name in item.get("sub_books", []):
                    item["sub_books"] = [b for b in item["sub_books"] if b != name]

                    if len(item["sub_books"]) == 0:
                        continue  # 子按钮删光 → 删除整个文件夹

                    if len(item["sub_books"]) == 1:
                        # 剩最后 1 个子按钮 → 解散文件夹
                        remaining = item["sub_books"][0]
                        new_items.append({
                            "type": "wordbook",
                            "name": remaining,
                            "color": item.get("color", "#a3d2ca")
                        })
                        continue

                new_items.append(item)

            data["layout"] = new_items
            with open(layout_path, "w", encoding="utf-8") as f:
                json.dump(data, f, ensure_ascii=False, indent=4)

        # ---------- E. 刷新界面 ----------
        if self.edit_mode:
            # 只做增量更新，保持临时布局
            self._remove_button_from_memory_and_ui(button)

            # 重绘文件夹图标与位置
            for btn in self.buttons:
                if getattr(btn, "is_folder", False):
                    btn.update_folder_icon()
            self.update_button_positions()
            self.bind_delete_context()

            # 继续抖动
            for b in (self.buttons +
                      [s for btn in self.buttons if btn.is_folder for s in btn.sub_buttons]):
                b.start_jitter()
        else:
            # 非编辑模式 → 完整刷新
            self.load_word_books()

    # ------------------------------------------------------------
    #  辅助：就地从内存 & UI 移除按钮（含子按钮 / 背景框）
    # ------------------------------------------------------------
    def _remove_button_from_memory_and_ui(self, btn):
        """
        无刷新地安全删除按钮（仅编辑模式用）。

        • 删除普通按钮        → 直接删
        • 删除文件夹          → 解散文件夹，子按钮全部升级为顶层按钮
        • 删除文件夹子按钮    → 仅删自身；若文件夹剩 1/0 个子按钮则自动解散 / 删除
        """
        def _safe_delete(b):
            try:
                b.stop_jitter()
            except Exception:
                pass
            if getattr(b, "background_frame", None):
                b.background_frame.deleteLater()
            b.setParent(None)
            b.deleteLater()

        # ---------- 1. 删除顶层按钮（普通 / 文件夹） ----------
        if btn in self.buttons:
            idx = self.buttons.index(btn)

            if getattr(btn, "is_folder", False):
                # —— 解散文件夹：子按钮转为顶层 —— #
                for sub in list(btn.sub_buttons):
                    sub.is_sub_button = False
                    sub.parent_folder = None
                    sub.show()
                    self.buttons.insert(idx, sub)
                    idx += 1
                btn.sub_buttons.clear()

            # 删除按钮本身
            self.buttons.remove(btn)
            _safe_delete(btn)
            return

        # ---------- 2. 删除文件夹子按钮 ----------
        parent = getattr(btn, "parent_folder", None)
        if parent and btn in parent.sub_buttons:
            parent.sub_buttons.remove(btn)
            _safe_delete(btn)

            # a) 没子按钮 → 整个文件夹也删
            if len(parent.sub_buttons) == 0:
                if parent in self.buttons:
                    self.buttons.remove(parent)
                _safe_delete(parent)

            # b) 仅剩 1 个子按钮 → 解散文件夹
            elif len(parent.sub_buttons) == 1:
                remaining = parent.sub_buttons[0]
                remaining.is_sub_button = False
                remaining.parent_folder = None
                parent.sub_buttons.clear()

                idx = self.buttons.index(parent)
                self.buttons[idx] = remaining
                _safe_delete(parent)

    # ------------------------------------------------------------
    #  绑定右键菜单到主按钮和子按钮
    # ------------------------------------------------------------
    def bind_delete_context(self):
        """
        为主按钮及所有子按钮安装右键菜单。

        修复要点
        --------
        1. **坐标精确**：将按钮局部坐标 `local_pos` → `global_pos`；
        2. **避免重复触发**：在重新绑定前尝试 disconnect()，
           防止出现一次右键冒出多个菜单、须点多次才能消失等问题。
        """
        from PySide6.QtWidgets import QPushButton

        def attach(btn):
            btn.setContextMenuPolicy(Qt.CustomContextMenu)
            # —— 先断开旧连接，防重复 —— #
            try:
                btn.customContextMenuRequested.disconnect()
            except (TypeError, RuntimeError):
                pass

            # —— 重新连接 —— #
            btn.customContextMenuRequested.connect(
                lambda local_pos, b=btn: self.show_context_menu(
                    b.mapToGlobal(local_pos), b
                )
            )

        for btn in self.buttons:
            # 跳过「新建单词本」按钮
            if getattr(btn, "is_new_button", False):
                continue

            # 主按钮
            attach(btn)

            # 文件夹子按钮
            if getattr(btn, "is_folder", False):
                for sub in btn.sub_buttons:
                    attach(sub)


    def resizeEvent(self, event):
        """Handle window resize events by updating layout of buttons and folder backgrounds."""
        super().resizeEvent(event)
        # When window (or scroll area) width changes, reposition all buttons
        self.update_button_positions()
        update_all_folder_backgrounds(self, self.button_width, self.button_height)





if __name__ == '__main__':
    print("程序启动")
    app = QApplication(sys.argv)

    app.setFont(normal_font)
    print("设置字体完成")

    window = WordAppCover()
    window.show()
    print("主窗口显示")
    sys.exit(app.exec())
