# repositories/layout_repository.py
"""持久化 Cover 布局 JSON（不做任何业务校验）"""
import json
import os
import sys
from typing import Any, Dict, List


def _layout_file_path() -> str:
    base_dir = os.path.dirname(os.path.abspath(sys.argv[0]))
    return os.path.join(base_dir, "cover_layout.json")


class LayoutRepository:
    @staticmethod
    def load_layout() -> List[Dict[str, Any]]:
        """读取 cover_layout.json，异常时返回空列表"""
        path = _layout_file_path()
        if not os.path.exists(path):
            return []
        try:
            with open(path, "r", encoding="utf-8") as f:
                data = json.load(f)
            return data.get("layout", [])
        except Exception:
            return []

    @staticmethod
    def save_layout(layout_items: List[Dict[str, Any]]) -> None:
        path = _layout_file_path()
        try:
            with open(path, "w", encoding="utf-8") as f:
                json.dump({"layout": layout_items}, f, ensure_ascii=False, indent=2)
        except Exception as exc:
            raise RuntimeError(f"保存 cover 布局失败: {exc}") from exc
