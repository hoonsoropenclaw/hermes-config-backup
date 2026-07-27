# GitHub Trending Repositories 自動抓取腳本

無外部資料源依賴（純 HTML scraping），抓 `https://github.com/trending`，輸出 **markdown 表格** 或 **JSON**。

## 安裝

已內建在 N100，Python 3.12 + `requests` + `beautifulsoup4`。
無其他依賴。

## 用法

```bash
cd ~/.hermes/scripts/github-trending

# 1. 預設：daily + 所有語言 + markdown → stdout
python3 fetch_trending.py

# 2. weekly python，輸出檔
python3 fetch_trending.py --since weekly --language python \
    --output /tmp/trending-week-py.md

# 3. 抓中文說明的 trending（GitHub 支援 spoken_language_code=en/zh/ja/...）
python3 fetch_trending.py --since weekly --spoken-language zh

# 4. 限制筆數 + JSON 格式
python3 fetch_trending.py --since daily --format json --limit 10 \
    --output /tmp/trending.json

# 5. 順便歸檔（按 YYYY-MM/ 切目錄）
python3 fetch_trending.py --since monthly --archive-dir /home/hoonsoropenclaw/permanent-projects/learning/archive/github-trending

# 6. 全部參數
python3 fetch_trending.py --help
```

## 參數

| 旗標 | 預設 | 說明 |
|------|------|------|
| `--since` | `daily` | `daily` / `weekly` / `monthly` |
| `--language` | `all` | 主語言（`python`、`typescript`、`go`、`rust`、`c++` 等） |
| `--spoken-language` | unset | 描述語言（`en`、`zh`、`ja`） |
| `--limit` | `25` | 最多保留幾筆 |
| `--format` | `markdown` | `markdown` / `json` |
| `--output` | `-` (stdout) | 寫入檔案的路徑；`-` 表 stdout |
| `--archive-dir` | unset | 額外歸檔到 `<archive-dir>/YYYY-MM/github-trending-YYYY-MM-DD.{md,json}` |

## 輸出格式範例

```markdown
| # | Repo | Language | ⭐ Total | 🍴 Forks | 🔥 Today | Description |
|---|------|----------|---------|---------|---------|-------------|
| 1 | [permissionlesstech/bitchat](https://github.com/permissionlesstech/bitchat) | Swift | 30,876 | 4,827 | 1,166 | bluetooth mesh chat, IRC vibes |
```

JSON 結構（每筆 repo）：

```json
{
  "rank": 1,
  "full_name": "owner/repo",
  "repo_url": "https://github.com/owner/repo",
  "description": "...",
  "language": "Python",
  "total_stars": "30,876",
  "forks": "4,827",
  "stars_today": "1,166 stars today",
  "contributor_avatars": ["https://avatars.githubusercontent.com/u/..."],
  "built_by": ["handle1", "handle2"]
}
```

## 測試

不需要網路（用 `fixtures/` 內存好的 HTML）：

```bash
cd ~/.hermes/scripts/github-trending
python3 test_fetch_trending.py
```

```
[OK] daily 解析 17 筆
[OK] python weekly 解析 20 筆，languages={'Python'}
[OK] markdown format (461 bytes)
[OK] json format roundtrip (259 bytes)
[OK] limit 切 3 筆後剩 3 筆
[OK] built_by 乾淨（共 81 筆 handle）

ALL TESTS PASSED
```

## 如何更新 fixture（GitHub 改版時）

```bash
cd ~/.hermes/scripts/github-trending
curl -sS -A "Mozilla/5.0" https://github.com/trending > fixtures/trending_daily.html
curl -sS -A "Mozilla/5.0" "https://github.com/trending/python?since=weekly" > fixtures/trending_python_weekly.html
python3 test_fetch_trending.py
```

## GitHub DOM 改版時怎麼除錯

跑：

```bash
python3 fetch_trending.py 2>&1
```

如果抓到空清單（表格只有 `(no repos fetched)`），進入 python REPL：

```python
from fetch_trending import parse_trending_html
html = open('/tmp/debug.html').read()
repos = parse_trending_html(html)
print(repos)
```

常見卡點：
1. `article.Box-row` 改 class → 改 `_parse_legacy_fallback` 之前的 selector
2. 星數 class 改了 → 改 `find("a", href=lambda h: h.endswith("/stargazers"))`
3. 今日 stars 改了位置 → 改 `find("span", class_=re.compile(r"d-inline-block\s+float-sm-right"))`

## 對應 trial-and-error 紀錄

- **python-sandbox.md** 第 13 行：寫檔案一律用 `Path.write_bytes(...)`、不要用 hermes `read_file()/write_file()` round-trip（會帶行號污染）。本腳本全程用前者。
- **hermes-internal.md** `read_file / write_file` 副作用：`read_file` 是給 agent 看的顯示工具，內容可能帶行號前綴（`1|...`、`2|...`），不要把它當 raw bytes round-trip。
