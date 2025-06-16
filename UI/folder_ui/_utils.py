import math
from typing import Sequence, Tuple, Union
from PySide6.QtCore import QPoint, QRect
import os
import sys
from pathlib import Path
from PIL import Image

def calculate_button_distance(btn1, btn2, button_width, button_height):
    """
    计算两个按钮中心点之间的距离
    """
    center1 = btn1.pos() + QPoint(button_width // 2, button_height // 2)
    center2 = btn2.pos() + QPoint(button_width // 2, button_height // 2)
    dx = center1.x() - center2.x()
    dy = center1.y() - center2.y()
    return math.sqrt(dx * dx + dy * dy)


def is_button_in_frame(button, frame):
    """
    检查按钮是否在框架内
    """
    button_rect = QRect(button.pos(), button.size())
    frame_rect = QRect(frame.pos(), frame.size())
    return frame_rect.contains(button_rect)


def create_folder_icon(
    sub_icon_paths: Sequence[Union[str, Path]],
    folder_name: str,
    out_path: Union[str, Path] = None,
    *,
    cell_size: int = 120,                 # ⬆️ 缩略图默认尺寸
    grid_size: Tuple[int, int] = (3, 3),
    spacing: int = 1,                    # ⬇️ 间距默认
    bg_color: Tuple[int, int, int, int] = (0, 0, 0, 0),
) -> str:
    """
    将最多 9 张子图标拼成一个九宫格缩略图（iOS 文件夹风格）。

    Parameters
    ----------
    sub_icon_paths : Sequence[str | Path]
        子按钮图标的文件路径列表。
    folder_name : str
        文件夹名称，用于生成输出文件名（格式为 ``folder_<文件夹名称>.png``）。
    out_path : str | Path, optional
        输出文件路径；为空则自动写入 <程序目录>/icon/ 目录，且文件名遵循
        ``folder_<文件夹名称>.png`` 的规则。
    cell_size : int, default 120
        单个子图在九宫格里的边长（像素）。
    grid_size : (int, int), default (3, 3)
        网格列数 × 行数。
    spacing : int, default 1
        子图之间以及与外边缘的间距。
    bg_color : (R, G, B, A), default (255, 255, 255, 0)
        背景颜色（含透明度）。

    Returns
    -------
    str
        合成图保存的绝对路径
    """
    # ---------- 计算整体尺寸 ----------
    cols, rows = grid_size
    total_w = cols * cell_size + (cols + 1) * spacing
    total_h = rows * cell_size + (rows + 1) * spacing
    canvas = Image.new("RGBA", (total_w, total_h), bg_color)

    # ---------- 粘贴子图 ----------
    for idx, icon_path in enumerate(sub_icon_paths[: rows * cols]):
        try:
            icon = Image.open(icon_path).convert("RGBA").resize(
                (cell_size, cell_size), Image.LANCZOS
            )
        except (FileNotFoundError, OSError):
            continue

        col = idx % cols
        row = idx // cols
        x = spacing + col * (cell_size + spacing)
        y = spacing + row * (cell_size + spacing)
        canvas.alpha_composite(icon, (x, y))

    # ---------- 保存 ----------
    if out_path is None:
        base_dir = Path(os.path.dirname(os.path.abspath(sys.argv[0]))) / "icon"
        base_dir.mkdir(parents=True, exist_ok=True)
        # 统一命名：folder_<文件夹名称>.png
        out_path = base_dir / f"folder_{folder_name}.png"

    out_path = Path(out_path)
    canvas.save(out_path)
    return str(out_path)

def update_all_folder_icons(app) -> None:
    """Update folder icons for every folder button under ``app``."""
    for btn in getattr(app, "buttons", []):
        if getattr(btn, "is_folder", False) and hasattr(btn, "update_folder_icon"):
            btn.update_folder_icon()

