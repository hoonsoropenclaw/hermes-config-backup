#!/usr/bin/env python3
"""
scrape_trending.py
==================
Fetch GitHub trending repositories and render them as a Markdown table.

Two data sources are supported:

1. ``scrape`` (default)  -> scrape https://github.com/trending/<lang>?since=<daily|weekly|monthly>
   This is the *real* GitHub trending list, ranked by star velocity by humans.
   No auth needed, but is sensitive to HTML structure changes.

2. ``api``               -> REST ``/search/repositories`` with quality filter,
   sorted by stars, filter ``created:>`` over the last 7 days. This is *not*
   GitHub's trending rank (which is velocity-based + velocity-weighted) but it
   gives a more stable, structured snapshot.

Usage:
    python scrape_trending.py                          # daily, all languages, top 25
    python scrape_trending.py --language python --since weekly
    python scrape_trending.py --backend api --limit 50 --output trending.md
    python scrape_trending.py --language rust --since monthly --limit 10

Exit codes:
    0 success
    1 partial failure (some rows couldn't be parsed)
    2 total failure (no rows at all)
"""

from __future__ import annotations

import argparse
import json
import os
import re
import sys
import time
import urllib.error
import urllib.parse
import urllib.request
from dataclasses import dataclass, field, asdict
from datetime import datetime, timedelta, timezone
from pathlib import Path
from typing import Optional

# BeautifulSoup is the only third-party dependency. It is already installed in
# the system Python (4.13.5 confirmed at write time).
try:
    from bs4 import BeautifulSoup  # type: ignore
    _HAS_BS4 = True
except ImportError:  # pragma: no cover
    _HAS_BS4 = False


USER_AGENT = (
    "Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 "
    "(KHTML, like Gecko) Chrome/124.0 Safari/537.36 "
    "(compatible; hermes-trending-scraper/1.0)"
)
REQUEST_TIMEOUT = 25  # seconds
DEFAULT_LIMIT = 25
MAX_LIMIT = 100


# ---------------------------------------------------------------------------
# Data model
# ---------------------------------------------------------------------------


@dataclass
class TrendingRepo:
    """A single trending repo record. Fields are kept short for table layout."""

    rank: int
    full_name: str           # e.g. "owner/repo"
    url: str                 # full https URL
    description: str         # short, may be empty
    language: str            # may be empty if unknown
    stars_total: int
    stars_period: int        # stars accumulated in the chosen period
    period: str              # "today", "this week", "this month"
    forks: int
    contributors: int = 0    # api backend only
    primary_topic: str = ""  # api backend only

    @property
    def display_name(self) -> str:
        return self.full_name

    def to_markdown_row(self) -> str:
        # Escape pipes so a rogue pipe in description does not break the table.
        def safe(value: str) -> str:
            return value.replace("|", "\\|").replace("\n", " ").strip()

        desc = safe(self.description) if self.description else "—"
        lang = safe(self.language) if self.language else "—"
        # Markdown link to the repo (display as the full_name for readability)
        repo_link = f"[{safe(self.full_name)}]({self.url})"
        stars_total = f"{self.stars_total:,}"
        stars_period = f"+{self.stars_period:,}"
        return (
            f"| {self.rank} | {repo_link} | {desc} | {lang} "
            f"| {stars_total} | {stars_period} |"
        )


# ---------------------------------------------------------------------------
# HTTP helpers
# ---------------------------------------------------------------------------


def _http_get(url: str, headers: Optional[dict] = None, timeout: int = REQUEST_TIMEOUT) -> bytes:
    """urllib HTTP GET with a UA header. Raises urllib.error.HTTPError on failure."""
    h = {"User-Agent": USER_AGENT, "Accept": "text/html,application/json"}
    if headers:
        h.update(headers)
    req = urllib.request.Request(url, headers=h)
    with urllib.request.urlopen(req, timeout=timeout) as r:
        return r.read()


