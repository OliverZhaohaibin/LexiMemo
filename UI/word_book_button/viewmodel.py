from __future__ import annotations

from pathlib import Path
from typing import Optional

from PySide6.QtCore import QObject, Signal

from repositories.wordbook_repository import  WordBook
from services.wordbook_service import WordBookService
from UI.word_book_button.view import WordBookButtonView


class WordBookButtonViewModel(QObject):
    """
    Glue between pure-view (Qt widget) and pure-business (Service).
    Keeps lightweight state that the View *renders*.
    """

    # Re-expose intent signals upward (Controller may also subscribe)
    rename_requested = Signal(str)
    delete_requested = Signal()
    open_requested = Signal()

    def __init__(
        self,
        book: WordBook,
        view: WordBookButtonView,
        service: Optional[WordBookService] = None,
        parent=None,
    ) -> None:
        super().__init__(parent)
        self._book = book
        self._view = view
        self._svc = service or WordBookService.get_instance()

        # 1) Forward View → VM public signals
        view.renameRequested.connect(self.rename_requested)
        view.deleteRequested.connect(self.delete_requested)
        view.openRequested.connect(self.open_requested)

        # 2) Handle View → business directly when Controller absent
        view.renameRequested.connect(self._on_rename)
        view.deleteRequested.connect(self._on_delete)
        view.openRequested.connect(self._on_open)

    # ------------------------------------------------------------------ #
    # Public API (used by Controller or outer UI)
    # ------------------------------------------------------------------ #
    @property
    def book(self) -> WordBook:
        return self._book

    def update_domain(self, book: WordBook) -> None:
        """Replace the underlying domain obj & refresh view."""
        self._book = book
        self._view.setText(book.name)

    def notify_deleted(self) -> None:
        """Disable the button visually after deletion."""
        self._view.setEnabled(False)

    def open_in_editor(self) -> None:
        """Default behaviour: open book path in OS explorer (overrideable)."""
        from PySide6.QtGui import QDesktopServices, QGuiApplication
        if self._book.path:
            QDesktopServices.openUrl(Path(self._book.path).as_uri())
        else:
            QGuiApplication.beep()

    # ------------------------------------------------------------------ #
    # Internal slots (View ➜ direct business)
    # ------------------------------------------------------------------ #
    def _on_rename(self, new_name: str) -> None:
        updated = self._svc.rename(self._book, new_name)
        self.update_domain(updated)

    def _on_delete(self) -> None:
        self._svc.delete(self._book)
        self.notify_deleted()

    def _on_open(self) -> None:
        self.open_in_editor()
