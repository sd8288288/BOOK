#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
扫描仓库内的 .txt 小说，生成 books.json 书架清单。
- 支持整仓扫描（默认）或仅扫描指定目录（环境变量 BOOKS_DIR）。
- 书名取「首个非空行」；若该行像章节标题（第X章/Chapter X），则回退为文件名。
- 删除某 txt 后重跑，清单自动不再包含它（从头生成，不增量合并）。
- 可选 .booksignore：每行一个子串，路径包含该子串的 .txt 被忽略。
"""
import json
import os
import re

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))  # 仓库根 = scripts/ 的父目录
OUT = "books.json"
BOOKS_DIR = os.environ.get("BOOKS_DIR", "").strip()  # 留空=整仓扫描
DENY_DIRS = {".git", ".github", "scripts", "node_modules", "assets"}
CHAPTER_RE = re.compile(r'^\s*第\s*[0-9零一二三四五六七八九十百千万两]+\s*[章回卷节部篇集]|^\s*chapter\s+\d+', re.I)


def title_of(path):
    try:
        with open(path, "r", encoding="utf-8-sig", errors="ignore") as f:
            head = f.read(2048)
    except Exception:
        return os.path.splitext(os.path.basename(path))[0]
    for line in head.splitlines():
        line = line.strip()
        if not line:
            continue
        if CHAPTER_RE.match(line):
            return os.path.splitext(os.path.basename(path))[0]
        return line[:60]
    return os.path.splitext(os.path.basename(path))[0]


def load_ignore():
    p = os.path.join(ROOT, ".booksignore")
    if not os.path.isfile(p):
        return []
    with open(p, "r", encoding="utf-8") as f:
        return [ln.strip() for ln in f.read().splitlines() if ln.strip()]


def main():
    ignore = load_ignore()
    books = []

    if BOOKS_DIR:
        base = BOOKS_DIR
        for name in sorted(os.listdir(base)):
            if name.lower().endswith(".txt"):
                full = os.path.join(base, name)
                if os.path.isfile(full):
                    rel = (base.rstrip("/") + "/" + name).replace("\\", "/")
                    books.append({"file": rel, "title": title_of(full)})
    else:
        for dirpath, dirnames, filenames in os.walk(ROOT):
            dirnames[:] = [d for d in dirnames if d not in DENY_DIRS]
            for fn in filenames:
                if not fn.lower().endswith(".txt"):
                    continue
                full = os.path.join(dirpath, fn)
                rel = os.path.relpath(full, ROOT).replace("\\", "/")
                if rel == OUT:
                    continue
                if any(sub in rel for sub in ignore):
                    continue
                books.append({"file": rel, "title": title_of(full)})

    books.sort(key=lambda b: b["title"])
    out_path = os.path.join(ROOT, OUT)
    with open(out_path, "w", encoding="utf-8") as f:
        json.dump(books, f, ensure_ascii=False, indent=2)
        f.write("\n")
    print("Generated %s with %d book(s):" % (OUT, len(books)))
    for b in books:
        print("  - %s  ->  %s" % (b["title"], b["file"]))


if __name__ == "__main__":
    main()
