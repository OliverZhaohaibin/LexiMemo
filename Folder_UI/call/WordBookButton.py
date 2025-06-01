# WordBookButton.py
from PySide6.QtWidgets import QPushButton, QVBoxLayout, QLabel, QWidget
from PySide6.QtGui import QIcon,QColor
from font import normal_font
from PySide6.QtCore import Qt
from PIL import Image
import os
import sys

class WordBookButton(QWidget):

    def __init__(self, title, color, parent=None):
        super().__init__(parent)
        cover_font = normal_font
        cover_font.setBold(True)
        self.button = QPushButton()
        self.label = QLabel(title)
        self.label.setFont(cover_font)
        layout = QVBoxLayout()
        layout.addWidget(self.button, alignment=Qt.AlignCenter)
        layout.addWidget(self.label, alignment=Qt.AlignCenter)
        self.setLayout(layout)

        self.label.setAlignment(Qt.AlignCenter)
        self.button.setFixedSize(120, 120)

        # 生成带有指定颜色的图标
        icon_path = self.create_colored_icon(color)
        icon = QIcon(icon_path)
        self.button.setIcon(icon)
        self.button.setIconSize(self.button.size())

        hover_color = color
        pressed_color = color

        self.button.setStyleSheet(f"""
                   QPushButton {{
                       background-color: transparent;
                       border: none;
                       text-align: center;
                   }}
                   QPushButton::hover {{
                       background-color: {self.lighten_color(hover_color)};
                       border-radius: 15px;
                   }}
                   QPushButton::pressed {{
                       background-color: {pressed_color};
                       border-radius: 15px;
                   }}
               """)

    @staticmethod
    def lighten_color(color, factor=0.6):
        rgb = QColor(color).getRgb()[:3]
        lightened_rgb = [int(min(255, c + (255 - c) * factor)) for c in rgb]
        return QColor(*lightened_rgb).name()

    def create_colored_icon(self, color):
        # 获取程序运行目录
        base_dir = os.path.dirname(os.path.abspath(sys.argv[0]))

        icon_dir = os.path.join(base_dir, "icon")
        os.makedirs(icon_dir, exist_ok=True)
        icon_path = os.path.join(icon_dir, f"colored_icon_{color[1:]}.png")

        # 如果图标已经存在，则直接返回路径
        if os.path.exists(icon_path):
            return icon_path

        base_image_path = os.path.join(base_dir, "icon", "cover.webp")  # 新的图标路径
        base_image = Image.open(base_image_path).convert("RGBA")

        # 提取图片中非"近白色"像素，并将这些像素转变为目标颜色，其他像素设为透明
        datas = base_image.getdata()
        new_data = []
        target_color = Image.new("RGBA", (1, 1), color).getdata()[0]

        for item in datas:
            # 找到非白色的像素
            if not (item[0] > 200 and item[1] > 200 and item[2] > 200):
                new_data.append(target_color)
            else:
                # 将非目标颜色的像素设为透明
                new_data.append((255, 255, 255, 0))

        base_image.putdata(new_data)

        # 保存合成的图像
        base_image.save(icon_path)
        return icon_path