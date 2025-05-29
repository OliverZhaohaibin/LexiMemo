#utils.py
import os
import sys
print("开始加载pandas")
import pandas as pd

def get_word_book_path(book_name, color):
    """
    Get the path to the word book folder.

    Args:
        book_name (str): The name of the word book.
        color (str): The color of the word book.

    Returns:
        str: The path to the word book folder.
    """
    base_dir = os.path.dirname(os.path.abspath(sys.argv[0]))
    directory = os.path.join(base_dir, "books")
    os.makedirs(directory, exist_ok=True)
    folder_name = f"books_{book_name}_{color}"
    path = os.path.join(directory, folder_name)
    return path


def get_tags_path(book_name, color):
    """
    Get the path to the tags.txt file.

    Args:
        book_name (str): The name of the word book.
        color (str): The color of the word book.

    Returns:
        str: The path to the tags.txt file.
    """
    path = get_word_book_path(book_name, color)
    return os.path.join(path, "tags.txt")

def get_excel_path(book_name, color):
    """
    Get the path to the words.xlsx file.

    Args:
        book_name (str): The name of the word book.
        color (str): The color of the word book.

    Returns:
        str: The path to the words.xlsx file.
    """
    path = get_word_book_path(book_name, color)
    return os.path.join(path, "words.xlsx")


def get_total_tags_path():
    """Get the path to the total word book's tags.txt file."""
    return get_tags_path("总单词册", "#FF0000")

def get_total_excel_path():
    """Get the path to the total word book's words.xlsx file."""
    return get_excel_path("总单词册", "#FF0000")

def clean_data(data):
    """Clean data to avoid writing NaN, None, and empty lists to Excel."""
    for key in data:
      if isinstance(data[key], list):
        # If the list is empty, it should be [] and not be converted to string
        if not data[key]:
            continue  # keep list as is
      elif pd.isna(data[key]) or (isinstance(data[key], str) and data[key].lower() == 'nan'):
            # Replace NaN values or "nan" string with an empty string
            data[key] = ""
    return data

# 此函数已被移除，数据合并逻辑已在db.py的save_word_to_total函数中实现

def get_all_word_books(exclude_main=True):
    base_dir = os.path.dirname(os.path.abspath(sys.argv[0]))
    directory = os.path.join(base_dir, "books")
    word_books = []
    for folder in os.listdir(directory):
        if folder.startswith("books_"):
            if exclude_main and folder == "books_总单词册_#FF0000":
                continue
            word_books.append(os.path.join(directory, folder))
    return word_books

def get_note_text(self, word):
    if self.book_name == "总单词册":
        from utils import get_all_word_books
        import sqlite3
        import os
        all_word_books = get_all_word_books(exclude_main=True)
        notes_with_sources = []
        for wb_path in all_word_books:
            wb_name = os.path.basename(wb_path).split('_')[1]
            db_path = os.path.join(wb_path, "wordbook.db")
            if os.path.exists(db_path):
                try:
                    conn = sqlite3.connect(db_path)
                    cursor = conn.cursor()
                    word_str = str(word["单词"]).strip()
                    cursor.execute("SELECT note FROM words WHERE word = ?", (word_str,))
                    result = cursor.fetchone()
                    if result and result[0]:
                        note_str = result[0]
                        if note_str.strip():
                            notes_with_sources.append(f"来自 {wb_name}: {note_str}")
                    conn.close()
                except Exception as e:
                    print(f"Error getting note from {wb_name}: {e}")
        return "\n\n".join(notes_with_sources) if notes_with_sources else "无备注"
    else:
        note = word.get('备注', '无备注')
        return str(note) if note else "无备注"
