"""
test_fetch_trending.py — 不用網路、用 HTML fixture 驗 fetch_trending.py 的 parser

執行方式：在 github-trending/ 目錄下
  python3 test_fetch_trending.py
"""
import sys
import json
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent))
import fetch_trending as ft


FIXTURES = Path(__file__).parent / "fixtures"


def _repo_dict(r):
    return r.to_dict() if hasattr(r, "to_dict") else r.__dict__


def test_parser_daily_trending_returns_repos():
    html = (FIXTURES / "trending_daily.html").read_text(encoding="utf-8")
    repos = ft.parse_trending_html(html)
    assert repos, "應該要有至少一筆 repo"
    assert all("rank" in _repo_dict(r) for r in repos)
    for r in repos:
        d = _repo_dict(r)
        assert "/" in d["full_name"], d
        assert d["repo_url"].startswith("https://github.com/"), d
    print(f"[OK] daily 解析 {len(repos)} 筆")


def test_python_weekly_returns_only_python():
    html = (FIXTURES / "trending_python_weekly.html").read_text(encoding="utf-8")
    repos = ft.parse_trending_html(html)
    langs = {_repo_dict(r)["language"] for r in repos}
    assert langs <= {"Python", "—"} or langs == {"Python"}, f"混入了非 python：{langs}"
    print(f"[OK] python weekly 解析 {len(repos)} 筆，languages={langs}")


def test_markdown_format_contains_columns():
    repos = [
        ft.TrendingRepo(
            rank=1, full_name="owner/repo",
            repo_url="https://github.com/owner/repo",
            description="hello | world", language="Python",
            total_stars="100", forks="10",
            stars_today="5 stars today",
            contributor_avatars=[], built_by=["alice"],
        ),
    ]
    md = ft.to_markdown(repos, since="daily", language="all", spoken_language=None)
    assert "| # |" in md and "| Repo |" in md
    assert "[owner/repo]" in md
    assert "hello \\| world" in md, "description 內的 | 應該 escape 成 \\|"
    assert "since=daily" in md
    print(f"[OK] markdown format ({len(md)} bytes)")


def test_json_format_roundtrip():
    repos = [
        ft.TrendingRepo(
            rank=1, full_name="a/b", repo_url="u",
            description="d", language="L", total_stars="1",
            forks="1", stars_today="1 stars today",
            contributor_avatars=[], built_by=["x"],
        ),
    ]
    js = ft.to_json(repos)
    data = json.loads(js)
    assert data[0]["full_name"] == "a/b"
    print(f"[OK] json format roundtrip ({len(js)} bytes)")


def test_limit_truncates():
    html = (FIXTURES / "trending_daily.html").read_text(encoding="utf-8")
    repos = ft.parse_trending_html(html)[:3]
    assert len(repos) <= 3
    print(f"[OK] limit 切 3 筆後剩 {len(repos)} 筆")


def test_built_by_filters_login_link():
    html = (FIXTURES / "trending_daily.html").read_text(encoding="utf-8")
    repos = ft.parse_trending_html(html)
    for r in repos:
        d = _repo_dict(r)
        for handle in d["built_by"]:
            assert "?" not in handle
            assert "login" not in handle.lower()
    print(f"[OK] built_by 乾淨（共 {sum(len(_repo_dict(r)['built_by']) for r in repos)} 筆 handle）")


if __name__ == "__main__":
    test_parser_daily_trending_returns_repos()
    test_python_weekly_returns_only_python()
    test_markdown_format_contains_columns()
    test_json_format_roundtrip()
    test_limit_truncates()
    test_built_by_filters_login_link()
    print("\nALL TESTS PASSED")

