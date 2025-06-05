# repositories/wordbook_repository.py
from __future__ import annotations

from dataclasses import dataclass, field
from pathlib import Path
from typing import List, Optional


# ---------- 纯数据：WordBook (原 domain.wordbook.WordBook) ----------
@dataclass
class WordBook:
    name: str
    color: str = "#ffffff"
    path: Optional[Path] = None
    is_folder: bool = False
    sub_books: List["WordBook"] = field(default_factory=list)


# ---------- 持久化层：示例 Repository ----------
class WordBookRepository:
    """负责磁盘 / SQLite 的增删改查，这里只给骨架示例。"""

    def rename(self, book: WordBook, new_name: str) -> WordBook: ...
    def delete(self, book: WordBook) -> None: ...
    def save(self, book: WordBook) -> None: ...
    def load_all(self) -> List[WordBook]: ...


__all__ = ["WordBook", "WordBookRepository"]
