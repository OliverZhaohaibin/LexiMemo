# services/memory_service.py
"""
背单词 / 记忆曲线业务层。供 memory_curve.py 及未来其它 UI 使用。
"""
import pandas as pd
from datetime import datetime, timedelta

from repositories.memory_repository import MemoryRepository

# 复习间隔（与 db_memory 保持一致，集中管理更方便）
DEFAULT_INTERVALS = [0, 1, 2, 4, 7, 15, 30]


class MemoryService:
    # ---------- DataFrame 存取 ----------
    @staticmethod
    def load_memory_df(book: str, color: str) -> pd.DataFrame:
        return MemoryRepository.load_memory_df(book, color)

    @staticmethod
    def save_memory_df(book: str, color: str, df: pd.DataFrame) -> None:
        MemoryRepository.save_memory_df(book, color, df)

    # ---------- 今日待复习列表 ----------
    @staticmethod
    def get_review_words(book: str, color: str) -> list[dict]:
        return MemoryRepository.get_today_review_words(book, color)

    # ---------- 更新单词结果 ----------
    @staticmethod
    def record_answer(
        book: str, color: str, word: str, is_correct: bool, *,
        intervals: list[int] = DEFAULT_INTERVALS,
    ) -> None:
        """
        更新答题结果，并根据是否正确推算下一次复习时间（在 repo 内完成）。
        """
        MemoryRepository.update_word_status(book, color, word, is_correct)
