#!/usr/bin/env python3
"""
github_trending.py — Scrape GitHub Trending repositories and emit a Markdown table.

Usage:
    python3 github_trending.py                       # daily trending, default language
    python3 github_trending.py --language python     # filter by language
    python3 github_trending.py --since weekly        # daily | weekly | monthly
    python3 github_trending.py --language go --since weekly --output trending.md
    python3 github_trending.py --top 50              # GitHub shows 25 per page; --top>25 triggers pagination
"""
from __future__ import annotations

import argparse
import sys
from dataclasses import dataclass, field
from datetime import datetime, timezone
from typing import List, Optional
from urllib.parse import urljoin

import requests
from bs4 import BeautifulSoup

GITHUB_TRENDING_URL = "https://github.com/trending"
DEFAULT_HEADERS = {
    "User-Agent": (
        "Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 "
        "(KHTML, like Gecko) Chrome/124.0.0.0 Safari/537.36"
    ),
    "Accept-Language": "en-US,en;q=0.9",
}
VALID_SINCE = {"daily", "weekly", "monthly"}
PER_PAGE = 25  # GitHub returns ~25 per page on trending


@dataclass
class Repo:
    rank: int
    full_name: str           # "owner/repo"
    url: str
    description: str
    language: str            # primary language or "—"
    stars_total: int
    stars_period: int        # stars gained in the trending window
    forks: int
    contributors: List[str] = field(default_factory=list)

    @property
    def slug(self) -> str:
        return self.full_name.split("/", 1)[-1]


def parse_count(text: str) -> int:
    """Convert '1,234' / '12.3k' / '1.2m' into int. Returns 0 on garbage."""
    if not text:
        return 0
    s = text.strip().replace(",", "").lower()
    if s in {"", "—", "-", "n/a"}:
        return 0
    mult = 1
    if s.endswith("k"):
        mult, s = 1_000, s[:-1]
    elif s.endswith("m"):
        mult, s = 1_000_000, s[:-1]
    try:
        return int(float(s) * mult)
    except ValueError:
        return 0


def fetch_page(session: requests.Session, language: str, since: str, page: int) -> str:
    params = {"since": since}
    if language:
        params["language"] = language
    if page > 1:
        params["page"] = page  # empirical: github honors ?page=N on trending
    resp = session.get(GITHUB_TRENDING_URL, params=params, headers=DEFAULT_HEADERS, timeout=20)
    resp.raise_for_status()
    return resp.text


def parse_articles(html: str) -> List[Repo]:
    soup = BeautifulSoup(html, "html.parser")
    repos: List[Repo] = []
    for idx, article in enumerate(soup.find_all("article", class_="Box-row"), start=1):
        # --- name + url ---
        h2 = article.find("h2", class_="h3")
        a = h2.find("a", href=True) if h2 else None
        href = a["href"].strip() if a else ""
        # href like "/owner/repo"
        full_name = href.strip("/").split("?")[0] if href else ""
        url = urljoin("https://github.com", href) if href else ""

        # --- description (p.col-9) ---
        desc_p = article.find("p", class_="col-9")
        description = desc_p.get_text(strip=True).replace("\n", " ") if desc_p else ""

        # --- language ---
        lang_span = article.find("span", itemprop="programmingLanguage")
        language = lang_span.get_text(strip=True) if lang_span else "—"

        # --- meta line: stars total / forks / contributors ---
        # Anchor text order in trending HTML (current observed):  "Total stars" link
        # then optional "Built by" contributors, then "Forks". Be defensive.
        meta_links = article.select("div.color-fg-muted a.Link--muted")
        stars_total = 0
        forks = 0
        for link in meta_links:
            txt = link.get_text(" ", strip=True)
            href_l = link.get("href", "")
            if href_l.endswith("/forks") or "/forks" in href_l:
                forks = parse_count(txt)
            else:
                # star count link is the first non-fork muted link
                stars_total = parse_count(txt)

        # --- period stars (the small "X stars today/this week/this month") ---
        period_span = article.find("span", class_="d-inline-block float-sm-right")
        stars_period = 0
        if period_span:
            raw = period_span.get_text(" ", strip=True)
            # e.g. "1,234 stars today" / "120 stars this week"
            digits = raw.split(" stars ", 1)[0].strip()
            stars_period = parse_count(digits)

        # --- contributors (optional, "Built by") ---
        contributors_a = article.select("span.d-inline-block a.Link--muted, "
                                         "span.d-inline-block img.avatar-user")
        contributors = []
        for c in contributors_a:
            if c.name == "a" and c.get("href"):
                contributors.append(c["href"].strip("/").split("/")[-1])
        # also catch avatar-only images (alt text holds username)
        for img in article.select("span.d-inline-block img.avatar-user"):
            alt = img.get("alt", "").lstrip("@")
            if alt and alt not in contributors:
                contributors.append(alt)

        repos.append(Repo(
            rank=idx,
            full_name=full_name,
            url=url,
            description=description,
            language=language,
            stars_total=stars_total,
            stars_period=stars_period,
            forks=forks,
            contributors=contributors[:5],
        ))
    return repos


