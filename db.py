# db.py
import os
import sys
import sqlite3
import json
from datetime import datetime

def get_db_path(book_name, color):
    """
    获取SQLite数据库文件路径
    
    Args:
        book_name (str): 单词本名称
        color (str): 单词本颜色
        
    Returns:
        str: 数据库文件路径
    """
    base_dir = os.path.dirname(os.path.abspath(sys.argv[0]))
    directory = os.path.join(base_dir, "books")
    os.makedirs(directory, exist_ok=True)
    folder_name = f"books_{book_name}_{color}"
    path = os.path.join(directory, folder_name)
    os.makedirs(path, exist_ok=True)
    return os.path.join(path, "wordbook.db")

def get_total_db_path():
    """
    获取总单词本数据库路径
    
    Returns:
        str: 总单词本数据库路径
    """
    return get_db_path("总单词册", "#FF0000")

def init_db(db_path):
    """
    初始化数据库，创建必要的表
    
    Args:
        db_path (str): 数据库文件路径
    """
    conn = sqlite3.connect(db_path)
    cursor = conn.cursor()
    
    # 创建单词表
    cursor.execute('''
    CREATE TABLE IF NOT EXISTS words (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        word TEXT NOT NULL,
        meanings TEXT NOT NULL,  -- JSON格式存储释义列表
        examples TEXT,           -- JSON格式存储例句列表
        related_words TEXT,      -- JSON格式存储相关单词列表
        tags TEXT,               -- JSON格式存储标签列表
        note TEXT,               -- 备注
        timestamp TEXT,          -- 时间戳
        UNIQUE(word)
    )
    ''')
    
    # 创建标签表
    cursor.execute('''
    CREATE TABLE IF NOT EXISTS tags (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        tag TEXT NOT NULL UNIQUE
    )
    ''')
    
    conn.commit()
    conn.close()

def get_connection(book_name, color):
    """
    获取数据库连接
    
    Args:
        book_name (str): 单词本名称
        color (str): 单词本颜色
        
    Returns:
        sqlite3.Connection: 数据库连接对象
    """
    db_path = get_db_path(book_name, color)
    init_db(db_path)  # 确保数据库和表已创建
    return sqlite3.connect(db_path)

def load_words(book_name, color):
    """
    从数据库加载单词数据
    
    Args:
        book_name (str): 单词本名称
        color (str): 单词本颜色
        
    Returns:
        list: 单词数据列表
    """
    try:
        conn = get_connection(book_name, color)
        cursor = conn.cursor()
        
        cursor.execute("SELECT word, meanings, examples, related_words, tags, note, timestamp FROM words")
        rows = cursor.fetchall()
        
        words = []
        for row in rows:
            word, meanings, examples, related_words, tags, note, timestamp = row
            word_data = {
                "单词": word,
                "释义": json.loads(meanings),
                "例句": json.loads(examples) if examples else [],
                "相关单词": json.loads(related_words) if related_words else [],
                "标签": json.loads(tags) if tags else [],
                "备注": note if note else "",
                "时间": timestamp
            }
            words.append(word_data)
            
        conn.close()
        return words
    except Exception as e:
        print(f"Error loading words from database: {e}")
        return []

