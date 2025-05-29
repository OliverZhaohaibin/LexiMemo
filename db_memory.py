# db_memory.py
import sqlite3
import json
from datetime import datetime, timedelta
import pandas as pd

from db import get_db_path

# 艾宾浩斯遗忘曲线复习间隔（单位：天）
MEMORY_INTERVALS = [0, 1, 2, 4, 7, 15, 30]

def init_memory_table(db_path):
    """
    初始化记忆曲线数据表
    
    Args:
        db_path (str): 数据库文件路径
    """
    conn = sqlite3.connect(db_path)
    cursor = conn.cursor()
    
    # 创建记忆曲线数据表
    cursor.execute('''
    CREATE TABLE IF NOT EXISTS memory_data (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        word TEXT NOT NULL,
        review_count INTEGER DEFAULT 0,  -- 复习次数
        last_review_date TEXT,          -- 上次复习时间
        next_review_date TEXT,          -- 下次复习时间
        correct_count INTEGER DEFAULT 0, -- 正确次数
        error_count INTEGER DEFAULT 0,   -- 错误次数
        UNIQUE(word)
    )
    ''')
    
    conn.commit()
    conn.close()

def get_memory_connection(book_name, color):
    """
    获取数据库连接并确保记忆表已创建
    
    Args:
        book_name (str): 单词本名称
        color (str): 单词本颜色
        
    Returns:
        sqlite3.Connection: 数据库连接对象
    """
    db_path = get_db_path(book_name, color)
    init_memory_table(db_path)  # 确保记忆表已创建
    return sqlite3.connect(db_path)

def load_memory_data(book_name, color):
    """
    从数据库加载记忆数据
    
    Args:
        book_name (str): 单词本名称
        color (str): 单词本颜色
        
    Returns:
        pd.DataFrame: 记忆数据DataFrame
    """
    try:
        conn = get_memory_connection(book_name, color)
        cursor = conn.cursor()
        
        # 获取所有单词
        cursor.execute("SELECT word FROM words")
        all_words = [row[0] for row in cursor.fetchall()]
        
        # 获取记忆数据
        cursor.execute("""
        SELECT word, review_count, last_review_date, next_review_date, correct_count, error_count 
        FROM memory_data
        """)
        memory_rows = cursor.fetchall()
        
        # 转换为字典列表
        memory_data = []
        memory_words = set()
        
        for row in memory_rows:
            word, review_count, last_review_date, next_review_date, correct_count, error_count = row
            memory_words.add(word)
            memory_data.append({
                "单词": word,
                "复习次数": review_count,
                "上次复习时间": last_review_date,
                "下次复习时间": next_review_date,
                "正确次数": correct_count,
                "错误次数": error_count
            })
        
        # 检查是否有新单词需要添加到记忆数据中
        new_words = set(all_words) - memory_words
        if new_words:
            today = datetime.now().strftime("%Y-%m-%d")
            for word in new_words:
                memory_data.append({
                    "单词": word,
                    "复习次数": 0,
                    "上次复习时间": None,
                    "下次复习时间": today,
                    "正确次数": 0,
                    "错误次数": 0
                })
                
                # 将新单词添加到数据库
                cursor.execute("""
                INSERT INTO memory_data (word, review_count, last_review_date, next_review_date, correct_count, error_count)
                VALUES (?, ?, ?, ?, ?, ?)
                """, (word, 0, None, today, 0, 0))
            
            conn.commit()
        
        # 检查是否有已删除的单词需要从记忆数据中移除
        deleted_words = memory_words - set(all_words)
        if deleted_words:
            for word in deleted_words:
                cursor.execute("DELETE FROM memory_data WHERE word = ?", (word,))
            conn.commit()
            # 从内存中的记忆数据中移除已删除的单词
            memory_data = [data for data in memory_data if data["单词"] not in deleted_words]
        
        conn.close()
        
        # 转换为DataFrame
        memory_df = pd.DataFrame(memory_data)
        return memory_df
    
    except Exception as e:
        print(f"Error loading memory data: {e}")
        # 返回空DataFrame，包含必要的列
        return pd.DataFrame(columns=["单词", "复习次数", "上次复习时间", "下次复习时间", "正确次数", "错误次数"])

