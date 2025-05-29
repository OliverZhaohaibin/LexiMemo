#font.py
from PySide6.QtGui import QFont, QPalette, QColor

# 使用通用字体族，确保在任何中文Windows系统上都能正常显示
normal_font = QFont("Microsoft YaHei, SimSun, sans-serif", 12)

meaning_font = QFont("Microsoft YaHei, SimSun, sans-serif", 13)
meaning_font.setBold(True)

sentence_font = QFont("Microsoft YaHei, SimSun, sans-serif", 13)
sentence_font.setBold(True)
sentence_font_platte = QPalette()
sentence_font_platte.setColor(QPalette.WindowText, QColor("gray"))

word_font = QFont("Microsoft YaHei, SimSun, sans-serif", 15)
word_font.setBold(True)

note_font = QFont("SimSun, Microsoft YaHei, sans-serif")

# 对于英文字体，添加备选字体
main_word_font = QFont("Georgia, Times New Roman, serif", 35)
main_word_font.setBold(True)
main_word_font.setWordSpacing(2.5)

list_word_font = QFont("Georgia, Times New Roman, serif", 12)
list_word_font.setBold(True)