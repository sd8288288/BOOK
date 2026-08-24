#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
扫描仓库内的 .txt 小说，生成 books.json 书架清单。
- 整仓扫描（默认）或仅扫描 BOOKS_DIR 指定目录。
- 书名提取：跳过空白与装饰行（=== --- —— 等），跳过整行方括号标签（【xxx】），
  跳过章节标题行（第X章/Chapter X），优先取首个长度合理（2-40）的有意义行；
  都失败则回退到文件名。
- 编码：依次尝试 utf-8-sig → gb18030（兼容 GBK），再失败用 utf-8 兜底。
- 删除某 txt 后重跑，清单自动不再包含它（从头生成，不增量合并）。
- 可选 .booksignore：每行一个子串，路径包含该子串的 .txt 被忽略（# 开头为注释）。
"""
import json
import os
import re

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
OUT = "books.json"
BOOKS_DIR = os.environ.get("BOOKS_DIR", "").strip()
DENY_DIRS = {".git", ".github", "scripts", "node_modules", "assets"}

CHAPTER_RE = re.compile(
    r"^\s*第\s*[0-9零一二三四五六七八九十百千万两]+\s*[章回卷节部篇集]"
    r"|^\s*chapter\s+\d+",
    re.I,
)
# 装饰行：纯 = - — * · … _ ~ ` | 重复（≥4 个）
DECORATIVE_RE = re.compile(r"^[\s=\-—*·…_~`|]{4,}$")
# 整行方括号标签：例如 【内容简介】 【作者】
BRACKET_LABEL_RE = re.compile(r"^【.+】$")


def read_text(path):
    """按 utf-8-sig → gb18030 顺序尝试解码；都失败则 utf-8 兜底。"""
    with open(path, "rb") as f:
        raw = f.read()
    for enc in ("utf-8-sig", "gb18030"):
        try:
            return raw.decode(enc)
        except UnicodeDecodeError:
            continue
    return raw.decode("utf-8", errors="replace")


# 通用节标签/元数据（不是书名）
SECTION_LABELS = {
    "正文", "正文卷", "序章", "序", "前言", "楔子", "引子", "序言",
    "目录", "后记", "番外", "外传", "简介", "内容简介", "作品相关",
    "卷一", "卷二",
}
# 广告/下载站/作者元数据等提示词
AD_HINTS = ("http://", "https://", "www.", "下载", "更多", "精校吧", "@", "作者")


def is_likely_title(s):
    """判断一行文字是否「像书名」：长度合理、无句末标点、非广告/作者元数据。"""
    if not (2 <= len(s) <= 40):
        return False
    if re.search(r"[。！？!?]", s):
        return False
    low = s.lower()
    for hint in AD_HINTS:
        if hint in low:
            return False
    if s in SECTION_LABELS:
        return False
    return True


def clean_stem(stem):
    """去掉「作者：xxx」后缀，得到更干净的书名。"""
    s = re.sub(r"作者[::].*$", "", stem).strip()
    return s or stem


def title_of(path):
    fallback = clean_stem(os.path.splitext(os.path.basename(path))[0])
    try:
        text = read_text(path)
    except Exception:
        return fallback
    candidates = []
    for line in text.splitlines():
        s = line.strip()
        if not s:
            continue
        if DECORATIVE_RE.match(s):
            continue
        if BRACKET_LABEL_RE.match(s):
            continue
        if CHAPTER_RE.match(s):
            continue
        candidates.append(s)
        if len(candidates) >= 8:
            break
    for s in candidates:
        if is_likely_title(s):
            return s[:40]
    # 文件首部没有合适的书名行 → 回退到（已清理的）文件名
    return fallback


def load_ignore():
    p = os.path.join(ROOT, ".booksignore")
    if not os.path.isfile(p):
        return []
    with open(p, "r", encoding="utf-8") as f:
        return [
            ln.strip()
            for ln in f.read().splitlines()
            if ln.strip() and not ln.strip().startswith("#")
        ]


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
                    if any(sub in rel for sub in ignore):
                        continue
                    books.append({"file": rel, "title": title_of(full)})
    else:
        for dirpath, dirnames, filenames in os.walk(ROOT):
            # 剪枝：deny + ignore
            dirnames[:] = [
                d for d in dirnames
                if d not in DENY_DIRS
                and not any(
                    sub in os.path.join(dirpath, d).replace("\\", "/")
                    for sub in ignore
                )
            ]
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
