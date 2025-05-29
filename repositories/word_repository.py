"""repositories/word_repository.py
---------------------------------
Wrap db.py helpers so upper layers never import db directly.
"""
from __future__ import annotations

from typing import Any, Dict, List

from db import (
    load_words as _load_words,
    save_word as _save_word,
    delete_word as _delete_word,
)


class WordRepository:
    """Thin data-access wrapper."""

    # -------- Query --------
    @staticmethod
    def list_words(book_name: str, color: str) -> List[Dict[str, Any]]:
        return _load_words(book_name, color)

    # -------- Save / Update --------
    @staticmethod
    def save_word(
        book_name: str,
        color: str,
        data: Dict[str, Any],
        *,
        sync_to_total: bool = True,
    ) -> None:
        _save_word(book_name, color, data, sync_to_total=sync_to_total)

    # -------- Delete --------
    @staticmethod
    def delete_word(book_name: str, color: str, word: str) -> None:
        _delete_word(book_name, color, word)
