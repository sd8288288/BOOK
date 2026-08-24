// 解析逻辑验证：与 index.html 内正则保持一致，校验多种格式的切分结果
import { readFileSync } from "fs";

const PATTERNS = [
  { key: "cn", re: /^\s*第\s*[0-9零一二三四五六七八九十百千万两]+\s*[章回卷节部篇集]/ },
  { key: "en", re: /^\s*chapter\s+[0-9]+\b/i },
  { key: "num", re: /^\s*[0-9]+[\.．、]\s*\S+/ },
];
const isTitleLine = (l, re) => re.test(l);

function parseNovel(raw) {
  const text = (raw || "").replace(/﻿/g, "");
  const lines = text.split(/\r?\n/);
  const trimmed = lines.map((l) => l.replace(/\s+$/, ""));
  let best = null;
  for (const p of PATTERNS) {
    let count = 0;
    for (const l of trimmed) if (isTitleLine(l, p.re)) count++;
    if (count >= 2 && (!best || count > best.count)) best = { p, count };
  }
  if (!best) return [{ title: "正文", paragraphs: trimmed.filter(Boolean) }];
  const re = best.p.re;
  const chapters = [];
  let cur = null;
  for (const l of trimmed) {
    if (isTitleLine(l, re)) {
      cur = { title: l.trim(), lines: [] };
      chapters.push(cur);
    } else if (cur) cur.lines.push(l);
  }
  return chapters.map((c) => ({ title: c.title, text: c.lines.join("\n").trim() }));
}

let pass = 0, fail = 0;
function check(name, cond) { if (cond) { pass++; console.log("  ✓", name); } else { fail++; console.log("  ✗", name); } }

// 1. 中文 第X章
const a = readFileSync(new URL("./novel.txt", import.meta.url), "utf8");
const ca = parseNovel(a);
check("中文第X章 -> 5章", ca.length === 5);
check("第一章标题正确", ca[0].title === "第一章 启程");
check("第一章有正文", ca[0].text.includes("林默站在车站"));

// 2. 英文 Chapter
const b = "Prologue\nSome text.\nChapter 1 The Beginning\nHello world.\nChapter 2 The End\nGoodbye.\n";
const cb = parseNovel(b);
check("英文Chapter -> 2章(无前言)", cb.length === 2);
check("Chapter 1 标题", cb[0].title === "Chapter 1 The Beginning");

// 3. 第X回 (古典)
const c = "第一回 风雪夜\nfoo\n第二回 相逢\nbar\n";
const cc = parseNovel(c);
check("第一回/第二回 -> 2章", cc.length === 2);
check("第一回标题", cc[0].title === "第一回 风雪夜");

// 4. 无章节 -> 单章兜底
const d = "这是一段没有章节标题的普通文字。\n它应该被当作整本处理。\n";
const cd = parseNovel(d);
check("无章节 -> 1章", cd.length === 1 && cd[0].title === "正文");

// 5. 带 BOM 与空行
const e = "﻿第一章 甲\n\n正文A\n\n第二章 乙\n正文B\n";
const ce = parseNovel(e);
check("BOM+空行 -> 2章", ce.length === 2);

console.log(`\n结果：${pass} 通过 / ${fail} 失败`);
process.exit(fail ? 1 : 0);