def save_memory_data(book_name, color, memory_data):
    """
    保存记忆数据到数据库
    
    Args:
        book_name (str): 单词本名称
        color (str): 单词本颜色
        memory_data (pd.DataFrame): 记忆数据DataFrame
    """
    try:
        conn = get_memory_connection(book_name, color)
        cursor = conn.cursor()
        
        # 遍历DataFrame中的每一行
        for _, row in memory_data.iterrows():
            word = row["单词"]
            review_count = int(row["复习次数"])
            last_review_date = row["上次复习时间"]
            next_review_date = row["下次复习时间"]
            correct_count = int(row["正确次数"])
            error_count = int(row["错误次数"])
            
            # 检查单词是否已存在
            cursor.execute("SELECT id FROM memory_data WHERE word = ?", (word,))
            existing = cursor.fetchone()
            
            if existing:
                # 更新现有记录
                cursor.execute("""
                UPDATE memory_data SET 
                    review_count = ?,
                    last_review_date = ?,
                    next_review_date = ?,
                    correct_count = ?,
                    error_count = ?
                WHERE word = ?
                """, (review_count, last_review_date, next_review_date, correct_count, error_count, word))
            else:
                # 插入新记录
                cursor.execute("""
                INSERT INTO memory_data (word, review_count, last_review_date, next_review_date, correct_count, error_count)
                VALUES (?, ?, ?, ?, ?, ?)
                """, (word, review_count, last_review_date, next_review_date, correct_count, error_count))
        
        conn.commit()
        conn.close()
    
    except Exception as e:
        print(f"Error saving memory data: {e}")
        raise Exception(f"保存记忆数据失败: {str(e)}")

def get_review_words(book_name, color):
    """
    获取今天需要复习的单词
    
    Args:
        book_name (str): 单词本名称
        color (str): 单词本颜色
        
    Returns:
        list: 需要复习的单词数据列表
    """
    try:
        conn = get_memory_connection(book_name, color)
        cursor = conn.cursor()
        
        # 获取今天需要复习的单词
        today = datetime.now().strftime("%Y-%m-%d")
        cursor.execute("""
        SELECT m.word, m.review_count, m.last_review_date, m.next_review_date, m.correct_count, m.error_count
        FROM memory_data m
        WHERE m.next_review_date <= ?
        """, (today,))
        
        memory_rows = cursor.fetchall()
        if not memory_rows:
            conn.close()
            return []
        
        # 获取单词详细信息
        review_words = []
        for row in memory_rows:
            word, review_count, last_review_date, next_review_date, correct_count, error_count = row
            
            # 获取单词详细信息
            cursor.execute("""
            SELECT meanings, examples, related_words, tags, note
            FROM words
            WHERE word = ?
            """, (word,))
            
            word_info = cursor.fetchone()
            if word_info:
                meanings, examples, related_words, tags, note = word_info
                
                word_data = {
                    "单词": word,
                    "释义": json.loads(meanings),
                    "例句": json.loads(examples) if examples else [],
                    "相关单词": json.loads(related_words) if related_words else [],
                    "标签": json.loads(tags) if tags else [],
                    "备注": note if note else "",
                    "复习次数": review_count,
                    "上次复习时间": last_review_date,
                    "下次复习时间": next_review_date,
                    "正确次数": correct_count,
                    "错误次数": error_count
                }
                
                review_words.append(word_data)
        
        conn.close()
        return review_words
    
    except Exception as e:
        print(f"Error getting review words: {e}")
        return []

def update_word_memory_status(book_name, color, word, is_correct):
    """
    更新单词的记忆状态
    
    Args:
        book_name (str): 单词本名称
        color (str): 单词本颜色
        word (str): 单词
        is_correct (bool): 是否回答正确
    """
    try:
        conn = get_memory_connection(book_name, color)
        cursor = conn.cursor()
        
        # 获取当前记忆状态
        cursor.execute("""
        SELECT review_count, correct_count, error_count
        FROM memory_data
        WHERE word = ?
        """, (word,))
        
        row = cursor.fetchone()
        if not row:
            conn.close()
            return
        
        review_count, correct_count, error_count = row
        review_count += 1
        today = datetime.now().strftime("%Y-%m-%d")
        
        if is_correct:
            correct_count += 1
            # 更新下次复习时间
            review_stage = min(review_count, len(MEMORY_INTERVALS) - 1)
            next_review_date = (datetime.now() + timedelta(days=MEMORY_INTERVALS[review_stage])).strftime("%Y-%m-%d")
        else:
            error_count += 1
            # 错误的单词第二天就复习
            next_review_date = (datetime.now() + timedelta(days=1)).strftime("%Y-%m-%d")
        
        # 更新记忆状态
        cursor.execute("""
        UPDATE memory_data SET 
            review_count = ?,
            last_review_date = ?,
            next_review_date = ?,
            correct_count = ?,
            error_count = ?
        WHERE word = ?
        """, (review_count, today, next_review_date, correct_count, error_count, word))
        
        conn.commit()
        conn.close()
    
    except Exception as e:
        print(f"Error updating word memory status: {e}")
        raise Exception(f"更新单词记忆状态失败: {str(e)}")