from __future__ import annotations


from services.wordbook_service import WordBookService
from ui.word_book_button import WordBookButtonViewModel


class WordBookButtonController:
    """
    Orchestrates high-level use-cases for a WordBook button.
    Receives ‘intent’ signals from the ViewModel and delegates to Service.
    """

    def __init__(
        self,
        vm: WordBookButtonViewModel,
        service: WordBookService | None = None,
    ) -> None:
        self._vm = vm
        self._service = service or WordBookService.get_instance()

        # Wire VM-level signals ➜ local handlers
        vm.rename_requested.connect(self._handle_rename)
        vm.delete_requested.connect(self._handle_delete)
        vm.open_requested.connect(self._handle_open)

    # --------------------------------------------------------------------- #
    # Signal handlers
    # --------------------------------------------------------------------- #
    def _handle_rename(self, new_name: str) -> None:
        """Rename the underlying WordBook then tell VM to update its state."""
        updated = self._service.rename(self._vm.book, new_name)
        self._vm.update_domain(updated)

    def _handle_delete(self) -> None:
        """Delete the WordBook and tell VM/ui to reflect the removal."""
        self._service.delete(self._vm.book)
        self._vm.notify_deleted()

    def _handle_open(self) -> None:
        """Open the book in its dedicated editor/window."""
        # 你可在 Service 层实现更复杂的逻辑；这里简单转给 VM。
        self._vm.open_in_editor()


__all__ = ["WordBookButtonController"]