def save_word(book_name, color, data, sync_to_total=True):
    """
    保存 / 更新单词数据到数据库（『覆盖式』）。
    · 若单词不存在 ——> 直接插入
    · 若单词已存在 ——> 以最新提交的数据完全覆盖旧记录
      —— 这样才能正确处理『删除释义 / 例句』等编辑场景。
    """
    try:
        conn    = get_connection(book_name, color)
        cursor  = conn.cursor()

        # ---------- 1) 整理并去重 ----------
        word         = data["单词"]
        new_meanings = list(dict.fromkeys(data["释义"]))                # 去重但保持顺序
        new_examples = data.get("例句", [])
        new_related  = list(dict.fromkeys(data.get("相关单词", [])))
        new_tags     = list(dict.fromkeys(data.get("标签", [])))
        note         = data.get("备注", "")
        timestamp    = data.get("时间", datetime.now().strftime("%Y-%m-%d %H:%M:%S"))

        # 例句条数不足时用空串占位，保证与释义等长
        if len(new_examples) < len(new_meanings):
            new_examples += [""] * (len(new_meanings) - len(new_examples))

        # ---------- 2) 查询是否已存在 ----------
        cursor.execute("SELECT id FROM words WHERE word = ?", (word,))
        row = cursor.fetchone()

        # ---------- 3) 覆盖更新 / 新增 ----------
        if row:        # ---- 更新 ----
            word_id = row[0]
            cursor.execute("""
                UPDATE words SET
                    meanings      = ?,
                    examples      = ?,
                    related_words = ?,
                    tags          = ?,
                    note          = ?,
                    timestamp     = ?
                WHERE id = ?
            """, (
                json.dumps(new_meanings, ensure_ascii=False),
                json.dumps(new_examples, ensure_ascii=False),
                json.dumps(new_related, ensure_ascii=False),
                json.dumps(new_tags,    ensure_ascii=False),
                note,
                timestamp,
                word_id
            ))
        else:          # ---- 插入 ----
            cursor.execute("""
                INSERT INTO words (
                    word, meanings, examples, related_words, tags, note, timestamp
                ) VALUES (?, ?, ?, ?, ?, ?, ?)
            """, (
                word,
                json.dumps(new_meanings, ensure_ascii=False),
                json.dumps(new_examples, ensure_ascii=False),
                json.dumps(new_related,  ensure_ascii=False),
                json.dumps(new_tags,     ensure_ascii=False),
                note,
                timestamp
            ))

        # ---------- 4) 新标签入库 ----------
        for tag in new_tags:
            cursor.execute("INSERT OR IGNORE INTO tags (tag) VALUES (?)", (tag,))

        conn.commit()
        conn.close()

        # ---------- 5) 同步到总单词册（同样采用覆盖策略） ----------
        if sync_to_total and book_name != "总单词册":
            sync_data        = data.copy()
            sync_data["备注"] = ""          # 总册不保留备注
            save_word_to_total(sync_data)

    except Exception as e:
        raise Exception(f"保存单词到数据库失败：{str(e)}")


def save_word_to_total(data):
    """
    保存单词到总单词本（#FF0000）。
    修复：同样基于『释义-例句对』精细合并，避免出现释义空行或例句错位。
    """
    try:
        conn   = get_connection("总单词册", "#FF0000")
        cursor = conn.cursor()

        word          = data["单词"]
        new_meanings  = data["释义"]
        new_examples  = data.get("例句", [])
        new_related   = data.get("相关单词", [])
        new_tags      = data.get("标签", [])
        timestamp     = data.get("时间", datetime.now().strftime("%Y-%m-%d %H:%M:%S"))

        if len(new_examples) < len(new_meanings):
            new_examples += [""] * (len(new_meanings) - len(new_examples))

        cursor.execute(
            "SELECT id, meanings, examples, related_words, tags FROM words WHERE word = ?",
            (word,),
        )
        existing = cursor.fetchone()

        if existing:
            # ---------- 合并 ----------
            word_id, om_json, oe_json, or_json, ot_json = existing
            old_meanings = json.loads(om_json)
            old_examples = json.loads(oe_json) if oe_json else []
            old_related  = json.loads(or_json) if or_json else []
            old_tags     = json.loads(ot_json) if ot_json else []

            merged_meanings, merged_examples = _merge_meanings_examples(
                old_meanings, old_examples, new_meanings, new_examples
            )

            merged_related = old_related + [r for r in new_related if r not in old_related]
            merged_tags    = old_tags    + [t for t in new_tags if t not in old_tags]

            cursor.execute(
                """
                UPDATE words SET
                    meanings      = ?,
                    examples      = ?,
                    related_words = ?,
                    tags          = ?,
                    timestamp     = ?
                WHERE id = ?
                """,
                (
                    json.dumps(merged_meanings, ensure_ascii=False),
                    json.dumps(merged_examples, ensure_ascii=False),
                    json.dumps(merged_related, ensure_ascii=False),
                    json.dumps(merged_tags, ensure_ascii=False),
                    timestamp,
                    word_id,
                ),
            )
        else:
            # ---------- 直接插入 ----------
            cursor.execute(
                """
                INSERT INTO words (
                    word, meanings, examples,
                    related_words, tags, note, timestamp
                ) VALUES (?, ?, ?, ?, ?, ?, ?)
                """,
                (
                    word,
                    json.dumps(new_meanings, ensure_ascii=False),
                    json.dumps(new_examples, ensure_ascii=False),
                    json.dumps(new_related, ensure_ascii=False),
                    json.dumps(new_tags, ensure_ascii=False),
                    "",        # 总单词册不记录备注
                    timestamp,
                ),
            )

        # ---- 标签入库 ----
        for tag in new_tags:
            cursor.execute("INSERT OR IGNORE INTO tags (tag) VALUES (?)", (tag,))

        conn.commit()
        conn.close()

    except Exception as e:
        raise Exception(f"保存单词到总单词本失败：{str(e)}")
