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

    def rename(self, book: WordBook, new_name: str) -> WordBook:
        import os, sys

        base_dir = os.path.dirname(os.path.abspath(sys.argv[0]))
        books_dir = os.path.join(base_dir, "books")

        old_folder = f"books_{book.name}_{book.color}"
        new_folder = f"books_{new_name}_{book.color}"
        old_path = os.path.join(books_dir, old_folder)
        new_path = os.path.join(books_dir, new_folder)

        if old_path != new_path:
            if os.path.exists(new_path):
                raise FileExistsError(f"目标文件夹 '{new_folder}' 已存在。")
            if os.path.exists(old_path):
                os.rename(old_path, new_path)
            else:
                os.makedirs(new_path, exist_ok=True)
                from db import init_db
                init_db(os.path.join(new_path, "wordbook.db"))

        book.name = new_name
        book.path = Path(new_path)
        return book

    def delete(self, book: WordBook) -> None: ...
    def save(self, book: WordBook) -> None: ...
    def load_all(self) -> List[WordBook]: ...


__all__ = ["WordBook", "WordBookRepository"]
