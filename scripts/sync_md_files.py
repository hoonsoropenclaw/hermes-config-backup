#!/usr/bin/env python3
"""
sync_md_files.py
每天自動把本機的七大核心 MD 檔案內容同步到 hermes-status-site

輸出：
  assets/md-files.json  — 卡片資料（JSON，sync script 寫入）
  tabs/md-files.html    — 純 HTML 結構（不動）
  css/md-files.css      — 樣式（不動）
  js/md-files.js        — 邏輯（不動）

用法：
  python3 sync_md_files.py              # 更新並部署
  python3 sync_md_files.py --local-only  # 只更新本機，不部署
"""

import os, json, re, sys
from pathlib import Path

# 設定
HERMES_BASE = Path.home() / ".hermes"
MEMORIES_DIR = HERMES_BASE / "memories"
STATUS_SITE = Path("/home/hoonsoropenclaw/hermes-status-site")
JSON_FILE = STATUS_SITE / "assets" / "md-files.json"

# 七大核心 MD 檔案
CORE_FILES = [
    "SOUL.md", "USER.md", "HEARTBEAT.md", "AGENTS.md",
    "IDENTITY.md", "TOOLS.md", "MEMORY.md",
]

# Pre-write secret scan: never let these patterns into the public GitHub repo
# (2026-06-06 added after GH013 incident with sync of MEMORY.md to assets/md-files.json)
SECRET_PATTERNS = [
    (re.compile(r"vcp_[A-Za-z0-9]{20,}"), "Vercel Token"),
    (re.compile(r"ghp_[A-Za-z0-9]{36}"), "GitHub PAT"),
    (re.compile(r"sk-[A-Za-z0-9]{40,}"), "OpenAI/Anthropic API Key"),
    (re.compile(r"hms_[A-Za-z0-9_]{20,}"), "Hermes Portal API Key"),
    (re.compile(r"gho_[A-Za-z0-9]{36}"), "GitHub OAuth"),
    (re.compile(r"glpat-[A-Za-z0-9_-]{20,}"), "GitLab Token"),
]


def scan_for_secrets(text: str, source: str) -> list[str]:
    """Return list of detected secret names; empty list = clean."""
    hits = []
    for pat, name in SECRET_PATTERNS:
        if pat.search(text):
            hits.append(f"{name} (pattern: {pat.pattern})")
    return hits


def scrub_secrets(text: str) -> str:
    """Replace matched secrets with a redacted placeholder."""
    for pat, name in SECRET_PATTERNS:
        text = pat.sub(f"[{name} REDACTED]", text)
    return text


def read_md_content(filepath: Path) -> tuple[str, str]:
    """讀取檔案內容，回傳 (content, modified_time)"""
    if filepath.exists():
        content = filepath.read_text(encoding="utf-8")
        mtime = str(int(os.path.getmtime(filepath)))
        return content, mtime
    return "", ""


def content_preview(content: str, max_len=120) -> str:
    """產生內容預覽（第一行或前 max_len 字）"""
    lines = [l for l in content.splitlines() if l.strip()]
    if not lines:
        return "（空檔案）"
    first = lines[0].strip()
    if len(first) > max_len:
        return first[:max_len] + "…"
    return first


def sync():
    """把七大 MD 檔案寫入 assets/md-files.json（會先 scrub secrets）"""
    files_data = []
    for fname in CORE_FILES:
        fpath = MEMORIES_DIR / fname
        content, mtime = read_md_content(fpath)

        # Pre-write secret scan (2026-06-06 GH013 fix)
        hits = scan_for_secrets(content, fname)
        if hits:
            print(f"[SECRET-LEAK] {fname}: {hits}")
            print("[SECRET-LEAK] Auto-scrubbing before write.")
            content = scrub_secrets(content)

        files_data.append({
            "name": fname,
            "content": content,
            "mtime": mtime,
            "preview": content_preview(content),
        })

    JSON_FILE.parent.mkdir(parents=True, exist_ok=True)
    JSON_FILE.write_text(
        json.dumps(files_data, ensure_ascii=False, indent=2),
        encoding="utf-8"
    )
    print(f"[OK] Wrote {len(files_data)} files to {JSON_FILE}")
    return files_data


def deploy():
    """部署 hermes-status-site 到 Vercel"""
    # 2026-06-06: removed hardcoded token fallback — force caller to provide via env.
    # The default previously was a real (now-revoked) Vercel token, which would have
    # been a leak risk if the env var were ever missing.
    token = os.environ.get("VERCEL_TOKEN") or os.environ.get("VERCEL_API_TOKEN")
    if not token:
        print("[DEPLOY] ERROR: VERCEL_TOKEN/VERCEL_API_TOKEN not set in environment.")
        return False
    import subprocess
    result = subprocess.run(
        ["vercel", "--token", token, "--prod", "--yes"],
        cwd=str(STATUS_SITE),
        capture_output=True, text=True, timeout=120
    )
    print(f"[DEPLOY] stdout: {result.stdout[-500:]}")
    if result.returncode != 0:
        print(f"[DEPLOY] stderr: {result.stderr[-300:]}")
    return result.returncode == 0


def main(local_only=False):
    print("=== hermes-status-site MD files sync ===")
    print(f"Memories dir: {MEMORIES_DIR}")
    print(f"Output file: {JSON_FILE}")

    if not MEMORIES_DIR.exists():
        print(f"[ERROR] {MEMORIES_DIR} not found!")
        return 1

    files_data = sync()

    # 驗證
    with open(JSON_FILE, encoding="utf-8") as f:
        loaded = json.load(f)
    print(f"[OK] {len(loaded)} files in JSON, first: {loaded[0]['name']}")

    if local_only:
        print("[SKIP] Skipping deploy (--local-only)")
        return 0

    print("\nDeploying to Vercel...")
    ok = deploy()
    if ok:
        print("[OK] Deployed successfully")
    else:
        print("[FAIL] Deploy failed")
    return 0 if ok else 1


if __name__ == "__main__":
    import sys
    local_only = "--local-only" in sys.argv
    code = main(local_only)
    sys.exit(code)