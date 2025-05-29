# business_logic.py
from data_access import load_words_from_excel, save_words_to_excel
from utils import get_excel_path
from db import delete_word as db_delete_word

def get_all_words(book_name, book_color):
   """Loads and return all word data for a given word book."""
   excel_path = get_excel_path(book_name, book_color)
   return load_words_from_excel(excel_path)

def save_word(book_name, book_color, data, sync_to_total = True):
    """Saves word data to a given word book."""
    try:
        excel_path = get_excel_path(book_name, book_color)
        save_words_to_excel(excel_path, data, sync_to_total)
    except Exception as e:
        raise Exception(f"保存单词失败：{str(e)}")

def delete_word(book_name, book_color, word):
    """Deletes a word from a given word book."""
    try:
        db_delete_word(book_name, book_color, word)
    except Exception as e:
        raise Exception(f"删除单词失败：{str(e)}")