def get_all_tags(book_name, color):
    """
    获取所有标签
    
    Args:
        book_name (str): 单词本名称
        color (str): 单词本颜色
        
    Returns:
        list: 标签列表
    """
    try:
        conn = get_connection(book_name, color)
        cursor = conn.cursor()
        
        cursor.execute("SELECT tag FROM tags ORDER BY tag")
        tags = [row[0] for row in cursor.fetchall()]
        
        conn.close()
        return tags
    except Exception as e:
        print(f"Error getting tags from database: {e}")
        return []

def save_tags(book_name, color, tags):
    """
    保存标签到数据库
    
    Args:
        book_name (str): 单词本名称
        color (str): 单词本颜色
        tags (list): 标签列表
    """
    try:
        conn = get_connection(book_name, color)
        cursor = conn.cursor()
        
        # 清空现有标签
        cursor.execute("DELETE FROM tags")
        
        # 插入新标签
        for tag in tags:
            cursor.execute("INSERT INTO tags (tag) VALUES (?)", (tag,))
        
        conn.commit()
        conn.close()
    except Exception as e:
        print(f"Error saving tags to database: {e}")

def delete_word(book_name, color, word):
    """
    从数据库删除单词
    
    Args:
        book_name (str): 单词本名称
        color (str): 单词本颜色
        word (str): 要删除的单词
    """
    try:
        conn = get_connection(book_name, color)
        cursor = conn.cursor()
        
        cursor.execute("DELETE FROM words WHERE word = ?", (word,))
        
        conn.commit()
        conn.close()
    except Exception as e:
        raise Exception(f"删除单词失败：{str(e)}")

# ======== 1. 释义-例句 合并工具 ========
def _merge_meanings_examples(
    old_meanings: list[str],
    old_examples: list[str],
    new_meanings: list[str],
    new_examples: list[str],
) -> tuple[list[str], list[str]]:
    """
    按『释义-例句』成对合并，解决：
      • 仅凭释义去重 → 例句丢失
      • 释义已存在但旧例句为空 → 写入新例句
      • 同一释义可保留多条不同例句
    """
    # --- 长度对齐 ---
    if len(old_examples) < len(old_meanings):
        old_examples += [""] * (len(old_meanings) - len(old_examples))

    # --- 逐对处理 ---
    for m, ex in zip(new_meanings, new_examples):
        # a. 查找所有同释义的位置
        idx_list = [i for i, om in enumerate(old_meanings) if om == m]

        updated = False
        for idx in idx_list:
            # ① 完全重复 → 跳过
            if old_examples[idx] == ex:
                updated = True
                break
            # ② 旧例句为空 → 填充
            if not old_examples[idx] and ex:
                old_examples[idx] = ex
                updated = True
                break

        if updated:
            continue    # 已处理

        # b. 释义不存在 / 未匹配成功 → 追加新对
        old_meanings.append(m)
        old_examples.append(ex)

    return old_meanings, old_examples