#!/usr/bin/env python3
"""
OpenClaw Session Cleanup Utility
清理 sessions.json 中的 subagent/cron:run child sessions，保留 main/dashboard/channel sessions
"""

import json
import argparse
from pathlib import Path

SESSIONS_FILE = Path.home() / ".openclaw" / "agents" / "main" / "sessions" / "sessions.json"

# 保留規則：這些 key patterns 會被保留
KEEP_PATTERNS = [
    "agent:main:main",
    "agent:main:dashboard",
    "agent:main:explicit",
]

# 刪除規則：這些 key patterns 會被刪除
DELETE_PATTERNS = [
    "subagent",
    "cron:run",
]

def load_sessions():
    with open(SESSIONS_FILE, 'r') as f:
        return json.load(f)

def should_keep(key: str) -> bool:
    """判斷是否應該保留這個 session"""
    # 嚴格保留的 patterns
    for pattern in KEEP_PATTERNS:
        if pattern in key:
            return True
    # 刪除的 patterns
    for pattern in DELETE_PATTERNS:
        if pattern in key:
            return False
    return True

def analyze_sessions(store):
    """分析 session 分布"""
    stats = {
        'total': len(store),
        'keep': 0,
        'delete': 0,
        'by_type': {}
    }
    
    for key in store.keys():
        # 分類
        if 'subagent' in key:
            sess_type = 'subagent'
        elif 'cron:run' in key:
            sess_type = 'cron:run'
        elif 'cron:' in key:
            sess_type = 'cron:definition'
        elif 'telegram' in key:
            sess_type = 'telegram'
        elif 'dashboard' in key:
            sess_type = 'dashboard'
        elif 'main' in key:
            sess_type = 'main'
        else:
            sess_type = 'other'
        
        stats['by_type'][sess_type] = stats['by_type'].get(sess_type, 0) + 1
        
        if should_keep(key):
            stats['keep'] += 1
        else:
            stats['delete'] += 1
    
    return stats

def cleanup_sessions(dry_run=True, keep_jsonl=False):
    """清理 sessions.json"""
    store = load_sessions()
    stats = analyze_sessions(store)
    
    print(f"分析結果:")
    print(f"  總 sessions: {stats['total']}")
    print(f"  保留: {stats['keep']}")
    print(f"  刪除: {stats['delete']}")
    print(f"\n分類統計:")
    for t, c in sorted(stats['by_type'].items(), key=lambda x: -x[1]):
        print(f"  {t}: {c}")
    
    if dry_run:
        print(f"\n[DRY RUN] 未實際刪除任何 sessions")
        return
    
    # 實際刪除
    new_store = {k: v for k, v in store.items() if should_keep(k)}
    
    # 備份
    backup_path = SESSIONS_FILE.with_suffix('.json.backup')
    import shutil
    shutil.copy(SESSIONS_FILE, backup_path)
    print(f"\n已備份到: {backup_path}")
    
    # 寫入新檔案
    with open(SESSIONS_FILE, 'w') as f:
        json.dump(new_store, f, indent=2)
    
    print(f"已刪除 {len(store) - len(new_store)} 個 sessions")
    print(f"剩餘: {len(new_store)} 個 sessions")
    
    # 清理 .jsonl 檔案（可選）
    if keep_jsonl:
        print("\n保留所有 .jsonl 檔案")
    else:
        print("\n注意：如需清理 .jsonl 檔案，需手動處理")

def main():
    parser = argparse.ArgumentParser(description='OpenClaw Session Cleanup')
    parser.add_argument('--dry-run', action='store_true', help='預覽模式，不實際刪除')
    parser.add_argument('--keep-jsonl', action='store_true', help='保留 .jsonl 檔案')
    parser.add_argument('--execute', action='store_true', help='實際執行清理')
    
    args = parser.parse_args()
    
    if args.execute:
        cleanup_sessions(dry_run=False, keep_jsonl=args.keep_jsonl)
    else:
        cleanup_sessions(dry_run=True, keep_jsonl=args.keep_jsonl)

if __name__ == '__main__':
    main()