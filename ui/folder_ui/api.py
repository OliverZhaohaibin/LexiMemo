# ui/folder_ui/api.py开始
"""Public façade for the *Folder ui* subsystem.

External modules – notably *CoverContent*, *WordBookButton*, or any editor
plugins – should import all Folder‑related ui behaviour exclusively from this
module.  Doing so decouples them from the internal physical layout of the
package, which may evolve over time.

Example
-------
from ui.folder_ui.api import FolderLayoutMixin, ButtonFrame # Corrected import example

All symbols listed in ``__all__`` below are guaranteed to remain stable across
minor releases.
"""

from __future__ import annotations

from ._layout import (
    FolderLayoutMixin,
    calculate_main_button_positions,
    calculate_sub_button_positions,
    calculate_folder_area,
    calculate_reorder_area
)
from ._operations import FolderOperationMixin
from ._animations import (
    FolderAnimationMixin,
    create_folder_toggle_animation,
    create_button_position_animation
)
from ._background import (
    update_all_folder_backgrounds,
    update_folder_background,
    FolderBackground,
)
from ._hints import FolderHintMixin
from ._frame import ButtonFrame # This is the generic frame for hints
from ._utils import create_folder_icon, calculate_button_distance, is_button_in_frame

__all__: list[str] = [
    "FolderLayoutMixin",
    "calculate_main_button_positions", # Exporting helper if needed directly
    "calculate_sub_button_positions",
    "calculate_folder_area",
    "calculate_reorder_area",
    "FolderOperationMixin",
    "FolderAnimationMixin",
    "create_folder_toggle_animation", # Exporting helper if needed directly
    "create_button_position_animation",
    "FolderHintMixin",
    "update_all_folder_backgrounds",
    "update_folder_background",
    "FolderBackground",
    "ButtonFrame",
    "create_folder_icon",
    "calculate_button_distance",
    "is_button_in_frame",
]
# ui/folder_ui/api.py结束