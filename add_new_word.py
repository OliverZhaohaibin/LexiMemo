# add_new_word.py
import sys
import os
from PySide6.QtWidgets import (
    QApplication, QWidget, QVBoxLayout, QLineEdit, QLabel, QPushButton, QHBoxLayout, QMessageBox,
    QInputDialog, QGridLayout, QFrame, QTextEdit, QScrollArea, QCheckBox
)
from UI.font import normal_font
from PySide6.QtCore import Signal

from datetime import datetime

from UI.font import meaning_font, word_font
from utils import get_tags_path, get_total_tags_path
from services.wordbook_service import WordBookService as WS
from UI.styles import GREEN_BUTTON_STYLE, RED_BUTTON_STYLE, GRAY_INPUT_STYLE, GRAY_TEXT_EDIT_STYLE, PRIMARY_BUTTON_STYLE, \
    SECONDARY_BUTTON_STYLE


class WordEntryUI(QWidget):
    save_successful = Signal(dict)
    def __init__(self, path):
        super(WordEntryUI, self).__init__()
        self.path = path  # 保存传入的路径
        self.book_name = os.path.basename(path).split('_')[1]
        self.book_color = os.path.basename(path).split('_')[2]

        self.setWindowTitle("新单词")
        self.resize(800, 700)

        self.scroll_area = QScrollArea()
        self.scroll_area.setWidgetResizable(True)

        self.scroll_content = QWidget()
        self.scroll_layout = QVBoxLayout(self.scroll_content)

        self.layout = QVBoxLayout()

        # 单词
        self.word_layout = QHBoxLayout()
        self.word_label = QLabel("单词:")
        self.word_label.setFont(word_font)
        self.word_input = QLineEdit()
        self.word_input.setFixedSize(400, 30)
        self.word_input.setStyleSheet(GRAY_INPUT_STYLE)
        self.word_layout.addWidget(self.word_label)
        self.word_layout.addWidget(self.word_input)
        self.scroll_layout.addLayout(self.word_layout)

        # 相关单词
        self.related_layout = QVBoxLayout()
        self.related_layout.setSpacing(10)
        self.related_items = [self.add_related_input_field(0)]
        self.add_related_button = QPushButton("+")
        self.add_related_button.setFixedSize(30, 30)
        self.add_related_button.setStyleSheet(GREEN_BUTTON_STYLE) # 加号按钮样式
        self.add_related_button.clicked.connect(self.add_related_input_row)
        self.remove_related_button = QPushButton("-")
        self.remove_related_button.setFixedSize(30, 30)
        self.remove_related_button.setStyleSheet(RED_BUTTON_STYLE) # 减号按钮样式
        self.remove_related_button.clicked.connect(self.remove_related_input_row)
        button_layout = QHBoxLayout()
        button_layout.addWidget(self.add_related_button)
        button_layout.addWidget(self.remove_related_button)
        self.scroll_layout.addLayout(self.related_layout)
        self.scroll_layout.addLayout(button_layout)

        # Separator
        line = QFrame()
        line.setFrameShape(QFrame.HLine)
        line.setFrameShadow(QFrame.Sunken)
        self.scroll_layout.addWidget(line)

        # 释义和例句
        self.meaning_example_layout = QVBoxLayout()
        self.meaning_example_grid = QGridLayout()
        self.meaning_inputs = [self.add_meaning_example_pair(0)]
        self.add_meaning_button = QPushButton("+")
        self.add_meaning_button.setFixedSize(30, 30)
        self.add_meaning_button.setStyleSheet(GREEN_BUTTON_STYLE) # 加号按钮样式
        self.add_meaning_button.clicked.connect(self.add_meaning_example_row)
        self.remove_meaning_button = QPushButton("-")
        self.remove_meaning_button.setFixedSize(30, 30)
        self.remove_meaning_button.setStyleSheet(RED_BUTTON_STYLE) # 减号按钮样式
        self.remove_meaning_button.clicked.connect(self.remove_meaning_example_row)
        self.meaning_example_layout.addLayout(self.meaning_example_grid)
        self.meaning_button_layout = QHBoxLayout()
        self.meaning_button_layout.addWidget(self.add_meaning_button)
        self.meaning_button_layout.addWidget(self.remove_meaning_button)
        self.meaning_example_layout.addLayout(self.meaning_button_layout)
        self.scroll_layout.addLayout(self.meaning_example_layout)

        # 备注
        self.note_layout = QHBoxLayout()
        self.note_label = QLabel("备注:")
        self.note_input = QTextEdit()
        self.note_input.setFixedSize(400, 90)
        self.note_input.setStyleSheet(GRAY_TEXT_EDIT_STYLE)
        self.note_layout.addWidget(self.note_label)
        self.note_layout.addWidget(self.note_input)
        self.scroll_layout.addLayout(self.note_layout)

        # 标签
        self.tag_label = QLabel("标签:")
        self.scroll_layout.addWidget(self.tag_label)

        self.tag_scroll_area = QScrollArea()
        self.tag_scroll_area.setWidgetResizable(True)
        self.tag_widget = QWidget()
        self.tag_layout = QVBoxLayout(self.tag_widget)
        self.tag_scroll_area.setWidget(self.tag_widget)

        self.new_tag_button = QPushButton("新建标签")
        self.new_tag_button.clicked.connect(self.add_new_tag)
        self.new_tag_button.setStyleSheet(PRIMARY_BUTTON_STYLE)

        self.scroll_layout.addWidget(self.tag_scroll_area)
        self.scroll_layout.addWidget(self.new_tag_button)
        self.load_tags()

        # 保存和取消按钮
        self.button_layout = QHBoxLayout()
        self.save_button = QPushButton("保存")
        self.cancel_button = QPushButton("取消")
        self.cancel_button.setStyleSheet(RED_BUTTON_STYLE)  # 取消按钮样式
        self.cancel_button.clicked.connect(self.close)
        self.save_button.setStyleSheet(SECONDARY_BUTTON_STYLE) # 保存按钮样式
        self.button_layout.addWidget(self.save_button)
        self.button_layout.addWidget(self.cancel_button)
        self.save_button.setFixedSize(80, 30)
        self.cancel_button.setFixedSize(80, 30)
        self.scroll_layout.addLayout(self.button_layout)

        self.save_button.clicked.connect(self.save_word)

        self.scroll_area.setWidget(self.scroll_content)
        self.layout.addWidget(self.scroll_area)
        self.setLayout(self.layout)

    def add_meaning_example_pair(self, row):
        """
        新建“释义-例句”输入对，并在其上方预留隐藏的错误提示标签。
        每个输入对占两行：第 1 行放错误提示，第 2 行放输入控件。
        """
        base_row = row * 2  # 每对控件预留两行
        # ---------- 错误提示 ----------
        meaning_err = QLabel("")
        meaning_err.setStyleSheet("color: red;")
        meaning_err.hide()
        example_err = QLabel("")
        example_err.setStyleSheet("color: red;")
        example_err.hide()
        self.meaning_example_grid.addWidget(meaning_err, base_row, 1)
        self.meaning_example_grid.addWidget(example_err, base_row, 3)

        # ---------- 输入控件 ----------
        meaning_label = QLabel(f"释义{row + 1}:")
        meaning_label.setFont(meaning_font)
        meaning_input = QLineEdit()
        meaning_input.setFixedSize(180, 30)
        meaning_input.setStyleSheet(GRAY_INPUT_STYLE)

        example_label = QLabel(f"例句{row + 1}:")
        example_input = QTextEdit()
        example_input.setFixedSize(300, 90)
        example_input.setStyleSheet(GRAY_TEXT_EDIT_STYLE)

        self.meaning_example_grid.addWidget(meaning_label, base_row + 1, 0)
        self.meaning_example_grid.addWidget(meaning_input, base_row + 1, 1)
        self.meaning_example_grid.addWidget(example_label, base_row + 1, 2)
        self.meaning_example_grid.addWidget(example_input, base_row + 1, 3)

        return (meaning_input, example_input, meaning_err, example_err)

    def add_meaning_example_row(self):
        row = len(self.meaning_inputs)
        self.meaning_inputs.append(self.add_meaning_example_pair(row))

    def remove_meaning_example_row(self):
        if len(self.meaning_inputs) > 1:
            pair_index = len(self.meaning_inputs) - 1
            base_row = pair_index * 2

            # 遍历待删除的两行（错误提示行和输入控件行）
            for r in (base_row, base_row + 1):
                for c in range(4):
                    item = self.meaning_example_grid.itemAtPosition(r, c)
                    if item is not None:
                        widget = item.widget()
                        if widget is not None:
                            widget.deleteLater()

            self.meaning_inputs.pop()

    def add_related_input_field(self, index):
        layout = QHBoxLayout()
        label = QLabel(f"相关单词{index + 1}:")
        input_field = QLineEdit()
        input_field.setFixedSize(400, 30)
        input_field.setStyleSheet(GRAY_INPUT_STYLE)
        layout.addWidget(label)
        layout.addWidget(input_field)
        self.related_layout.addLayout(layout)
        return (layout, label, input_field)

    def add_related_input_row(self):
        index = len(self.related_items)
        self.related_items.append(self.add_related_input_field(index))

    def remove_related_input_row(self):
        if len(self.related_items) > 1:
            layout, label, input_field = self.related_items.pop()
            label.deleteLater()
            input_field.deleteLater()
            layout.deleteLater()

    def load_tags(self):
        if hasattr(self, 'tag_checkboxes'):
            for checkbox in self.tag_checkboxes:
                checkbox.setParent(None)
        self.tag_checkboxes = []
        tags_path = get_tags_path(self.book_name, self.book_color)
        if os.path.exists(tags_path):
            with open(tags_path, "r", encoding="utf-8") as file:
                tags = file.read().splitlines()
                for tag in tags:
                    tag_checkbox = QCheckBox(tag)
                    self.tag_layout.addWidget(tag_checkbox)
                    self.tag_checkboxes.append(tag_checkbox)

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
                self.load_tags()
                for checkbox in self.tag_checkboxes:
                    if checkbox.text() == tag:
                        checkbox.setChecked(True)

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

    def save_word(self):
        """
        校验并保存单词。
        - 校验失败 → 在对应输入框上方显示红色“*该内容为必填字段”，弹窗提示但窗口保持开启
        - 校验成功 → 保存→发射 save_successful 信号→弹窗提示→关闭窗口
        """
        try:
            # ---------- 0. 先清空旧错误提示 ----------
            for tup in self.meaning_inputs:
                if len(tup) >= 4:
                    _, _, err_m, err_e = tup
                    err_m.hide();
                    err_m.setText("")
                    err_e.hide();
                    err_e.setText("")

            # ---------- 1. 收集字段 ----------
            word = self.word_input.text().strip()
            related = [w.text().strip() for _, _, w in self.related_items if w.text().strip()]
            tags = [c.text() for c in self.tag_checkboxes if c.isChecked()]
            note = self.note_input.toPlainText().strip()
            timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")

            # ---------- 2. 校验释义-例句成对必填 ----------
            meanings, examples = [], []
            valid = True
            for meaning_inp, example_inp, err_m, err_e in self.meaning_inputs:
                m = meaning_inp.text().strip()
                e = example_inp.toPlainText().strip()

                if m and not e:  # 释义有值，例句缺失
                    err_e.setText("*该内容为必填字段")
                    err_e.show()
                    valid = False
                elif e and not m:  # 例句有值，释义缺失
                    err_m.setText("*该内容为必填字段")
                    err_m.show()
                    valid = False

                meanings.append(m)
                examples.append(e)

            # 过滤出真正成对的数据
            paired = [(m, e) for m, e in zip(meanings, examples) if m and e]

            # ---------- 3. 其它必填校验 ----------
            if not word:
                QMessageBox.warning(self, "警告", "单词不能为空！", QMessageBox.Ok)
                return
            if not paired:  # 全部为空或都不成对
                QMessageBox.warning(self, "警告", "至少填写一对释义和例句！", QMessageBox.Ok)
                return
            if not valid:  # 有红色提示，停止保存
                return

            # ---------- 4. 组织并保存 ----------
            data = {
                "单词": word,
                "相关单词": related,
                "标签": tags,
                "释义": [m for m, _ in paired],
                "例句": [e for _, e in paired],
                "备注": note,
                "时间": timestamp,
            }

            WS.save_word(self.book_name, self.book_color, data)

            # ---------- 5. 成功操作 ----------
            self.save_successful.emit(data)  # 发射信号，供父窗口刷新
            QMessageBox.information(self, "成功", "单词保存成功！", QMessageBox.Ok)
            self.close()

        except PermissionError:
            QMessageBox.warning(self, "错误", "无法写入文件，请检查文件占用或权限。", QMessageBox.Ok)
        except Exception as e:
            QMessageBox.critical(self, "错误", f"保存单词时发生错误：{e}", QMessageBox.Ok)

def show_word_entry_ui():
    app = QApplication(sys.argv)
    app.setFont(normal_font)
    window = WordEntryUI()
    window.show()
    sys.exit(app.exec_())


if __name__ == '__main__':
    show_word_entry_ui()
