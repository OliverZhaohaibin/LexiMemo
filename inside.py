# inside.py
print("有进入inside尝试")
import os
import sys
from PySide6.QtCore import Qt
from PySide6.QtWidgets import (
    QApplication, QWidget, QVBoxLayout, QLineEdit, QLabel, QPushButton, QHBoxLayout, QMessageBox,
    QScrollArea, QTextEdit, QInputDialog, QTabWidget, QGridLayout, QFrame, QSplitter,
    QSizePolicy
)

from MultiSelectComboBox import MultiSelectComboBox
print("inside前置加载成功")
from add_new_word import WordEntryUI
print("add new word加载成功")
from font import meaning_font, main_word_font, list_word_font, sentence_font, sentence_font_platte, note_font
print("开始加载utils")
from utils import get_excel_path, get_tags_path, get_total_tags_path, get_note_text
from datetime import datetime

from styles import PRIMARY_BUTTON_STYLE, SECONDARY_BUTTON_STYLE, TEXT_EDIT_STYLE, LINE_EDIT_STYLE, SCROLL_AREA_STYLE, \
    TAG_LABEL_STYLE, GREEN_BUTTON_STYLE, RED_BUTTON_STYLE, NOTE_TEXT_EDIT_STYLE
from business_logic import get_all_words, save_word
print("inside导入所有模块成功")

