# services/tag_service.py
"""
面向 UI 的标签业务层。
"""
from repositories.tag_repository import TagRepository

_MAIN_BOOK = "总单词册"
_MAIN_COLOR = "#FF0000"


class TagService:
    # ---------- 查询 ----------
    @staticmethod
    def list_tags(book: str, color: str) -> list[str]:
        return TagRepository.list_tags(book, color)

    # ---------- 新增 ----------
    @staticmethod
    def add_tag(book: str, color: str, tag: str) -> None:
        """向当前册添加标签，并确保同步到『总单词册』"""
        TagRepository.add_tag(book, color, tag)
        if book != _MAIN_BOOK:
            TagRepository.add_tag(_MAIN_BOOK, _MAIN_COLOR, tag)
