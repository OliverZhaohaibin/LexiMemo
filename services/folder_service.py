# services/folder_service.py开始
from __future__ import annotations
import os
import sys
from typing import List, Dict, Any, TYPE_CHECKING

from UI.word_book_button import WordBookButton

if TYPE_CHECKING:
    from UI.word_book_cover.cover_content import CoverContent  # For type hinting


class FolderService:
    """Business‑logic layer for the word_book_cover page operations related to folders and buttons."""

    def __init__(self) -> None:
        self.content: 'CoverContent' | None = None

    def build_buttons(self, cover_content_instance: 'CoverContent') -> List[WordBookButton]:
        """扫描 books/ 目录并以新 WordBookButton 创建按钮列表。"""
        self.content = cover_content_instance

        base_dir = os.path.dirname(os.path.abspath(sys.argv[0]))
        books_dir = os.path.join(base_dir, "books")
        os.makedirs(books_dir, exist_ok=True)

        # -- 确保「总单词册」文件夹存在 ------------------------------------
        main_name, main_color = "总单词册", "#FF0000"
        main_folder = f"books_{main_name}_{main_color}"
        main_path = os.path.join(books_dir, main_folder)
        if not os.path.exists(main_path):
            os.makedirs(main_path, exist_ok=True)
            from db import init_db as _init_db
            _init_db(os.path.join(main_path, "wordbook.db"))

        # -- 枚举磁盘目录，整理元数据 ------------------------------------
        metas: list[Dict[str, str]] = []
        for d in os.listdir(books_dir):
            p = os.path.join(books_dir, d)
            if not (d.startswith("books_") and os.path.isdir(p)):
                continue
            try:
                _, nm, cl = d.split("_", 2)
                metas.append({"name": nm, "color": cl, "folder": d})
            except ValueError:
                continue

        metas.sort(key=lambda m: (m["name"] != main_name, m["name"]))

        buttons: list[WordBookButton] = []
        for m in metas:
            path = os.path.join(books_dir, m["folder"])

            btn = WordBookButton(m["name"], m["color"], parent=self.content)  # ★ 不再传 app=
            # —— 兼容旧逻辑：补挂属性 —— #
            btn.app = self.content
            btn.path = path
            btn.color = m["color"]
            btn.is_folder = False
            btn.is_sub_button = False
            # Ensure button is visible and has a default size
            btn.setFixedSize(self.content.button_width, self.content.button_height)  # Use CoverContent's dimensions
            btn.show()  # Explicitly show the button to ensure visibility



            buttons.append(btn)

        self.content.buttons = buttons
        # Trigger layout update to position buttons correctly
        if hasattr(self.content, 'update_button_positions'):
            self.content.update_button_positions()

        return buttons

    def set_edit_mode(self, entering: bool, buttons_on_content: list[WordBookButton]) -> None:
        """Toggles edit mode for buttons (jitter, delete visibility)."""
        if not self.content: return

        for b in buttons_on_content:
            if not getattr(b, 'is_new_button', False):
                if entering:
                    b.start_jitter()
                else:
                    b.stop_jitter()

        if hasattr(self.content, 'new_book_button'):
            if entering:
                self.content.new_book_button.start_jitter()
            else:
                self.content.new_book_button.stop_jitter()

        if entering:
            for b_main in buttons_on_content:
                if b_main.is_folder and b_main.is_expanded:
                    for sub_b in b_main.sub_buttons:
                        sub_b.start_jitter()

    def highlight_search(self, kw: str, buttons_on_content: list[WordBookButton]) -> None:
        kw_lc = kw.strip().lower()
        all_buttons_to_check = buttons_on_content[:]
        if hasattr(self.content, 'new_book_button'):
            all_buttons_to_check.append(self.content.new_book_button)

        for b in all_buttons_to_check:
            if getattr(b, "is_new_button", False) and b is not self.content.new_book_button:
                continue

            original_stylesheet = getattr(b, '_original_stylesheet', b.styleSheet())
            if not hasattr(b, '_original_stylesheet'):
                b._original_stylesheet = original_stylesheet

            is_match = kw_lc and kw_lc in b.text().lower()

            current_style = b.styleSheet()
            border_highlight = "border:2px solid #e67e22;"

            if is_match:
                if border_highlight not in current_style:
                    import re
                    style_no_border = re.sub(r"border:.*?;", "", current_style, flags=re.IGNORECASE)
                    style_no_border = re.sub(r"\s\s+", " ", style_no_border).strip()
                    if style_no_border and not style_no_border.endswith(';'):
                        style_no_border += ";"
                    b.setStyleSheet(style_no_border + " " + border_highlight if style_no_border else border_highlight)
            else:
                b.setStyleSheet(original_stylesheet)

    def show_new_wordbook_dialog(self) -> tuple[bool, str | None, str | None]:
        from UI.new_wordbook_dialog import NewWordBookDialog
        parent_window = self.content.window() if self.content else None
        dlg = NewWordBookDialog(parent_window)
        if dlg.exec():
            return True, dlg.book_name, dlg.book_color
        return False, None, None

    def export_layout(self, buttons_on_content: list[WordBookButton]) -> List[Dict[str, Any]]:
        """Exports the current layout of buttons and folders."""
        items = []
        for btn in buttons_on_content:
            if getattr(btn, "is_new_button", False): continue

            item_data: Dict[str, Any] = {
                "name": btn.text(),
                "color": btn.color,
            }
            if btn.path:  # Store path if available
                item_data["path"] = btn.path

            if btn.is_folder:
                item_data["type"] = "folder"
                item_data["is_expanded"] = btn.is_expanded
                item_data["sub_books"] = []
                for sub in btn.sub_buttons:
                    sub_book_data = {
                        "name": sub.text(),
                        "color": sub.color,
                    }
                    if sub.path:
                        sub_book_data["path"] = sub.path
                    item_data["sub_books"].append(sub_book_data)
            else:
                item_data["type"] = "wordbook"
            items.append(item_data)
        return items

    def apply_layout(
        self,
        layout_items: List[Dict[str, Any]],
        current_buttons_from_scan: list[WordBookButton],
    ) -> None:
        """根据保存的布局重建按钮顺序 / 文件夹结构。"""
        if not self.content:
            return

        # ---------- 1. 统一补充缺失属性 ----------
        for b in current_buttons_from_scan:
            if not hasattr(b, "color"):
                b.color = getattr(b, "_color", "#999999")   # 默认灰，基本不会用到
            if not hasattr(b, "is_folder"):
                b.is_folder = False
            if not hasattr(b, "is_sub_button"):
                b.is_sub_button = False

        # ---------- 2. 建立检索索引 ----------
        path_to_scan = {b.path: b for b in current_buttons_from_scan if b.path}
        name_color_to_scan = {f"{b.text()}_{b.color}": b for b in current_buttons_from_scan}

        new_main_buttons: list[WordBookButton] = []
        processed: set[str] = set()

        # ---------- 3. 按布局文件逐条构建 ----------
        for spec in layout_items:
            name, color = spec.get("name"), spec.get("color")
            path, typ   = spec.get("path"), spec.get("type")

            # 先在扫描结果里找现成的按钮
            btn = None
            if path and path in path_to_scan:
                btn = path_to_scan[path]
            elif name and color and f"{name}_{color}" in name_color_to_scan:
                btn = name_color_to_scan[f"{name}_{color}"]

            # —— 文件夹 —— #
            if typ == "folder":
                folder_btn = btn or WordBookButton(name, color, parent=self.content)
                folder_btn.color = color             # 确保属性存在
                folder_btn.app   = self.content
                folder_btn.is_folder   = True
                folder_btn.is_expanded = spec.get("is_expanded", False)
                folder_btn.sub_buttons = []
                folder_btn.setFixedSize(self.content.button_width, self.content.button_height)

                # 处理子按钮
                for sub in spec.get("sub_books", []):
                    s_name, s_color, s_path = sub.get("name"), sub.get("color"), sub.get("path")
                    sub_btn = None
                    if s_path and s_path in path_to_scan:
                        sub_btn = path_to_scan[s_path]
                    elif s_name and s_color and f"{s_name}_{s_color}" in name_color_to_scan:
                        sub_btn = name_color_to_scan[f"{s_name}_{s_color}"]

                    if sub_btn and (sub_btn.path or sub_btn.text()):
                        sub_btn.color = getattr(sub_btn, "color", getattr(sub_btn, "_color", s_color))
                        sub_btn.is_sub_button = True
                        sub_btn.parent_folder = folder_btn
                        folder_btn.sub_buttons.append(sub_btn)
                        processed.add(sub_btn.path or f"{sub_btn.text()}_{sub_btn.color}")

                folder_btn.update_folder_icon = getattr(folder_btn, "update_folder_icon", lambda: None)
                folder_btn.update_folder_icon()
                if folder_btn.is_expanded:
                    for sb in folder_btn.sub_buttons:
                        sb.show()
                else:
                    for sb in folder_btn.sub_buttons:
                        sb.hide()
                new_main_buttons.append(folder_btn)
                processed.add(path or f"{name}_{color}")

            # —— 普通单词本 —— #
            elif typ == "wordbook":
                word_btn = btn or WordBookButton(name, color, parent=self.content)
                word_btn.color = color
                word_btn.app   = self.content
                word_btn.is_folder = False
                word_btn.setFixedSize(self.content.button_width, self.content.button_height)
                new_main_buttons.append(word_btn)
                processed.add(path or f"{name}_{color}")

        # ---------- 4. 把扫描到但布局缺失的按钮追加到末尾 ----------
        for b in current_buttons_from_scan:
            key = b.path or f"{b.text()}_{b.color}"
            if key not in processed:
                new_main_buttons.append(b)

        # ---------- 5. 写回 CoverContent ----------
        self.content.buttons = new_main_buttons
        self.content.update_button_positions()

# services/folder_service.py结束