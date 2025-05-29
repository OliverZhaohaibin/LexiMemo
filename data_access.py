#data_access.py
import os
from db import load_words, save_word
from utils import clean_data

def load_words_from_excel(path):
    """兼容旧接口，从路径获取单词本名称和颜色，然后从数据库加载单词"""
    try:
        # 从路径中提取单词本名称和颜色
        folder_name = os.path.basename(os.path.dirname(path))
        parts = folder_name.split('_')
        if len(parts) >= 3:
            book_name = parts[1]
            book_color = parts[2]
            return load_words(book_name, book_color)
        return []
    except Exception as e:
        print(f"Error loading words from database: {e}")
        return []


def save_words_to_excel(path, data, sync_to_total=True):
    """Saves word data to Excel file."""
    try:
        data = clean_data(data)
        
        # 从路径中提取单词本名称和颜色
        folder_name = os.path.basename(os.path.dirname(path))
        parts = folder_name.split('_')
        if len(parts) >= 3:
            book_name = parts[1]
            book_color = parts[2]
            # 调用db.py中的save_word函数保存数据
            save_word(book_name, book_color, data, sync_to_total)
        else:
            raise Exception("无法从路径中提取单词本信息")
    except Exception as e:
        raise Exception(f"保存单词数据时出错：{str(e)}")