def fetch_repos(language: str, since: str, top: int) -> List[Repo]:
    """Fetch up to `top` repos.

    Note: GitHub Trending does not expose true pagination — `?page=N` returns
    the same ~25 trending items (or, in some sessions, a partially-overlapping
    earlier snapshot). Each (language, since) combination caps at PER_PAGE.
    We paginate defensively but stop the moment page 2+ doesn't add *new*
    repos (full overlap) so we never inflate the table with duplicates.
    """
    session = requests.Session()
    all_repos: List[Repo] = []
    page = 1
    while len(all_repos) < top and page <= 5:
        html = fetch_page(session, language, since, page)
        batch = parse_articles(html)
        if not batch:
            break
        seen_slugs = {r.slug for r in all_repos}
        new_batch = [r for r in batch if r.slug not in seen_slugs]
        if page > 1 and not new_batch:
            break  # page 2+ is a full re-show, no more content
        for i, r in enumerate(new_batch, start=len(all_repos) + 1):
            r.rank = i
        all_repos.extend(new_batch)
        if len(batch) < PER_PAGE:
            break
        page += 1
    return all_repos[:top]


def _md_escape(text: str) -> str:
    """Escape pipes and newlines so markdown tables don't break."""
    if not text:
        return ""
    return text.replace("|", "\\|").replace("\n", " ").replace("\r", " ").strip()


def to_markdown(repos: List[Repo], language: str, since: str) -> str:
    title_lang = language or "all languages"
    since_label = {"daily": "today", "weekly": "this week", "monthly": "this month"}[since]
    timestamp = datetime.now(timezone.utc).strftime("%Y-%m-%d %H:%M UTC")

    lines: List[str] = []
    lines.append(f"# GitHub Trending — {title_lang} ({since_label})")
    lines.append("")
    lines.append(f"_Scraped at {timestamp}. Source: https://github.com/trending_")
    lines.append("")
    lines.append("| # | Repository | Description | Language | ⭐ Total | ⭐ "
                 f"{since_label.capitalize()} | Forks |")
    lines.append("|---|------------|-------------|----------|---------:|------:|------:|")
    if not repos:
        lines.append("| — | _No repositories found_ | | | | | |")
    else:
        for r in repos:
            lines.append(
                f"| {r.rank} | [{_md_escape(r.full_name)}]({r.url}) | "
                f"{_md_escape(r.description)} | {_md_escape(r.language)} | "
                f"{r.stars_total:,} | {r.stars_period:,} | {r.forks:,} |"
            )
    lines.append("")
    lines.append(f"**Total repositories:** {len(repos)}")
    lines.append("")
    return "\n".join(lines)


def main(argv: Optional[List[str]] = None) -> int:
    ap = argparse.ArgumentParser(description="Scrape GitHub Trending → Markdown table.")
    ap.add_argument("--language", default="", help="Filter by language (e.g. python, go, rust). Empty = all.")
    ap.add_argument("--since", default="daily", choices=sorted(VALID_SINCE),
                    help="Time window (daily/weekly/monthly). Default: daily")
    ap.add_argument("--top", type=int, default=25,
                    help="How many repositories to fetch (max 125). Default: 25")
    ap.add_argument("--output", "-o", default="",
                    help="Write Markdown to this file. Default: stdout")
    args = ap.parse_args(argv)

    if args.top < 1 or args.top > 125:
        ap.error("--top must be between 1 and 125")

    try:
        repos = fetch_repos(args.language, args.since, args.top)
    except requests.HTTPError as e:
        print(f"[error] GitHub returned HTTP {e.response.status_code}", file=sys.stderr)
        return 2
    except requests.RequestException as e:
        print(f"[error] Network failure: {e}", file=sys.stderr)
        return 2

    md = to_markdown(repos, args.language, args.since)

    if args.output:
        with open(args.output, "w", encoding="utf-8") as f:
            f.write(md)
        print(f"[ok] Wrote {len(repos)} repos → {args.output}", file=sys.stderr)
    else:
        print(md)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())