def _load_github_token() -> Optional[str]:
    """Try to find a GitHub token from env or gh CLI config."""
    tok = os.environ.get("GH_TOKEN") or os.environ.get("GITHUB_TOKEN")
    if tok:
        return tok.strip()
    gh_hosts = Path.home() / ".config" / "gh" / "hosts.yml"
    if gh_hosts.exists():
        try:
            # very loose parse -- avoid PyYAML dependency
            text = gh_hosts.read_text(encoding="utf-8", errors="replace")
            m = re.search(r"oauth_token:\s*([A-Za-z0-9_]+)", text)
            if m:
                return m.group(1).strip()
        except OSError:
            pass
    return None


# ---------------------------------------------------------------------------
# Backend: scrape github.com/trending
# ---------------------------------------------------------------------------


def _parse_int(text: str) -> int:
    """Parse "1,234" or "1.2k" into an integer (best-effort)."""
    if not text:
        return 0
    t = text.strip().replace(",", "").lower()
    if not t:
        return 0
    m = re.match(r"^([\d.]+)\s*([km]?)$", t)
    if not m:
        return 0
    n = float(m.group(1))
    suf = m.group(2)
    if suf == "k":
        n *= 1_000
    elif suf == "m":
        n *= 1_000_000
    return int(n)


def scrape_trending(language: str, since: str, limit: int) -> list[TrendingRepo]:
    """
    Scrape https://github.com/trending/<lang>?since=<period>.

    Returns at most ``limit`` repos. Empty list (not exception) on structural failure.
    """
    if not _HAS_BS4:
        raise RuntimeError("beautifulsoup4 is required for the scrape backend")

    since = (since or "daily").lower()
    if since not in {"daily", "weekly", "monthly"}:
        raise ValueError(f"since must be one of daily/weekly/monthly, got {since!r}")

    # Trending URL: /trending for all, /trending/python for a language
    parts = ["https://github.com/trending"]
    if language and language.lower() not in {"all", "*", ""}:
        parts.append(urllib.parse.quote(language, safe=""))
    url = "/".join(parts) + (f"?since={since}" if since else "")

    raw = _http_get(url)
    soup = BeautifulSoup(raw, "html.parser")
    articles = soup.find_all("article", class_="Box-row")
    if not articles:
        # Fallback selector in case GitHub changes the class name
        articles = soup.find_all("article")
        if not articles:
            return []

    period_label = {"daily": "today", "weekly": "this week", "monthly": "this month"}[since]
    repos: list[TrendingRepo] = []

    for i, art in enumerate(articles[:limit], start=1):
        try:
            # Title / URL
            h2 = art.find("h2")
            h2_link = h2.find("a") if h2 else None
            if not h2_link or not h2_link.get("href"):
                continue
            href = h2_link["href"].strip()
            full_name = href.lstrip("/")
            url_full = "https://github.com" + href if href.startswith("/") else href

            # Description
            desc_tag = art.find("p", class_=re.compile(r"col-9"))
            description = desc_tag.get_text(" ", strip=True) if desc_tag else ""

            # Language
            lang_tag = art.find(attrs={"itemprop": "programmingLanguage"})
            language_name = lang_tag.get_text(strip=True) if lang_tag else ""

            # Total stars
            stars_link = art.find("a", href=re.compile(r"/stargazers$"))
            stars_total = _parse_int(stars_link.get_text(strip=True)) if stars_link else 0

            # Forks
            forks_link = art.find("a", href=re.compile(r"/forks$"))
            forks = _parse_int(forks_link.get_text(strip=True)) if forks_link else 0

            # Period stars ("1,234 stars today")
            # Find the span that contains "stars today" (or week / month)
            text = art.get_text("\n")
            stars_period = 0
            m = re.search(
                r"([\d,\.]+)\s+stars?\s+(today|this week|this month)",
                text,
                re.IGNORECASE,
            )
            if m:
                stars_period = _parse_int(m.group(1))

            repos.append(
                TrendingRepo(
                    rank=i,
                    full_name=full_name,
                    url=url_full,
                    description=description,
                    language=language_name,
                    stars_total=stars_total,
                    stars_period=stars_period,
                    period=period_label,
                    forks=forks,
                )
            )
        except Exception as e:  # noqa: BLE001
            # One bad row shouldn't kill the whole batch
            print(f"[warn] row {i} parse failed: {e}", file=sys.stderr)
            continue

    return repos


# ---------------------------------------------------------------------------
# Backend: GitHub REST search API
# ---------------------------------------------------------------------------


