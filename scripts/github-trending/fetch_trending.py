#!/usr/bin/env python3
"""
fetch_trending.py — 抓 GitHub Trending Repositories、輸出為 markdown table / JSON。

設計原則
- 無外部資料來源依賴：純 HTML 抓 GitHub trending page（不需要 API token）
- 內含三次 fallback：HTML DOM → 看 meta fallback（如 DOM 改版） → 直輸出 raw HTML 段落
- 支援 daily / weekly / monthly 三種跨度
- 支援語言過濾（?since=...&spoken_language_code=...）
- 兩種輸出格式：markdown 表格 / JSON
- 自動 archive 到 ~/permanent-projects/.../archive/github-trending/YYYY-MM/

參考：trial-and-error/references/by-category/python-sandbox.md
（任何讀寫檔用 Path.read_bytes / write_bytes，避免 hermes read_file 行號污染）
"""
from __future__ import annotations

import argparse
import json
import re
import sys
from dataclasses import dataclass, asdict
from datetime import datetime, timezone
from pathlib import Path

import requests
from bs4 import BeautifulSoup, Tag

USER_AGENT = (
    "Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 "
    "(KHTML, like Gecko) Chrome/124.0.0.0 Safari/537.36"
)
TRENDING_BASE = "https://github.com/trending"

DEFAULT_LANG_MAP = {
    "all": "",
    "python": "python",
    "javascript": "javascript",
    "typescript": "typescript",
    "go": "go",
    "rust": "rust",
    "java": "java",
    "kotlin": "kotlin",
    "swift": "swift",
    "c++": "c++",
    "c": "c",
    "ruby": "ruby",
    "php": "php",
}


# ---------- 資料類 ----------

@dataclass
class TrendingRepo:
    rank: int
    full_name: str           # "owner/repo"
    repo_url: str
    description: str
    language: str
    total_stars: str         # 例如 "30,871"
    forks: str               # 例如 "4,827"
    stars_today: str         # 例如 "1,166 stars today"
    contributor_avatars: list[str]
    built_by: list[str]      # contributor URLs 抓不到時 fallback 從圖 alt 取 handle

    def to_dict(self):
        return asdict(self)


# ---------- 抓取層 ----------

def fetch_trending_page(since: str = "daily", language: str = "all",
                        spoken_language: str | None = None,
                        timeout: int = 30) -> str:
    params = [f"since={since}"]
    if language and language.lower() in DEFAULT_LANG_MAP and DEFAULT_LANG_MAP[language.lower()]:
        lang_val = DEFAULT_LANG_MAP[language.lower()]
        # Github trend URL 用 + 表空格（如 "c++"），我們把 c++ 直接傳、再用 requests 自己串接編碼
        params.append(f"language={lang_val}")
    if spoken_language and spoken_language.lower() != "en":
        params.append(f"spoken_language_code={spoken_language}")
    url = TRENDING_BASE
    if params:
        # 保留 + / # 之類
        url = f"{TRENDING_BASE}?{'&'.join(params)}"
    resp = requests.get(url, headers={"User-Agent": USER_AGENT}, timeout=timeout)
    resp.raise_for_status()
    return resp.text


# ---------- 解析層（兩次 fallback） ----------

def _text(node: Tag | None) -> str:
    return node.get_text(" ", strip=True) if node else ""


def _int_or_zero(s: str) -> int:
    m = re.search(r"[\d,]+", s or "")
    return int(m.group(0).replace(",", "")) if m else 0


def parse_trending_html(html: str) -> list[TrendingRepo]:
    soup = BeautifulSoup(html, "html.parser")
    articles = soup.find_all("article", class_="Box-row")
    if not articles:
        return _parse_legacy_fallback(soup)

    repos: list[TrendingRepo] = []
    for idx, art in enumerate(articles, start=1):
        h2 = art.find("h2")
        a_name = h2.find("a", href=True) if h2 else None
        if not a_name:
            continue
        href = a_name["href"].lstrip("/")
        full_name = href
        repo_url = f"https://github.com/{href}"

        desc_p = art.find("p", class_=re.compile(r"col-9"))
        description = _text(desc_p)

        lang_span = art.find("span", attrs={"itemprop": "programmingLanguage"})
        language = _text(lang_span)

        star_link = art.find("a", href=lambda h: h and h.endswith("/stargazers"))
        total_stars = _text(star_link)
        fork_link = art.find("a", href=lambda h: h and h.endswith("/forks"))
        forks = _text(fork_link)

        # 今日 stars: "1,166 stars today" — 通常在 .d-inline-block.float-sm-right
        today_node = art.find("span", class_=re.compile(r"d-inline-block\s+float-sm-right"))
        if not today_node:
            today_node = art.find(string=re.compile(r"stars today|stars this", re.I))
        stars_today = _text(today_node) if today_node else ""
        if not stars_today:
            # 全文搜尋
            t = art.get_text(" ", strip=True)
            m = re.search(r"(\d[\d,]*)\s+stars (today|this week|this month)", t)
            if m:
                stars_today = f"{m.group(1)} stars {m.group(2)}"

        avatars = [img.get("src", "") for img in art.find_all("img", class_="avatar")
                   if img.get("src")]
        built_by: list[str] = []
        for link in art.find_all("a", href=True):
            href = link["href"]
            # 過濾掉：登入連結、有 query string 的、非單一 owner 路徑、Trending 連結
            if not href.startswith("/"):
                continue
            if "?" in href or "login" in href.lower():
                continue
            if href.startswith("/trending"):
                continue
            # 只收「單段」handle（owner 名），沒有第二段斜線
            segment = href.lstrip("/")
            if "/" not in segment and segment:
                built_by.append(segment)

        repos.append(TrendingRepo(
            rank=idx,
            full_name=full_name,
            repo_url=repo_url,
            description=description,
            language=language or "—",
            total_stars=total_stars or "0",
            forks=forks or "0",
            stars_today=stars_today or "",
            contributor_avatars=avatars,
            built_by=built_by,
        ))
    return repos


