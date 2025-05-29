# repositories/memory_repository.py
"""
纯数据访问层：背单词 / 记忆曲线相关持久化
"""
import pandas as pd
from db_memory import (
    load_memory_data as _load,
    save_memory_data as _save,
    get_review_words as _review,
    update_word_memory_status as _update,
)


class MemoryRepository:
    """对 db_memory.py 做一次薄封装"""

    # ---------- DataFrame 全量读 / 写 ----------
    @staticmethod
    def load_memory_df(book: str, color: str) -> pd.DataFrame:
        return _load(book, color)

    @staticmethod
    def save_memory_df(book: str, color: str, df: pd.DataFrame) -> None:
        _save(book, color, df)

    # ---------- 业务片段 ----------
    @staticmethod
    def get_today_review_words(book: str, color: str) -> list[dict]:
        return _review(book, color)

    @staticmethod
    def update_word_status(book: str, color: str, word: str, is_correct: bool) -> None:
        _update(book, color, word, is_correct)