def api_search_recent(
    language: str,
    since: str,
    limit: int,
    token: Optional[str],
) -> list[TrendingRepo]:
    """
    Use the GitHub Search API to find repos created in the last 7 days and
    sort by stars. This is NOT the official trending list (which is
    velocity-based) but it gives a stable, structured snapshot for
    discovery / monitoring purposes.
    """
    days = {"daily": 1, "weekly": 7, "monthly": 30}.get(since, 7)
    cutoff = (datetime.now(timezone.utc) - timedelta(days=days)).strftime("%Y-%m-%d")
    q_parts = [f"created:>{cutoff}"]
    if language and language.lower() not in {"all", "*", ""}:
        q_parts.append(f"language:{language}")
    # Star buckets help avoid paginating through long tail of empty repos
    q_parts.append("stars:>10")
    query = " ".join(q_parts)

    per_page = min(100, max(1, limit))
    repos: list[TrendingRepo] = []
    page = 1

    while len(repos) < limit:
        params = {
            "q": query,
            "sort": "stars",
            "order": "desc",
            "per_page": per_page,
            "page": page,
        }
        url = "https://api.github.com/search/repositories?" + urllib.parse.urlencode(params)
        headers = {"Accept": "application/vnd.github+json"}
        if token:
            headers["Authorization"] = f"Bearer {token}"

        try:
            raw = _http_get(url, headers=headers)
        except urllib.error.HTTPError as e:
            if e.code == 403:
                # Rate limit hit
                print("[error] GitHub API rate limit reached. Use --backend scrape "
                      "or set GH_TOKEN.", file=sys.stderr)
                break
            if e.code == 422:
                # Most often means: query invalid (e.g. unsupported combination)
                print(f"[error] GitHub API 422: bad query '{query}'", file=sys.stderr)
                break
            print(f"[error] GitHub API HTTP {e.code}", file=sys.stderr)
            break

        try:
            payload = json.loads(raw)
        except json.JSONDecodeError:
            print("[error] GitHub API returned non-JSON", file=sys.stderr)
            break

        items = payload.get("items") or []
        if not items:
            break

        for it in items:
            repos.append(
                TrendingRepo(
                    rank=len(repos) + 1,
                    full_name=it.get("full_name", ""),
                    url=it.get("html_url", ""),
                    description=(it.get("description") or "").strip(),
                    language=(it.get("language") or "").strip(),
                    stars_total=int(it.get("stargazers_count") or 0),
                    stars_period=int(it.get("stargazers_count") or 0),
                    period=since,
                    forks=int(it.get("forks_count") or 0),
                    contributors=0,
                    primary_topic=(it.get("topics") or [""])[0],
                )
            )
            if len(repos) >= limit:
                break

        if len(items) < per_page:
            break
        page += 1
        # Be polite to the API
        time.sleep(0.4)

    return repos


# ---------------------------------------------------------------------------
# Markdown rendering
# ---------------------------------------------------------------------------


def render_markdown(repos: list[TrendingRepo], language: str, since: str, backend: str) -> str:
    """Render a list of repos as a Markdown table with a header section."""
    now = datetime.now(timezone.utc).strftime("%Y-%m-%d %H:%M UTC")
    lang_label = language if language and language.lower() not in {"all", "*", ""} else "all languages"
    period_label = {"daily": "today", "weekly": "this week", "monthly": "this month"}.get(since, since)

    lines: list[str] = []
    lines.append("# GitHub Trending Repositories")
    lines.append("")
    lines.append(f"- **Generated**: {now}")
    lines.append(f"- **Backend**: `{backend}`")
    lines.append(f"- **Language**: {lang_label}")
    lines.append(f"- **Period**: {period_label}")
    lines.append(f"- **Count**: {len(repos)}")
    lines.append("")
    if backend == "scrape":
        lines.append("Stars shown: `total` over the lifetime of the repo, "
                     "`+period` accumulated in the chosen window.")
    else:
        lines.append("Stars shown: total stars accumulated since the repo "
                     "was created in the chosen window.")
    lines.append("")
    lines.append("| # | Repository | Description | Language | ⭐ Stars | ⬆ Period |")
    lines.append("|---:|:---|:---|:---|---:|---:|")
    for r in repos:
        lines.append(r.to_markdown_row())
    lines.append("")
    return "\n".join(lines)