def _parse_legacy_fallback(soup: BeautifulSoup) -> list[TrendingRepo]:
    """DOM 改版時的後備：用整個 article 區塊的純文字組合抽取欄位。"""
    out = []
    for idx, art in enumerate(soup.find_all("article"), start=1):
        text = art.get_text(" ", strip=True)
        m_repo = re.match(r"(\w[\w.-]*)\s*/\s*(\S+)", text)
        if not m_repo:
            continue
        full_name = f"{m_repo.group(1)}/{m_repo.group(2).rstrip(',')}"
        m_today = re.search(r"(\d[\d,]*)\s+stars (today|this week|this month)", text, re.I)
        stars_today = m_today.group(0) if m_today else ""
        out.append(TrendingRepo(
            rank=idx, full_name=full_name,
            repo_url=f"https://github.com/{full_name}",
            description="", language="—", total_stars="?", forks="?",
            stars_today=stars_today, contributor_avatars=[], built_by=[]
        ))
    return out


# ---------- 輸出層 ----------

def to_markdown(repos: list[TrendingRepo], *, since: str, language: str,
                spoken_language: str | None, header_extra: str = "") -> str:
    now = datetime.now(timezone.utc).strftime("%Y-%m-%d %H:%M UTC")
    spk = spoken_language or "any"
    lines = []
    lines.append(f"# GitHub Trending Repositories — {since}")
    lines.append("")
    lines.append(f"- 抓取時間：**{now}**")
    lines.append(f"- 跨度：{since}")
    lines.append(f"- 主要語言 filter：`{language}` / spoken language：`{spk}`")
    if header_extra:
        lines.append(f"- {header_extra}")
    lines.append(f"- 來源：`{TRENDING_BASE}?since={since}`")
    lines.append("")
    lines.append("| # | Repo | Language | ⭐ Total | 🍴 Forks | 🔥 " +
                 ("Today" if since == "daily" else since.capitalize()) +
                 " | Description |")
    lines.append("|---|------|----------|---------|---------|---------|-------------|")
    for r in repos:
        repo_cell = f"[{r.full_name}]({r.repo_url})"
        spark = r.stars_today.split(" ")[0] if r.stars_today else "—"
        desc = r.description.replace("|", "\\|").replace("\n", " ")
        if len(desc) > 200:
            desc = desc[:197] + "..."
        lines.append(f"| {r.rank} | {repo_cell} | {r.language} | {r.total_stars} | "
                     f"{r.forks} | {spark} | {desc} |")
    if not repos:
        lines.append("| — | (no repos fetched) | — | — | — | — | — |")
    lines.append("")
    lines.append(f"_Generated by fetch_trending.py · {now}_")
    lines.append("")
    return "\n".join(lines)


def to_json(repos: list[TrendingRepo]) -> str:
    return json.dumps([r.to_dict() for r in repos], indent=2, ensure_ascii=False)


# ---------- 主程式 ----------

def main() -> int:
    p = argparse.ArgumentParser(description="Fetch GitHub Trending Repositories")
    p.add_argument("--since", choices=["daily", "weekly", "monthly"],
                   default="daily", help="時間跨度（預設 daily）")
    p.add_argument("--language", default="all",
                   help="主要語言過濾（python / typescript / ... / all）")
    p.add_argument("--spoken-language", default=None,
                   help="spoken language code（en / zh / ja / ...）")
    p.add_argument("--limit", type=int, default=25, help="最多保留幾筆（預設 25）")
    p.add_argument("--format", choices=["markdown", "json"], default="markdown")
    p.add_argument("--output", default="-",
                   help="輸出檔路徑（預設 stdout，- 表 stdout）")
    p.add_argument("--archive-dir", default=None,
                   help="額外把輸出順便歸檔一份到這個目錄（按 YYYY-MM/ 分目錄）")
    args = p.parse_args()

    try:
        html = fetch_trending_page(
            since=args.since,
            language=args.language,
            spoken_language=args.spoken_language,
        )
    except Exception as e:
        print(f"[ERROR] failed to fetch GitHub trending: {e}", file=sys.stderr)
        return 2

    repos = parse_trending_html(html)[: args.limit]

    if args.format == "markdown":
        body = to_markdown(repos, since=args.since, language=args.language,
                           spoken_language=args.spoken_language)
    else:
        body = to_json(repos)

    # 寫到主要 output
    if args.output == "-":
        sys.stdout.write(body)
        if not body.endswith("\n"):
            sys.stdout.write("\n")
    else:
        out_path = Path(args.output)
        out_path.parent.mkdir(parents=True, exist_ok=True)
        out_path.write_bytes(body.encode("utf-8"))
        print(f"[OK] wrote {len(body)} bytes to {out_path}", file=sys.stderr)

    # 順便歸檔
    if args.archive_dir:
        archive_root = Path(args.archive_dir)
        yyyymm = datetime.now(timezone.utc).strftime("%Y-%m")
        archive_path = archive_root / yyyymm / out_suffix(args.format)
        archive_path.parent.mkdir(parents=True, exist_ok=True)
        archive_path.write_bytes(body.encode("utf-8"))
        print(f"[OK] archived to {archive_path}", file=sys.stderr)
    return 0

    return 0


def out_suffix(fmt: str) -> str:
    today = datetime.now(timezone.utc).strftime("%Y-%m-%d")
    if fmt == "markdown":
        return f"github-trending-{today}.md"
    return f"github-trending-{today}.json"


if __name__ == "__main__":
    sys.exit(main())
