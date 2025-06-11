"""
Convenience re-exports so callers can simply:

    from ui.wordbook_button import WordBookButton, WordBookButtonViewModel
"""

from .view import WordBookButtonView
from .viewmodel import WordBookButtonViewModel

# Alias for backward-compat: treat the *view* as "the button widget".
WordBookButton = WordBookButtonView

__all__ = [
    "WordBookButtonView",
    "WordBookButtonViewModel",
    "WordBookButton",
]
