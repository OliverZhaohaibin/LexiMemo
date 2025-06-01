"""Public façade for the *Folder UI* subsystem.

External modules – notably *CoverContent*, *WordBookButton*, or any editor
plugins – should import all Folder‑related UI behaviour exclusively from this
module.  Doing so decouples them from the internal physical layout of the
package, which may evolve over time.

Example
-------
from ui.folder_ui.api import FolderLayoutMixin, ButtonFrame

All symbols listed in ``__all__`` below are guaranteed to remain stable across
minor releases.
"""

from __future__ import annotations

from ._layout import FolderLayoutMixin
from ._operations import FolderOperationMixin
from ._animations import FolderAnimationMixin
from ._background import (
    update_all_folder_backgrounds,
    update_folder_background,
)
from ._frame import ButtonFrame

__all__: list[str] = [
    "FolderLayoutMixin",
    "FolderOperationMixin",
    "FolderAnimationMixin",
    "update_all_folder_backgrounds",
    "update_folder_background",
    "ButtonFrame",
]
