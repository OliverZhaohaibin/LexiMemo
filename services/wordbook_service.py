"""services/wordbook_service.py
-------------------------------------------------
High‑level business logic façade used by every UI layer.
UI components must talk to this class instead of accessing repositories or
`db.py` directly.  The service orchestrates repositories, applies validation
or additional business rules (if any) and offers a *stable* API.
"""
from __future__ import annotations

from typing import List

from domain.models import Word, WordBook

from repositories.word_repository import WordRepository
from repositories.wordbook_repository import WordBookRepository


class WordBookService:
    """Business methods for word‑book CRUD operations."""

    _instance: "WordBookService" | None = None

    def __init__(self) -> None:
        self._repo = WordBookRepository()

    @classmethod
    def get_instance(cls) -> "WordBookService":
        if cls._instance is None:
            cls._instance = cls()
        return cls._instance

    # ------------------------------------------------------------------
    # READ
    # ------------------------------------------------------------------
    @staticmethod
    def list_words(book_name: str, book_color: str) -> List[Word]:
        """Return all words from the specified book.

        Thin wrapper for :py:meth:`repositories.word_repository.WordRepository.list_words`.
        UI should always call this instead of repositories directly so that
        later we can introduce caching, filtering or async loading without
        touching UI code.
        """
        return WordRepository.list_words(book_name, book_color)

    # ------------------------------------------------------------------
    # CREATE / UPDATE (Up‑sert)
    # ------------------------------------------------------------------
    @staticmethod
    def save_word(
        book_name: str,
        book_color: str,
        word: Word,
        *,
        sync_to_total: bool = True,
    ) -> None:
        """Insert or update a word.

        Currently just delegates to the repository.  Validation hooks can be
        added here later (e.g. ensure the word field is not empty, strip
        whitespace, etc.).
        """
        WordRepository.save_word(
            book_name,
            book_color,
            word,
            sync_to_total=sync_to_total,
        )

    # ------------------------------------------------------------------
    # DELETE
    # ------------------------------------------------------------------
    @staticmethod
    def delete_word(book_name: str, book_color: str, word: str) -> None:
        """Delete a word from the specified book."""
        WordRepository.delete_word(book_name, book_color, word)

    # ------------------------------------------------------------------
    # WORD BOOK MANIPULATION
    # ------------------------------------------------------------------
    def rename(self, book: WordBook, new_name: str) -> WordBook:
        """Rename a word book on disk and return the updated domain object."""
        updated = self._repo.rename(book, new_name)
        return updated

    # ------------------------------------------------------------------
    # WORD BOOK CREATE / DELETE
    # ------------------------------------------------------------------
    def create_wordbook(self, name: str, color: str) -> WordBook:
        """Create a new word book on disk and return the domain object."""
        book = WordBook(name=name, color=color)
        self._repo.save(book)
        return book

    def delete_wordbook(self, book: WordBook) -> None:
        """Delete the specified word book from disk."""
        self._repo.delete(book)
