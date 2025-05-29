# services/cover_layout_service.py
"""
Cover 布局业务封装：UI <-> Repository 中间层，便于后期加缓存、版本迁移等。
"""
from typing import Any, Dict, List
from repositories.layout_repository import LayoutRepository


class CoverLayoutService:
    @staticmethod
    def load() -> List[Dict[str, Any]]:
        return LayoutRepository.load_layout()

    @staticmethod
    def save(layout_items: List[Dict[str, Any]]) -> None:
        LayoutRepository.save_layout(layout_items)
