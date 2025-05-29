# repositories/tag_repository.py
"""
纯数据访问层：所有【标签】相关的持久化操作
"""
from db import get_all_tags as _get_all_tags, save_tags as _save_tags


class TagRepository:
    """封装 db.py 里的标签 API，保证 UI/Service 不直接依赖 db.py"""

    @staticmethod
    def list_tags(book_name: str, color: str) -> list[str]:
        """返回指定单词本的全部标签（按字典序）"""
        return _get_all_tags(book_name, color)

    @staticmethod
    def add_tag(book_name: str, color: str, new_tag: str) -> None:
        """向指定单词本追加单个标签（自动去重）"""
        tags = _get_all_tags(book_name, color)
        if new_tag not in tags:
            tags.append(new_tag)
            _save_tags(book_name, color, tags)