# ---------------------------------------------------------------------------
# CLI
# ---------------------------------------------------------------------------


def _parse_args(argv: list[str]) -> argparse.Namespace:
    p = argparse.ArgumentParser(
        description="Fetch GitHub trending repositories and render as Markdown.",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog=__doc__,
    )
    p.add_argument(
        "--language", "-l",
        default="",
        help="programming language filter (e.g. python, rust, go). Default: all",
    )
    p.add_argument(
        "--since", "-s",
        default="daily",
        choices=["daily", "weekly", "monthly"],
        help="time window (default: daily)",
    )
    p.add_argument(
        "--limit", "-n",
        type=int,
        default=DEFAULT_LIMIT,
        help=f"max number of repos to return (default: {DEFAULT_LIMIT}, max: {MAX_LIMIT})",
    )
    p.add_argument(
        "--backend", "-b",
        default="scrape",
        choices=["scrape", "api"],
        help="data source: 'scrape' (real github.com/trending) or 'api' (search API, default: scrape)",
    )
    p.add_argument(
        "--backend-fallback",
        action="store_true",
        help="if the chosen backend fails, automatically try the other one",
    )
    p.add_argument(
        "--output", "-o",
        default="",
        help="write Markdown to this file instead of stdout",
    )
    p.add_argument(
        "--json",
        action="store_true",
        help="also write raw JSON to <output>.json (only with --output)",
    )
    p.add_argument(
        "--quiet", "-q",
        action="store_true",
        help="suppress status messages on stderr",
    )
    return p.parse_args(argv)


def main(argv: list[str]) -> int:
    args = _parse_args(argv)
    if args.limit < 1 or args.limit > MAX_LIMIT:
        print(f"[error] --limit must be in [1, {MAX_LIMIT}]", file=sys.stderr)
        return 2

    if not args.quiet:
        print(f"[info] fetching {args.limit} trending repos "
              f"(language={args.language!r}, since={args.since}, backend={args.backend})",
              file=sys.stderr)

    repos: list[TrendingRepo] = []
    used_backend = args.backend

    try:
        if args.backend == "scrape":
            repos = scrape_trending(args.language, args.since, args.limit)
            if not repos and args.backend_fallback:
                if not args.quiet:
                    print("[warn] scrape returned 0 rows, falling back to api", file=sys.stderr)
                used_backend = "api"
                repos = api_search_recent(
                    args.language, args.since, args.limit, _load_github_token()
                )
        else:
            repos = api_search_recent(
                args.language, args.since, args.limit, _load_github_token()
            )
            if not repos and args.backend_fallback:
                if not args.quiet:
                    print("[warn] api returned 0 rows, falling back to scrape", file=sys.stderr)
                used_backend = "scrape"
                repos = scrape_trending(args.language, args.since, args.limit)
    except NotImplementedError as e:
        print(f"[error] {e}", file=sys.stderr)
        return 2
    except Exception as e:  # noqa: BLE001
        print(f"[error] fetch failed: {type(e).__name__}: {e}", file=sys.stderr)
        return 2

    if not repos:
        print("[error] no repos fetched", file=sys.stderr)
        return 2

    markdown = render_markdown(repos, args.language, args.since, used_backend)

    if args.output:
        out_path = Path(args.output)
        out_path.parent.mkdir(parents=True, exist_ok=True)
        out_path.write_text(markdown, encoding="utf-8")
        if not args.quiet:
            print(f"[info] wrote {len(repos)} repos to {out_path}", file=sys.stderr)
        if args.json:
            json_path = out_path.with_suffix(out_path.suffix + ".json")
            json_path.write_text(
                json.dumps([asdict(r) for r in repos], indent=2, ensure_ascii=False),
                encoding="utf-8",
            )
            if not args.quiet:
                print(f"[info] wrote JSON to {json_path}", file=sys.stderr)
    else:
        sys.stdout.write(markdown)

    # exit code: 1 if we got fewer than half the requested limit
    return 1 if len(repos) < max(1, args.limit // 2) else 0


if __name__ == "__main__":
    raise SystemExit(main(sys.argv[1:]))
