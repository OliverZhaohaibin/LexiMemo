# memory_curve.py
import os
import sys
import pandas as pd
import random
from datetime import datetime, timedelta
from PySide6.QtCore import Qt
from PySide6.QtWidgets import (
    QApplication, QWidget, QVBoxLayout, QHBoxLayout, QLabel, QPushButton, 
    QLineEdit, QMessageBox, QFrame, QTextEdit
)
from UI.font import meaning_font, main_word_font, list_word_font, sentence_font, normal_font
from UI.styles import PRIMARY_BUTTON_STYLE, SECONDARY_BUTTON_STYLE, TEXT_EDIT_STYLE, LINE_EDIT_STYLE
from db_memory import load_memory_data, save_memory_data, get_review_words, update_word_memory_status

# 艾宾浩斯遗忘曲线复习间隔（单位：天）
MEMORY_INTERVALS = [0, 1, 2, 4, 7, 15, 30]

class MemoryCurveApp(QWidget):
    def __init__(self, path):
        super().__init__()
        self.path = os.path.dirname(os.path.abspath(sys.argv[0]))  # 使用可执行文件所在目录
        self.book_name = os.path.basename(path).split('_')[1]  # 获取单词本名称
        self.book_color = os.path.basename(path).split('_')[2]  # 获取单词本颜色
        
        # 初始化数据
        self.current_word_index = 0
        self.correct_count = 0
        self.total_count = 0
        self.review_words = []
        
        # 初始化界面
        self.init_ui()
        self.load_memory_data()
        self.load_review_words()
        
    def init_ui(self):
        self.setWindowTitle(f"背单词 - {self.book_name}")
        self.resize(800, 600)
        
        main_layout = QVBoxLayout()
        
        # 顶部信息栏
        info_layout = QHBoxLayout()
        self.progress_label = QLabel("进度: 0/0")
        self.correct_label = QLabel("正确率: 0%")
        info_layout.addWidget(self.progress_label)
        info_layout.addStretch()
        info_layout.addWidget(self.correct_label)
        main_layout.addLayout(info_layout)
        
        # 分隔线
        line = QFrame()
        line.setFrameShape(QFrame.HLine)
        line.setFrameShadow(QFrame.Sunken)
        main_layout.addWidget(line)
        
        # 释义区域
        self.meaning_area = QTextEdit()
        self.meaning_area.setReadOnly(True)
        self.meaning_area.setFont(meaning_font)
        self.meaning_area.setStyleSheet(TEXT_EDIT_STYLE)
        main_layout.addWidget(self.meaning_area)
        
        # 下划线提示区域
        self.hint_label = QLabel("")
        self.hint_label.setAlignment(Qt.AlignCenter)
        self.hint_label.setFont(main_word_font)
        main_layout.addWidget(self.hint_label)
        
        # 输入区域
        input_layout = QHBoxLayout()
        self.word_input = QLineEdit()
        self.word_input.setPlaceholderText("请输入单词")
        self.word_input.setFont(list_word_font)
        self.word_input.setStyleSheet(LINE_EDIT_STYLE)
        self.word_input.returnPressed.connect(self.check_answer)
        self.word_input.textChanged.connect(self.update_hint_display)
        input_layout.addWidget(self.word_input)
        
        self.check_button = QPushButton("确认")
        self.check_button.setStyleSheet(PRIMARY_BUTTON_STYLE)
        self.check_button.clicked.connect(self.check_answer)
        input_layout.addWidget(self.check_button)
        
        main_layout.addLayout(input_layout)
        
        # 结果显示区域
        self.result_label = QLabel("")
        self.result_label.setAlignment(Qt.AlignCenter)
        self.result_label.setFont(main_word_font)
        main_layout.addWidget(self.result_label)
        
        # 例句区域
        self.example_area = QTextEdit()
        self.example_area.setReadOnly(True)
        self.example_area.setFont(sentence_font)
        self.example_area.setStyleSheet(TEXT_EDIT_STYLE)
        self.example_area.setVisible(False)  # 初始隐藏
        main_layout.addWidget(self.example_area)
        
        # 按钮区域
        button_layout = QHBoxLayout()
        
        self.hint_button = QPushButton("提示")
        self.hint_button.setStyleSheet(SECONDARY_BUTTON_STYLE)
        self.hint_button.clicked.connect(self.show_letter_hint)
        button_layout.addWidget(self.hint_button)
        
        self.show_answer_button = QPushButton("显示答案")
        self.show_answer_button.setStyleSheet(SECONDARY_BUTTON_STYLE)
        self.show_answer_button.clicked.connect(self.show_answer)
        button_layout.addWidget(self.show_answer_button)
        
        self.next_button = QPushButton("下一个")
        self.next_button.setStyleSheet(PRIMARY_BUTTON_STYLE)
        self.next_button.clicked.connect(self.next_word)
        self.next_button.setEnabled(False)  # 初始禁用
        button_layout.addWidget(self.next_button)
        
        main_layout.addLayout(button_layout)
        
        self.setLayout(main_layout)
        
        # 初始化提示相关变量
        self.current_word = ""
        self.revealed_letters = 0
    
    def load_memory_data(self):
        """加载记忆数据"""
        try:
            # 使用SQLite数据库加载记忆数据
            self.memory_data = load_memory_data(self.book_name, self.book_color)
            
            if self.memory_data.empty:
                QMessageBox.warning(self, "提示", "记忆数据为空，将创建新的记忆数据。")
                
        except Exception as e:
            QMessageBox.warning(self, "错误", f"加载记忆数据失败: {str(e)}")
            self.memory_data = pd.DataFrame(columns=["单词", "复习次数", "上次复习时间", "下次复习时间", "正确次数", "错误次数"])
    
    def save_memory_data(self):
        """保存记忆数据"""
        try:
            # 使用SQLite数据库保存记忆数据
            save_memory_data(self.book_name, self.book_color, self.memory_data)
        except Exception as e:
            QMessageBox.warning(self, "错误", f"保存记忆数据失败: {str(e)}")
    
    def load_review_words(self):
        """加载需要复习的单词"""
        try:
            # 使用SQLite数据库获取今天需要复习的单词
            self.review_words = get_review_words(self.book_name, self.book_color)
            
            if not self.review_words:
                QMessageBox.information(self, "提示", "今天没有需要复习的单词!")
                return
            
            # 随机打乱顺序
            random.shuffle(self.review_words)
            
            self.total_count = len(self.review_words)
            self.current_word_index = 0
            self.correct_count = 0
            
            self.update_progress()
            self.show_current_word()
        except Exception as e:
            QMessageBox.warning(self, "错误", f"加载单词数据失败: {str(e)}")
    
    def update_progress(self):
        """更新进度信息"""
        if self.total_count > 0:
            self.progress_label.setText(f"进度: {self.current_word_index}/{self.total_count}")
            correct_rate = (self.correct_count / max(1, self.current_word_index)) * 100 if self.current_word_index > 0 else 0
            self.correct_label.setText(f"正确率: {correct_rate:.1f}%")
        else:
            self.progress_label.setText("进度: 0/0")
            self.correct_label.setText("正确率: 0%")
    
    def show_current_word(self):
        """显示当前单词的释义"""
        if not self.review_words or self.current_word_index >= len(self.review_words):
            QMessageBox.information(self, "完成", "恭喜你完成了今天的复习!")
            self.close()
            return
        
        # 重置界面状态
        self.word_input.clear()
        self.word_input.setEnabled(True)
        self.check_button.setEnabled(True)
        self.show_answer_button.setEnabled(True)
        self.hint_button.setEnabled(True)
        self.next_button.setEnabled(False)
        self.result_label.clear()
        self.example_area.clear()
        self.example_area.setVisible(False)
        
        # 显示释义
        current_word = self.review_words[self.current_word_index]
        self.current_word = current_word["单词"]  # 保存当前单词
        self.revealed_letters = 0  # 重置已提示的字母数
        
        meanings = current_word.get("释义", [])
        
        meanings_text = ""
        for i, meaning in enumerate(meanings):
            meanings_text += f"释义{i+1}: {meaning}\n\n"
        
        self.meaning_area.setText(meanings_text)
        
        # 显示下划线提示
        self.update_hint_display()
        
        self.word_input.setFocus()
    def update_hint_display(self):
        """根据单词长度和用户输入更新下划线提示"""
        if not hasattr(self, 'current_word') or not self.current_word:
            return
            
        # 确保current_word是字符串类型
        if not isinstance(self.current_word, str):
            self.current_word = str(self.current_word)
            
        word_length = len(self.current_word)
        user_input = self.word_input.text()
        
        # 创建下划线提示
        hint_text = ""
        for i in range(word_length):
            if i < self.revealed_letters:
                # 已提示的字母
                hint_text += f" {self.current_word[i]} "
            elif i < len(user_input):
                # 用户已输入的字母
                hint_text += f" {user_input[i]} "
            else:
                # 未输入的字母用下划线表示
                hint_text += " _ "
                
        self.hint_label.setText(hint_text)
    
    def show_letter_hint(self):
        """提示下一个字母"""
        if not self.current_word or self.revealed_letters >= len(self.current_word):
            return
            
        self.revealed_letters += 1
        self.update_hint_display()
        
        # 如果已经提示了所有字母，禁用提示按钮
        if self.revealed_letters >= len(self.current_word):
            self.hint_button.setEnabled(False)
    
    def check_answer(self):
        """检查答案"""
        if not self.review_words or self.current_word_index >= len(self.review_words):
            return
        try:
            user_input = self.word_input.text().strip().lower()
            current_word = self.review_words[self.current_word_index]
            
            # 确保current_word是字典类型且包含单词字段
            if not isinstance(current_word, dict) or "单词" not in current_word:
                raise ValueError("单词数据格式错误")
                
            correct_word = str(current_word["单词"]).strip().lower()
            
            if user_input == correct_word:
                # 答案正确
                self.result_label.setText("✓ 正确!")
                self.result_label.setStyleSheet("color: green;")
                self.correct_count += 1
                
                # 使用SQLite数据库更新单词记忆状态
                update_word_memory_status(self.book_name, self.book_color, current_word["单词"], True)
                
                # 更新内存中的数据以保持UI一致性
                word_idx = self.memory_data[self.memory_data["单词"] == current_word["单词"]].index[0]
                self.memory_data.at[word_idx, "正确次数"] = self.memory_data.at[word_idx, "正确次数"] + 1
                self.memory_data.at[word_idx, "复习次数"] = self.memory_data.at[word_idx, "复习次数"] + 1
                review_stage = min(self.memory_data.at[word_idx, "复习次数"], len(MEMORY_INTERVALS) - 1)
                next_review_date = datetime.now() + timedelta(days=MEMORY_INTERVALS[review_stage])
                self.memory_data.at[word_idx, "上次复习时间"] = datetime.now().strftime("%Y-%m-%d")
                self.memory_data.at[word_idx, "下次复习时间"] = next_review_date.strftime("%Y-%m-%d")
            else:
                # 答案错误
                self.result_label.setText(f"✗ 错误! 正确答案是: {current_word['单词']}")
                self.result_label.setStyleSheet("color: red;")
                
                # 使用SQLite数据库更新单词记忆状态
                update_word_memory_status(self.book_name, self.book_color, current_word["单词"], False)
                
                # 更新内存中的数据以保持UI一致性
                word_idx = self.memory_data[self.memory_data["单词"] == current_word["单词"]].index[0]
                self.memory_data.at[word_idx, "错误次数"] = self.memory_data.at[word_idx, "错误次数"] + 1
                self.memory_data.at[word_idx, "复习次数"] = self.memory_data.at[word_idx, "复习次数"] + 1
                self.memory_data.at[word_idx, "上次复习时间"] = datetime.now().strftime("%Y-%m-%d")
                self.memory_data.at[word_idx, "下次复习时间"] = (datetime.now() + timedelta(days=1)).strftime("%Y-%m-%d")
                
                # 将当前单词添加到队列末尾，以便再次复习
                self.review_words.append(current_word)
            
            # 显示例句
            examples = current_word.get("例句", [])
            if examples:
                examples_text = ""
                for i, example in enumerate(examples):
                    examples_text += f"例句{i+1}: {example}\n\n"
                self.example_area.setText(examples_text)
                self.example_area.setVisible(True)
            
            # 禁用输入和检查按钮，启用下一个按钮
            self.word_input.setEnabled(False)
            self.check_button.setEnabled(False)
            self.show_answer_button.setEnabled(False)
            self.hint_button.setEnabled(False)  # 禁用提示按钮
            self.next_button.setEnabled(True)
            
            # 保存记忆数据
            self.save_memory_data()
            self.update_progress()
        except Exception as e:
            QMessageBox.warning(self, "错误", f"检查答案时发生错误: {str(e)}")
    def show_answer(self):
        """显示答案"""
        if not self.review_words or self.current_word_index >= len(self.review_words):
            return
        
        current_word = self.review_words[self.current_word_index]
        self.result_label.setText(f"答案: {current_word['单词']}")
        self.result_label.setStyleSheet("color: blue;")
        
        # 显示例句
        examples = current_word.get("例句", [])
        if examples:
            examples_text = ""
            for i, example in enumerate(examples):
                examples_text += f"例句{i+1}: {example}\n\n"
            self.example_area.setText(examples_text)
            self.example_area.setVisible(True)
        
        # 使用SQLite数据库更新单词记忆状态 - 显示答案视为错误
        update_word_memory_status(self.book_name, self.book_color, current_word["单词"], False)
        
        # 更新内存中的数据以保持UI一致性
        word_idx = self.memory_data[self.memory_data["单词"] == current_word["单词"]].index[0]
        self.memory_data.at[word_idx, "错误次数"] = self.memory_data.at[word_idx, "错误次数"] + 1
        self.memory_data.at[word_idx, "复习次数"] = self.memory_data.at[word_idx, "复习次数"] + 1
        self.memory_data.at[word_idx, "上次复习时间"] = datetime.now().strftime("%Y-%m-%d")
        self.memory_data.at[word_idx, "下次复习时间"] = (datetime.now() + timedelta(days=1)).strftime("%Y-%m-%d")
        
        # 将当前单词添加到队列末尾，以便再次复习
        self.review_words.append(current_word)
        
        # 禁用输入和检查按钮，启用下一个按钮
        self.word_input.setEnabled(False)
        self.check_button.setEnabled(False)
        self.show_answer_button.setEnabled(False)
        self.hint_button.setEnabled(False)  # 禁用提示按钮
        self.next_button.setEnabled(True)
    
    def next_word(self):
        """进入下一个单词"""
        self.current_word_index += 1
        self.show_current_word()


    def closeEvent(self, event):
        """窗口关闭事件处理"""
        # 数据已经在每次更新时保存到SQLite数据库，不需要再次保存
        event.accept()

if __name__ == "__main__":
    app = QApplication(sys.argv)
    app.setFont(normal_font)
    if len(sys.argv) > 1:
        path = sys.argv[1]
        window = MemoryCurveApp(path)
        window.show()
        sys.exit(app.exec())
    else:
        print("请提供单词本路径")