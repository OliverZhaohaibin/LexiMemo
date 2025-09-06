#styles.py
# 主题颜色
# iOS-inspired palette
# 基础背景色
BACKGROUND_COLOR = "#f0f0f2"

PRIMARY_COLOR = "#007AFF"  # system blue
PRIMARY_COLOR_LIGHT = "#419CFF"
SECONDARY_COLOR = "#34C759"  # system green
SECONDARY_COLOR_LIGHT = "#70E17B"

# 文字颜色
TEXT_COLOR = "#212121"
GRAY_COLOR = "#757575"
WHITE_COLOR = "#FFFFFF"

# 按钮样式
PRIMARY_BUTTON_STYLE = f"""
    QPushButton {{
        background-color: {PRIMARY_COLOR};
        color: {WHITE_COLOR};
        border: none;
        border-radius: 12px;
        padding: 8px 16px;
        font-size: 14px;
    }}
    QPushButton:hover {{
        background-color: {PRIMARY_COLOR_LIGHT};
    }}
    QPushButton:pressed {{
        background-color: {PRIMARY_COLOR};
    }}
"""

SECONDARY_BUTTON_STYLE = f"""
    QPushButton {{
        background-color: transparent;
        color: {PRIMARY_COLOR};
        border: 1px solid {PRIMARY_COLOR};
        border-radius: 12px;
        padding: 8px 16px;
        font-size: 14px;
    }}
    QPushButton:hover {{
        background-color: rgba(0,122,255,0.1);
    }}
    QPushButton:pressed {{
        background-color: rgba(0,122,255,0.2);
    }}
"""

TEXT_EDIT_STYLE = f"""
    QTextEdit {{
        border: 1px solid #ccc;
        border-radius: 10px;
        background-color: rgba(255,255,255,0.8);
        padding: 6px;
        font-size: 23px;
    }}
    QTextEdit:focus {{
        border: 1px solid {PRIMARY_COLOR};
    }}
"""

LINE_EDIT_STYLE = f"""
    QLineEdit {{
        border: 1px solid #ccc;
        border-radius: 10px;
        background-color: rgba(255,255,255,0.8);
        padding: 6px;
        font-size: 23px;
    }}
    QLineEdit:focus {{
        border: 1px solid {PRIMARY_COLOR};
    }}
"""
SCROLL_AREA_STYLE = f"""
    QScrollArea {{
        border: none;
    }}
    QScrollArea > QWidget > QWidget {{
        background-color: {BACKGROUND_COLOR};
    }}
"""
TAG_COMBOBOX_STYLE = """
    QComboBox {
        border: 1px solid #ddd;
        border-radius: 4px;
        background-color: white;
        padding: 4px;
        font-size: 14px;
    }
    QComboBox:focus {
        border: 1px solid #444;
    }
"""
TAG_LABEL_STYLE = """
    QLabel {
        background-color: #e0e0e0;
        border-radius: 8px;
        padding: 3px 8px;
        margin-right:5px;
        margin-bottom:5px;

    }
"""

GREEN_BUTTON_STYLE = f"""
    QPushButton {{
        background-color: {SECONDARY_COLOR};
        color: {WHITE_COLOR};
        border: none;
        border-radius: 12px;
        padding: 6px 12px;
        font-size: 14px;
    }}
    QPushButton:hover {{
        background-color: {SECONDARY_COLOR_LIGHT};
    }}
    QPushButton:pressed {{
        background-color: {SECONDARY_COLOR};
    }}
"""

RED_BUTTON_STYLE = f"""
    QPushButton {{
        background-color: #FF4D4D;
        color: {WHITE_COLOR};
        border: none;
        border-radius: 12px;
        padding: 6px 12px;
        font-size: 14px;
    }}
    QPushButton:hover {{
        background-color: #FF8080;
    }}
    QPushButton:pressed {{
        background-color: #FF4D4D;
    }}
"""

# 专用于小型删除按钮的红色样式（无内边距，适合 20-30px 尺寸）
SMALL_RED_BUTTON_STYLE = f"""
    QPushButton {{
        background-color: #FF4D4D;
        color: {WHITE_COLOR};
        border: none;
        border-radius: 4px;
        padding: 0px;
        font-size: 14px;
    }}
    QPushButton:hover {{
        background-color: #FF8080;
    }}
    QPushButton:pressed {{
        background-color: #FF4D4D;
    }}
"""

GRAY_INPUT_STYLE = """
    QLineEdit {
        border: 2px solid #ddd;
        border-radius: 4px;
        background-color: #e5e5e5; /* 稍微置灰的背景 */
        padding: 4px;
        font-size: 23px;
        min-height: 30px;
    }
    QLineEdit:focus {
        border: 2px solid #444;
    }
"""

GRAY_TEXT_EDIT_STYLE = """
    QTextEdit {
        border: 2px solid #ddd;
        border-radius: 4px;
        background-color: #e5e5e5; /* 稍微置灰的背景 */
        padding: 4px;
        font-size: 23px;
        min-height: 30px;
    }
     QTextEdit:focus {
        border: 2px solid #444;
    }
"""

# 备注部分的样式
NOTE_TEXT_EDIT_STYLE = """
    QTextEdit {
        background-color: #e5e5e5;  /* 浅灰背景 */
        border: 1px solid #ddd;     /* 浅灰边框 */
        border-radius: 4px;         /* 圆角 */
        padding: 5px;               /* 内边距 */
        font-size: 26px;            /* 字体大小 */
        color: #333;                /* 深灰文字 */
    }
"""