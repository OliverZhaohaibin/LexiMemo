"""Service package public interface.

Re‑export the main service classes so callers can simply do:

    from services import WordBookService
"""

from .wordbook_service import WordBookService

__all__: list[str] = [
    "WordBookService",
]