class WordBookApp(QWidget):
    def __init__(self, path, target_word=None):
        super().__init__()
        self.path = path  # 保存传入的路径
        self.book_name = os.path.basename(path).split('_')[1]  # 获取单词本名称
        self.book_color = os.path.basename(path).split('_')[2]  # 获取单词本颜色
        self.target_word = target_word
        self.init_ui()
        self.load_words()
        # 若指定了目标单词，立即跳转
        if self.target_word:
            self.jump_to_word(self.target_word)
        self.search_query = ""  # 用于存储搜索栏的文本

    def jump_to_word(self, word_name: str):
        """在列表中定位并展示指定单词；若未找到则静默忽略"""
        word_key = str(word_name).strip().lower()
        # ① 展开详情
        for w in self.word_data:
            if str(w["单词"]).strip().lower() == word_key:
                self.display_word_details(w)
                break

        # ② 左侧按钮滚动可见并临时高亮
        for i in range(self.word_list_layout.count()):
            btn = self.word_list_layout.itemAt(i).widget()
            if btn and str(btn.text()).strip().lower() == word_key:
                self.word_list_scroll_area.ensureWidgetVisible(btn)
                # 简单高亮（可在 styles.py 自行美化）
                btn.setStyleSheet(btn.styleSheet() + "background-color:#D6EAF8;")
                break


    def init_ui(self):
        self.setWindowTitle("单词书")
        self.resize(1200, 800)
        self.setStyleSheet(SCROLL_AREA_STYLE)

        main_layout = QVBoxLayout(self)
        
        # 创建QSplitter用于左右布局
        self.splitter = QSplitter(Qt.Horizontal)
        
        left_container = self.create_left_layout()
        right_container = QWidget()
        right_container.setLayout(self.create_right_layout())
        
        self.splitter.addWidget(left_container)
        self.splitter.addWidget(right_container)
        
        # 设置初始分割比例，左侧占30%
        self.splitter.setSizes([300, 700])
        
        main_layout.addWidget(self.splitter)
        self.setLayout(main_layout)

    def create_left_layout(self):
        left_layout = QVBoxLayout()
        left_container = QWidget()
        left_container.setLayout(left_layout)
        left_container.setSizePolicy(QSizePolicy.Preferred, QSizePolicy.Expanding)
        left_container.setMinimumWidth(150)  # 设置最小宽度

        # 搜索框
        self.search_bar = QLineEdit()
        self.search_bar.setPlaceholderText("查找")
        self.search_bar.setStyleSheet(LINE_EDIT_STYLE)
        self.search_bar.textChanged.connect(self.filter_words_debounce)
        left_layout.addWidget(self.search_bar)

        # 标签过滤器
        self.tag_filter_label = QLabel("过滤标签:")
        left_layout.addWidget(self.tag_filter_label)

        self.tag_filter_combo = MultiSelectComboBox(book_name=self.book_name, book_color=self.book_color)
        self.load_tags_to_filter()
        self.tag_filter_combo.model().itemChanged.connect(self.filter_words)
        left_layout.addWidget(self.tag_filter_combo)

        self.add_word_button = QPushButton("添加新单词")
        self.add_word_button.clicked.connect(self.show_add_word_dialog)
        self.add_word_button.setStyleSheet(PRIMARY_BUTTON_STYLE)
        left_layout.addWidget(self.add_word_button)
        
        # 添加背单词按钮
        self.memory_button = QPushButton("背单词")
        self.memory_button.clicked.connect(self.show_memory_curve)
        self.memory_button.setStyleSheet(SECONDARY_BUTTON_STYLE)  # 使用蓝色样式
        left_layout.addWidget(self.memory_button)
        
        self.word_list_widget = QWidget()
        self.word_list_layout = QVBoxLayout(self.word_list_widget)

        self.word_list_scroll_area = QScrollArea()
        self.word_list_scroll_area.setWidgetResizable(True)
        self.word_list_scroll_area.setWidget(self.word_list_widget)
        left_layout.addWidget(self.word_list_scroll_area)

        return left_container

    def create_right_layout(self):
        right_layout = QVBoxLayout()

        # 添加显示单词的标签
        self.word_label = QLabel()
        self.word_label.setFont(main_word_font)
        self.word_label.setAlignment(Qt.AlignCenter)
        right_layout.addWidget(self.word_label)

        self.details_layout = QVBoxLayout()
        self.details_layout.setAlignment(Qt.AlignTop)

        self.details_container = QWidget()
        self.details_container.setLayout(self.details_layout)

        right_scroll_area = QScrollArea()
        right_scroll_area.setWidgetResizable(True)
        right_scroll_area.setWidget(self.details_container)
        right_layout.addWidget(right_scroll_area)
        return right_layout

    def filter_words_debounce(self):
        """文本框修改的节流函数"""
        self.search_query = self.search_bar.text().strip().lower()
        if not hasattr(self, 'filter_timer'):
            from PySide6.QtCore import QTimer
            self.filter_timer = QTimer()
            self.filter_timer.timeout.connect(self.filter_words)
        self.filter_timer.stop()
        self.filter_timer.start(300)  # 设置节流时间

    def load_words(self):
        self.word_data = get_all_words(self.book_name, self.book_color)
        self.display_word_list(self.word_data)

    def load_tags_to_filter(self):
        self.tag_filter_combo.clear()
        tags_path = get_tags_path(self.book_name, self.book_color)
        if os.path.exists(tags_path):
            with open(tags_path, "r", encoding="utf-8") as file:
                tags = file.read().splitlines()
                for tag in tags:
                    self.tag_filter_combo.addItem(tag)

    def display_word_list(self, words):
        self.clear_layout(self.word_list_layout)
        for word in words:
            button = QPushButton(str(word["单词"]))
            button.setFont(list_word_font)
            button.clicked.connect(lambda _, w=word: self.display_word_details(w))
            self.word_list_layout.addWidget(button)

    def filter_words(self):
        query = self.search_query  # 用户输入的搜索词
        selected_tags = self.tag_filter_combo.selectedItems()  # 获取选中的标签列表

        if not selected_tags:  # 如果没有选中任何标签，显示所有匹配搜索词的单词
            filtered_words = [word for word in self.word_data if query.lower() in str(word["单词"]).lower()]
        else:  # 根据选中的标签和搜索词过滤单词
            filtered_words = [
                word for word in self.word_data
                if query.lower() in str(word["单词"]).lower()
                   and any(tag in word.get("标签", []) for tag in selected_tags)
            ]
        self.display_word_list(filtered_words)  # 显示过滤后的单词列表

    def display_word_details(self, word):
        """
        展示单词详情：
        1) 同一释义只显示一次；
        2) 该释义下所有例句按 例句x.1、例句x.2 … 编号；
        3) 每组『释义 + 例句列表』之间绘制一条分割线。
        """
        from collections import OrderedDict
        from PySide6.QtWidgets import QFrame  # ← 新增

        # ---------- 0. UI 初始化 ----------
        self.clear_layout(self.details_layout)
        self.word_detail_widgets = {}
        self.current_word = word
        self.current_word_index = next(
            (idx for idx, w in enumerate(self.word_data) if w["单词"] == word["单词"]), -1
        )
        self.word_label.setText(str(word["单词"]))

        # -------------- 1. 分组『释义-例句』--------------
        meanings = word.get("释义", [])
        examples = word.get("例句", [])
        if len(examples) < len(meanings):
            examples += [""] * (len(meanings) - len(examples))

        grouped: "OrderedDict[str, list[str]]" = OrderedDict()
        for m, e in zip(meanings, examples):
            key = str(m).strip()
            grouped.setdefault(key, [])
            if e:
                grouped[key].append(e)

        # -------------- 2. 构建 UI --------------
        tab_widget = QTabWidget()
        self.details_layout.addWidget(tab_widget)

        # (a) 释义 & 例句面板
        meaning_example_widget = QWidget()
        meaning_example_layout = QVBoxLayout(meaning_example_widget)

        total_groups = len(grouped)
        for m_idx, (m_text, ex_list) in enumerate(grouped.items(), start=1):
            # —— 释义行 —— #
            self.word_detail_widgets[f"释义{m_idx}"] = self.add_detail_row(
                f"释义{m_idx}:", m_text, layout=meaning_example_layout
            )

            # —— 例句行 —— #
            if ex_list:
                for e_idx, ex in enumerate(ex_list, start=1):
                    label = f"例句{m_idx}.{e_idx}:"
                    key = f"例句{m_idx}.{e_idx}"
                    self.word_detail_widgets[key] = self.add_detail_row(
                        label, ex, is_multiline=True, layout=meaning_example_layout
                    )
            else:
                key = f"例句{m_idx}.1"
                self.word_detail_widgets[key] = self.add_detail_row(
                    f"例句{m_idx}.1:", "", is_multiline=True, layout=meaning_example_layout
                )

            # —— 分割线（除最后一组外） —— #
            if m_idx < total_groups:
                separator = QFrame()
                separator.setFrameShape(QFrame.HLine)
                separator.setFrameShadow(QFrame.Sunken)
                separator.setStyleSheet("color:#e0e0e0; margin:6px 0;")
                meaning_example_layout.addWidget(separator)

        tab_widget.addTab(meaning_example_widget, "释义 & 例句")

        # (b) 备注面板
        note_widget, note_layout = QWidget(), QVBoxLayout()
        note_widget.setLayout(note_layout)
        note_label = QLabel("备注:")
        note_label.setFont(meaning_font)
        note_layout.addWidget(note_label)
        from utils import get_note_text
        note_edit = QTextEdit()
        note_edit.setPlainText(str(get_note_text(self, word)))
        note_edit.setReadOnly(True)
        note_edit.setStyleSheet(NOTE_TEXT_EDIT_STYLE)
        note_edit.setFont(note_font)
        note_edit.setMinimumHeight(100)
        note_layout.addWidget(note_edit)
        self.word_detail_widgets["备注"] = note_edit
        tab_widget.addTab(note_widget, "备注")

        # (c) 标签面板
        tags_widget, tags_layout = QWidget(), QVBoxLayout()
        tags_widget.setLayout(tags_layout)
        tags_display = ", ".join(word.get("标签", [])) or "无标签"
        self.word_detail_widgets["标签"] = self.add_detail_row(
            "标签:", tags_display, layout=tags_layout
        )
        tab_widget.addTab(tags_widget, "标签")

        # (d) 相关单词与编辑按钮
        self.add_related_words(word.get("相关单词", []))

        self.edit_button = QPushButton("编辑")
        self.edit_button.clicked.connect(self.enable_editing)
        self.edit_button.setStyleSheet(PRIMARY_BUTTON_STYLE)
        self.details_layout.addWidget(self.edit_button)

    def add_detail_row(self, label_text, content_text, is_multiline=False, layout=None):
        if layout is None:
            layout = self.details_layout
        label = QLabel(label_text)
        if label_text.startswith("释义"):
            label.setFont(meaning_font)
        if label_text.startswith("例句"):
            label.setFont(sentence_font)
            label.setPalette(sentence_font_platte)
        layout.addWidget(label)

        content = None  # 初始化 content 变量

        if is_multiline:
            content = QTextEdit()
            content.setPlainText(str(content_text))
            content.setFixedHeight(90)
            content.setReadOnly(True)
            content.setStyleSheet(TEXT_EDIT_STYLE)
            layout.addWidget(content)
        elif label_text == "标签:":
            # 创建标签容器
            tag_container = QWidget()
            tag_layout = QHBoxLayout(tag_container)
            tag_layout.setContentsMargins(0, 0, 0, 0)
            tag_layout.setSpacing(5)  # 设置标签之间的间距
            if isinstance(content_text, str):
                tags = content_text.split(',')
            elif isinstance(content_text, list):
                tags = content_text
            else:
                tags = []
            for tag in tags:
                tag = tag.strip()
                if tag:
                    tag_label = QLabel(tag)
                    tag_label.setStyleSheet(TAG_LABEL_STYLE)  # 使用 styles.py 中的样式
                    tag_layout.addWidget(tag_label)
            layout.addWidget(tag_container)


        else:
            content = QLineEdit()
            content.setText(str(content_text))
            content.setReadOnly(True)
            content.setStyleSheet(LINE_EDIT_STYLE)
            layout.addWidget(content)

        return content

    def add_related_words(self, related_words):
        if hasattr(self, 'related_words_layout'):
            if self.related_words_layout is not None:
                self.clear_layout(self.related_words_layout)
                self.related_words_layout.setParent(None)
                del self.related_words_layout

        if related_words:
            self.related_words_layout = QHBoxLayout()
            label = QLabel("关联单词:")
            label.setFont(meaning_font)
            self.details_layout.addWidget(label)

            self.related_words_widgets = []
            for word in related_words:
                if word in [wd["单词"] for wd in self.word_data]:
                    button = QPushButton(word)
                    button.setFont(list_word_font)
                    button.clicked.connect(lambda _, w=word: self.display_word_details_by_name(w))
                    self.related_words_layout.addWidget(button)
                    self.related_words_widgets.append(button)
                else:
                    label = QLabel(word)
                    label.setFont(list_word_font)
                    self.related_words_layout.addWidget(label)
                    self.related_words_widgets.append(label)
            self.details_layout.addLayout(self.related_words_layout)
        else:
            self.related_words_layout = None
            self.related_words_widgets = []

    def display_word_details_by_name(self, word_name):
        word = next(w for w in self.word_data if w["单词"] == word_name)
        self.display_word_details(word)

    def enable_editing(self) -> None:
        """
        切换到“可编辑”视图。
        拆分后仅做流程调度，可在 20 行内一目了然：
            1) 清空旧 UI
            2) 构建各区域（释义例句 / 关联单词 / 备注 / 标签）
            3) 放置“保存 / 取消”按钮
        """
        if not getattr(self, "current_word", None):
            return

        self._reset_detail_layout()
        self._build_meaning_example_editor()
        self._build_related_words_editor()
        self._build_note_editor()
        self._build_tag_editor()
        self._build_action_buttons()

    def _reset_detail_layout(self) -> None:
        """彻底清空详情区域并重置缓存引用。"""
        self.clear_layout(self.details_layout)
        self.word_detail_widgets: dict[str, QWidget] = {}
        for attr in (
                "meaning_example_grid",
                "related_words_layout",
                "note_edit",
                "tag_combobox",
        ):
            if hasattr(self, attr):
                delattr(self, attr)

    def _build_meaning_example_editor(self) -> None:
        """创建『释义-例句』网格及 +/- 控制按钮。"""
        self.meaning_example_layout = QVBoxLayout()
        self.meaning_example_grid: QGridLayout = QGridLayout()
        self.meaning_inputs: list[tuple[QLineEdit, QTextEdit, QLabel, QLabel]] = []
        self.meaning_example_layout.addLayout(self.meaning_example_grid)

        # ① 现有数据 → 输入行
        cur = self.current_word
        for idx, (m, e) in enumerate(
                zip(cur.get("释义", []), cur.get("例句", [])), start=0
        ):
            self.meaning_inputs.append(self.add_meaning_example_pair(idx, m, e))
        if not self.meaning_inputs:
            self.meaning_inputs.append(self.add_meaning_example_pair(0))

        # ② +/- 按钮
        add_btn = QPushButton("+");
        add_btn.setFixedSize(30, 30)
        add_btn.setStyleSheet(GREEN_BUTTON_STYLE)
        add_btn.clicked.connect(self.add_meaning_example_row)

        rm_btn = QPushButton("-");
        rm_btn.setFixedSize(30, 30)
        rm_btn.setStyleSheet(RED_BUTTON_STYLE)
        rm_btn.clicked.connect(self.remove_meaning_example_row)

        ctrl = QHBoxLayout();
        ctrl.addWidget(add_btn);
        ctrl.addWidget(rm_btn)
        self.meaning_example_layout.addLayout(ctrl)
        self.details_layout.addLayout(self.meaning_example_layout)

    def _build_related_words_editor(self) -> None:
        """创建关联单词的可增删列表。"""
        self.related_words_layout = QVBoxLayout()
        title = QLabel("关联单词:");
        self.details_layout.addWidget(title)

        self.related_words_widgets: list[QLineEdit] = []
        for w in self.current_word.get("相关单词", []):
            self._add_related_word_row(w)

        add_btn = QPushButton("添加关联单词")
        add_btn.setStyleSheet(PRIMARY_BUTTON_STYLE)
        add_btn.clicked.connect(self.add_related_word)
        self.details_layout.addLayout(self.related_words_layout)
        self.details_layout.addWidget(add_btn)

    def _add_related_word_row(self, word: str = "") -> None:
        row_w = QWidget();
        row_lay = QHBoxLayout(row_w)
        inp = QLineEdit(word);
        inp.setStyleSheet(LINE_EDIT_STYLE)
        del_btn = QPushButton("删除");
        del_btn.setStyleSheet(PRIMARY_BUTTON_STYLE)
        del_btn.clicked.connect(lambda _, r=row_w: self.delete_related_word(r))
        row_lay.addWidget(inp);
        row_lay.addWidget(del_btn)

        self.related_words_layout.addWidget(row_w)
        self.related_words_widgets.append(inp)

    def _build_note_editor(self) -> None:
        """备注区域——总单词册只读，其余可编辑。"""
        self.details_layout.addWidget(QLabel("备注:"))
        self.note_edit = QTextEdit()
        self.note_edit.setPlainText(str(get_note_text(self, self.current_word)))
        self.note_edit.setStyleSheet(TEXT_EDIT_STYLE)
        self.note_edit.setReadOnly(self.book_name == "总单词册")
        self.details_layout.addWidget(self.note_edit)

    def _build_tag_editor(self) -> None:
        """多选标签下拉 + 新建按钮。"""
        self.details_layout.addWidget(QLabel("标签:"))
        self.tag_combobox = MultiSelectComboBox(
            book_name=self.book_name, book_color=self.book_color
        )

        tags_path = get_tags_path(self.book_name, self.book_color)
        existing = []
        if os.path.exists(tags_path):
            with open(tags_path, "r", encoding="utf-8") as f:
                existing = f.read().splitlines()

        for tag in existing:
            checked = tag in self.current_word.get("标签", [])
            self.tag_combobox.addItem(tag, checked)

        self.details_layout.addWidget(self.tag_combobox)

        new_tag_btn = QPushButton("新建标签")
        new_tag_btn.setStyleSheet(PRIMARY_BUTTON_STYLE)
        new_tag_btn.clicked.connect(self.add_new_tag)
        self.details_layout.addWidget(new_tag_btn)

    def _build_action_buttons(self) -> None:
        """底部『保存 / 取消』按钮。"""
        save_btn = QPushButton("保存");
        save_btn.setStyleSheet(SECONDARY_BUTTON_STYLE)
        cancel_btn = QPushButton("取消");
        cancel_btn.setStyleSheet(RED_BUTTON_STYLE)
        save_btn.clicked.connect(self.save_edits)
        cancel_btn.clicked.connect(self.cancel_edits)

        row = QHBoxLayout();
        row.addWidget(save_btn);
        row.addWidget(cancel_btn)
        self.details_layout.addLayout(row)

        # 记录引用，供其它方法访问
        self.edit_button = save_btn
        self.cancel_button = cancel_btn

    def add_new_tag(self):
        tag, ok = QInputDialog.getText(self, "新建标签", "输入新标签:")
        if ok and tag:
            tags_path = get_tags_path(self.book_name, self.book_color)
            if os.path.exists(tags_path):
                with open(tags_path, "r", encoding="utf-8") as file:
                    existing_tags = file.read().splitlines()
            else:
                existing_tags = []

            if tag in existing_tags:
                QMessageBox.warning(self, "警告", "该标签已存在！", QMessageBox.Ok)
            else:
                with open(tags_path, "a", encoding="utf-8") as file:
                    file.write(tag + "\n")
                self.load_tags_to_filter()  # 重新加载标签到筛选框
                self.tag_combobox.addItem(tag)  # 添加新标签到选择框中

            # 更新总单词册中的标签文件
            total_tags_path = get_total_tags_path()
            os.makedirs(os.path.dirname(total_tags_path), exist_ok=True)
            if os.path.exists(total_tags_path):
                with open(total_tags_path, "r", encoding="utf-8") as file:
                    total_existing_tags = file.read().splitlines()
            else:
                total_existing_tags = []

            if tag not in total_existing_tags:
                with open(total_tags_path, "a", encoding="utf-8") as file:
                    file.write(tag + "\n")

    def add_meaning_example_pair(self, row, meaning="", example=""):
        """
        与 add_new_word.py 中实现相同的两行布局（含隐藏错误标签）。
        """
        base_row = row * 2
        meaning_err = QLabel("")
        meaning_err.setStyleSheet("color: red;")
        meaning_err.hide()
        example_err = QLabel("")
        example_err.setStyleSheet("color: red;")
        example_err.hide()
        self.meaning_example_grid.addWidget(meaning_err, base_row, 1)
        self.meaning_example_grid.addWidget(example_err, base_row, 3)

        meaning_label = QLabel(f"释义{row + 1}:")
        meaning_label.setFont(meaning_font)
        meaning_input = QLineEdit()
        meaning_input.setFixedSize(180, 30)
        meaning_input.setStyleSheet(LINE_EDIT_STYLE)
        meaning_input.setText(meaning)

        example_label = QLabel(f"例句{row + 1}:")
        example_input = QTextEdit()
        example_input.setFixedSize(300, 90)
        example_input.setStyleSheet(TEXT_EDIT_STYLE)
        example_input.setPlainText(example)

        self.meaning_example_grid.addWidget(meaning_label, base_row + 1, 0)
        self.meaning_example_grid.addWidget(meaning_input, base_row + 1, 1)
        self.meaning_example_grid.addWidget(example_label, base_row + 1, 2)
        self.meaning_example_grid.addWidget(example_input, base_row + 1, 3)

        return (meaning_input, example_input, meaning_err, example_err)

    def add_meaning_example_row(self):
        row = len(self.meaning_inputs)
        self.meaning_inputs.append(self.add_meaning_example_pair(row))

    def remove_meaning_example_row(self):
        """删除最后一对释义-例句输入行（含错误提示行）。"""
        if len(self.meaning_inputs) <= 1:
            return

        pair_index = len(self.meaning_inputs) - 1
        base_row   = pair_index * 2          # 第 0 行是错误提示，第 1 行是真正输入

        # ① 移除网格中的控件（两行 × 4 列）
        for grid_row in (base_row, base_row + 1):
            for col in range(4):
                item = self.meaning_example_grid.itemAtPosition(grid_row, col)
                if item:
                    w = item.widget()
                    if w:
                        w.setParent(None)
                        w.deleteLater()

        # ② 同步更新缓存列表
        self.meaning_inputs.pop()

    def add_new_tag(self):
        tag, ok = QInputDialog.getText(self, "新建标签", "输入新标签:")
        if ok and tag:
            tags_path = get_tags_path(self.book_name, self.book_color)
            if os.path.exists(tags_path):
                with open(tags_path, "r", encoding="utf-8") as file:
                    existing_tags = file.read().splitlines()
            else:
                existing_tags = []

            if tag in existing_tags:
                QMessageBox.warning(self, "警告", "该标签已存在！", QMessageBox.Ok)
            else:
                with open(tags_path, "a", encoding="utf-8") as file:
                    file.write(tag + "\n")
                self.load_tags_to_filter()  # 重新加载标签到筛选框
                self.tag_combobox.addItem(tag)  # 添加新标签到选择框中

            # 更新总单词册中的标签文件
            total_tags_path = get_total_tags_path()
            os.makedirs(os.path.dirname(total_tags_path), exist_ok=True)
            if os.path.exists(total_tags_path):
                with open(total_tags_path, "r", encoding="utf-8") as file:
                    total_existing_tags = file.read().splitlines()
            else:
                total_existing_tags = []

            if tag not in total_existing_tags:
                with open(total_tags_path, "a", encoding="utf-8") as file:
                    file.write(tag + "\n")

    def delete_related_word(self, widget):
        widget.setParent(None)
        self.related_words_layout.removeWidget(widget)
        self.related_words_widgets = [w for w in self.related_words_widgets if w != widget.findChild(QLineEdit)]
        # 更新 self.current_word 的相关单词列表
        related_words = [widget.text().strip() for widget in self.related_words_widgets]
        self.current_word['相关单词'] = related_words

    def add_related_word(self):
        related_input, ok = QInputDialog.getText(self, "添加关联单词", "输入关联单词:")
        if ok and related_input:
            related_widget = QWidget()
            related_layout = QHBoxLayout(related_widget)
            new_related_input = QLineEdit(related_input)
            new_related_input.setStyleSheet(LINE_EDIT_STYLE)
            delete_button = QPushButton("删除")
            delete_button.setStyleSheet(PRIMARY_BUTTON_STYLE)
            delete_button.clicked.connect(lambda _, r=related_widget: self.delete_related_word(r))

            related_layout.addWidget(new_related_input)
            related_layout.addWidget(delete_button)
            self.related_words_layout.addWidget(related_widget)
            self.related_words_widgets.append(new_related_input)

    def add_meaning_example(self):
        index = len([key for key in self.word_detail_widgets if key.startswith('释义')]) + 1
        new_meaning = QLineEdit()
        new_meaning.setStyleSheet(LINE_EDIT_STYLE)
        new_example = QTextEdit()
        new_example.setFixedHeight(90)
        new_example.setStyleSheet(TEXT_EDIT_STYLE)

        meaning_label = QLabel(f"释义{index}:")
        meaning_label.setFont(meaning_font)
        example_label = QLabel(f"例句{index}:")
        example_label.setFont(sentence_font)
        example_label.setPalette(sentence_font_platte)

        delete_button = QPushButton("删除")
        delete_button.clicked.connect(
            lambda: self.delete_meaning_example(index, meaning_label, new_meaning, example_label, new_example,
                                                delete_button))
        delete_button.setStyleSheet(PRIMARY_BUTTON_STYLE)
        self.details_layout.addWidget(meaning_label)
        self.details_layout.addWidget(new_meaning)
        self.details_layout.addWidget(example_label)
        self.details_layout.addWidget(new_example)
        self.details_layout.addWidget(delete_button)

        self.word_detail_widgets[f'释义{index}'] = new_meaning
        self.word_detail_widgets[f'例句{index}'] = new_example

    def delete_meaning_example(self, index, meaning_label, meaning_input, example_label, example_input, delete_button):
        if len(self.meaning_inputs) > 1:
            meaning_label.setParent(None)
            meaning_input.setParent(None)
            example_label.setParent(None)
            example_input.setParent(None)
            delete_button.setParent(None)
            # 从 self.meaning_inputs 中删除
            self.meaning_inputs = [item for i, item in enumerate(self.meaning_inputs) if i != (index - 1)]

            # 从 self.current_word 删除
            meanings = self.current_word.get("释义", [])
            examples = self.current_word.get("例句", [])

            if index <= len(meanings):  # 安全检查
                del meanings[index - 1]
                self.current_word['释义'] = meanings
                if index <= len(examples):
                    del examples[index - 1]
                    self.current_word['例句'] = examples

    def save_edits(self) -> None:
        """
        保存当前编辑内容：
            1) 收集各编辑区域数据
            2) 校验『释义-例句』成对必填
            3) 更新 self.current_word
            4) 持久化并刷新列表 / 详情
        """
        pairs, related_words, note, tags = self._collect_editor_data()
        if not self._validate_pairs(pairs):
            return                          # 有错误或无有效成对数据，已弹窗/标红
        self._update_current_word(pairs, related_words, note, tags)
        self._persist_and_refresh()

    def _collect_editor_data(self):
        """汇总表单数据并返回：
        (释义,例句) 成对列表、关联单词、备注、标签
        同时先清理无效控件并重置所有错误提示。
        """
        from shiboken6 import isValid
        from PySide6.QtWidgets import QLineEdit

        # —— a) 清理无效控件 / 旧错误 —— #
        self.meaning_inputs = [
            tup for tup in self.meaning_inputs
            if len(tup) == 4 and isValid(tup[0]) and isValid(tup[1])
        ]
        for _, _, err_m, err_e in self.meaning_inputs:
            err_m.hide();
            err_m.setText("")
            err_e.hide();
            err_e.setText("")

        # —— b) 采集释义-例句输入 —— #
        pairs = []
        for m_inp, e_inp, err_m, err_e in self.meaning_inputs:
            meaning = m_inp.text().strip()
            example = e_inp.toPlainText().strip()
            pairs.append((meaning, example, err_m, err_e))

        # —— c) 关联单词 / 备注 / 标签 —— #
        related_words = [
            w.text().strip() for w in self.related_words_widgets
            if isinstance(w, QLineEdit) and w.text().strip()
        ]
        note = self.note_edit.toPlainText().strip()
        tags = self.tag_combobox.selectedItems()
        return pairs, related_words, note, tags

    def _validate_pairs(self, pairs: list[tuple[str, str, QLabel, QLabel]]) -> bool:
        """
        校验逻辑：
          • 至少 1 组有效『释义 + 例句』；
          • 若只填其一则在对应行红色提示。
        返回 True 表示校验通过。
        """
        from PySide6.QtWidgets import QMessageBox

        valid, has_complete = True, False
        for meaning, example, err_m, err_e in pairs:
            if meaning and example:
                has_complete = True
            elif meaning and not example:
                err_e.setText("*该内容为必填字段");
                err_e.show();
                valid = False
            elif example and not meaning:
                err_m.setText("*该内容为必填字段");
                err_m.show();
                valid = False

        if not has_complete:
            QMessageBox.warning(self, "错误", "至少需要一个完整的释义-例句对！")
        return valid and has_complete

    def _update_current_word(
            self,
            pairs: list[tuple[str, str, QLabel, QLabel]],
            related_words: list[str],
            note: str,
            tags: list[str]
    ) -> None:
        """把表单数据写回 self.current_word"""
        from datetime import datetime

        meanings = [m for m, e, *_ in pairs if m and e]
        examples = [e for m, e, *_ in pairs if m and e]
        self.current_word.update(
            {
                "释义": meanings,
                "例句": examples,
                "相关单词": related_words,
                "备注": note,
                "标签": tags,
                "时间": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
            }
        )

    def _persist_and_refresh(self) -> None:
        """调用业务层保存；成功后刷新列表并返回只读视图"""
        from PySide6.QtWidgets import QMessageBox
        try:
            save_word(self.book_name, self.book_color, self.current_word)
            QMessageBox.information(self, "成功", "保存成功！")
            self.load_words()  # 刷新左侧列表
            self.display_word_details(self.current_word)  # 返回详情只读状态
        except Exception as exc:
            QMessageBox.warning(self, "错误", str(exc))

    def cancel_edits(self):
        self.display_word_details(self.current_word)
        self.edit_button.setText("编辑")
        self.edit_button.clicked.disconnect()
        self.edit_button.clicked.connect(self.enable_editing)
        self.edit_button.setStyleSheet(PRIMARY_BUTTON_STYLE)
        self.cancel_button.setParent(None)

        if hasattr(self, 'note_edit'):
            self.note_edit.deleteLater()
            self.note_edit = None

        if hasattr(self, 'related_words_layout'):
            self.clear_layout(self.related_words_layout)
            self.related_words_layout.deleteLater()
            self.related_words_layout = None

        if hasattr(self, 'meaning_example_grid'):
            self.clear_layout(self.meaning_example_grid)
            self.meaning_example_grid.deleteLater()
            self.meaning_example_grid = None

        self.word_detail_widgets = {}  # 移除所有widget
        self.clear_layout(self.related_words_layout)
        self.display_word_details(self.current_word)

    def show_add_word_dialog(self):
        """弹出『添加新单词』对话框，保存成功后自动刷新当前列表。"""
        self.add_word_dialog = WordEntryUI(self.path)
        # 保存成功 → 关闭对话框并刷新
        self.add_word_dialog.save_successful.connect(self.refresh_after_add)   # ⭐ 改用信号
        self.add_word_dialog.show()
        
    def show_memory_curve(self):
        # 导入MemoryCurveApp类
        from memory_curve import MemoryCurveApp
        # 创建背单词界面实例
        self.memory_curve_app = MemoryCurveApp(self.path)
        self.memory_curve_app.show()

    def refresh_after_add(self, *_):
        """关闭对话框并重新加载单词列表"""
        if getattr(self, "add_word_dialog", None):
            self.add_word_dialog.close()
        self.load_words()

    def clear_layout(self, layout):
        if layout is None:
            return
        while layout.count():
            item = layout.takeAt(0)
            widget = item.widget()
            if widget:
                widget.deleteLater()
            child_layout = item.layout()
            if child_layout:
                self.clear_layout(child_layout)


if __name__ == '__main__':
    app = QApplication(sys.argv)
    main_window = WordBookApp()
    main_window.show()
    sys.exit(app.exec_())