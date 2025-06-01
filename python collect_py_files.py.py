#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
collect_py_files.py

遍历根目录下所有 .py 文件，输出：
1. py_structure.txt          —— 目录结构（仅列出含 .py 的目录与文件）
2. combined_py_code.txt      —— 合并后的源码（带“开始/结束”标记）

用法：
    python collect_py_files.py <root_dir> [-s STRUCT_FILE] [-c COMBINED_FILE]
"""
from __future__ import annotations

import argparse
import os
from pathlib import Path
from typing import List


def find_py_files(root: Path) -> List[Path]:
    """递归收集 root 下的全部 .py 文件（按相对路径排序）"""
    return sorted(
        (p for p in root.rglob("*.py") if p.is_file()),
        key=lambda p: p.relative_to(root).as_posix()
    )


def write_structure(root: Path, py_files: List[Path], outfile: Path) -> None:
    """
    按目录层级写出仅含 .py 的“树状结构”：
    project/
        package/
            module.py
    """
    # 先收集每个目录下有哪些 py
    dirs_with_py: set[Path] = {p.parent for p in py_files}
    # 自底向上把父目录也加进来（以便保持层级完整）
    for d in list(dirs_with_py):
        while d != root:
            d = d.parent
            dirs_with_py.add(d)

    with outfile.open("w", encoding="utf-8") as f:
        def _walk(current: Path, depth: int = 0) -> None:
            indent = "    " * depth
            if current != root:  # 根目录名称通常显而易见，可省略
                f.write(f"{indent}{current.name}/\n")
            sub_indent = indent + "    "
            # 输出当前目录下的 .py 文件
            for py in sorted(p for p in current.iterdir() if p.suffix == ".py"):
                f.write(f"{sub_indent}{py.name}\n")
            # 递归子目录
            for sub in sorted(p for p in current.iterdir() if p.is_dir()):
                if sub in dirs_with_py:
                    _walk(sub, depth + 1)

        _walk(root)


def write_combined(root: Path, py_files: List[Path], outfile: Path) -> None:
    """把所有 .py 文件源码合并输出"""
    with outfile.open("w", encoding="utf-8") as f:
        for path in py_files:
            rel = path.relative_to(root).as_posix()
            f.write(f"{rel}开始\n")
            f.write(path.read_text(encoding="utf-8", errors="ignore"))
            f.write(f"\n{rel}结束\n\n")


def main() -> None:
    parser = argparse.ArgumentParser(...)
    parser.add_argument(
        "root_dir",
        nargs="?",  # 变成可选
        type=Path,
        default=Path.cwd(),  # 默认用当前工作目录
        help="根目录路径（默认=当前工作目录）"
    )
    parser.add_argument(
        "-s", "--structure-file",
        type=Path,
        default=Path("py_structure.txt"),
        help="目录结构输出文件（默认 py_structure.txt）"
    )
    parser.add_argument(
        "-c", "--combined-file",
        type=Path,
        default=Path("combined_py_code.txt"),
        help="合并源码输出文件（默认 combined_py_code.txt）"
    )
    args = parser.parse_args()

    root = args.root_dir.resolve()
    if not root.is_dir():
        raise SystemExit(f"错误：{root} 不是有效的目录。")

    py_files = find_py_files(root)
    if not py_files:
        print("未找到任何 .py 文件，未生成输出。")
        return

    write_structure(root, py_files, args.structure_file.resolve())
    write_combined(root, py_files, args.combined_file.resolve())

    print(f"已生成：\n  - {args.structure_file.resolve()}\n  - {args.combined_file.resolve()}")


if __name__ == "__main__":
    main()