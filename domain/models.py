from __future__ import annotations

from dataclasses import dataclass, field
from pathlib import Path
from typing import List, Optional


@dataclass
class Word:
    text: str
    meanings: List[str]
    examples: List[str] = field(default_factory=list)
    related_words: List[str] = field(default_factory=list)
    tags: List[str] = field(default_factory=list)
    note: str = ""
    timestamp: str = ""

    @staticmethod
    def from_dict(data: dict) -> "Word":
        return Word(
            text=str(data.get("单词", "")),
            meanings=list(data.get("释义", [])),
            examples=list(data.get("例句", [])),
            related_words=list(data.get("相关单词", [])),
            tags=list(data.get("标签", [])),
            note=str(data.get("备注", "")),
            timestamp=str(data.get("时间", "")),
        )

    def to_dict(self) -> dict:
        return {
            "单词": self.text,
            "释义": self.meanings,
            "例句": self.examples,
            "相关单词": self.related_words,
            "标签": self.tags,
            "备注": self.note,
            "时间": self.timestamp,
        }


@dataclass
class WordBook:
    name: str
    color: str = "#ffffff"
    path: Optional[Path] = None
    is_folder: bool = False
    sub_books: List["WordBook"] = field(default_factory=list)
