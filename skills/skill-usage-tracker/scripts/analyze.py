#!/usr/bin/env python3
"""
skill-usage-tracker analyze.py
讀取 ~/.hermes/skill-usage/*.jsonl,統計每個 skill 的平均評分。
支援口語回饋 auto-parse（Weak Reward）：comment 欄位自動轉為 combo_rating。

用法:
    python3 ~/.hermes/skills/skill-usage-tracker/scripts/analyze.py [--min-ratings N]
"""
import json
import sys
from pathlib import Path
from collections import defaultdict
from datetime import datetime

LOG_DIR = Path.home() / ".hermes" / "skill-usage"

# Weak-reward keyword sets for auto-parsing
POSITIVE_STRONG = {"超讚", "太棒了", "完美", "非常滿意", "棒", "優"}
POSITIVE_WEAK = {"好", "可以", "讚", "不錯", "ok", "okay"}
NEGATIVE_WEAK = {"不行", "不好", "爛", "失望", "太慢", "普通", "還好"}
NEGATIVE_STRONG = {"爛透了", "浪費時間", "完全不行", "垃圾"}


def parse_weak_reward(entry):
    """從 comment 欄位自動推斷 combo_rating（當 combo_rating 為 null 時）。

    規則（按優先順序）：
    1. entry.combo_rating 已有值 → 直接返回，不覆寫
    2. comment 為空 → 返回 None（無法推斷）
    3. 強烈正面關鍵字（超讚/太棒了/完美）→ 5
    4. 弱正面關鍵字 → 4
    5. 強烈負面關鍵字 → 1
    6. 弱負面關鍵字 → 2
    7. 中性地帶（普通/還好）→ 3
    8. 無關鍵字 → 返回 None
    """
    if entry.get("combo_rating") is not None:
        return None  # 已有人工評分，不覆寫

    comment = (entry.get("comment") or "").strip()
    if not comment:
        return None

    # 強烈正面優先
    for kw in POSITIVE_STRONG:
        if kw in comment:
            return 5
    for kw in POSITIVE_WEAK:
        if kw in comment:
            return 4
    for kw in NEGATIVE_STRONG:
        if kw in comment:
            return 1
    for kw in NEGATIVE_WEAK:
        if kw in comment:
            return 2
    return None


def load_entries():
    if not LOG_DIR.exists():
        return []
    entries = []
    for f in sorted(LOG_DIR.glob("*.jsonl")):
        with open(f) as fp:
            for line in fp:
                line = line.strip()
                if not line:
                    continue
                try:
                    entry = json.loads(line)
                    # Auto-parse weak reward into combo_rating
                    inferred = parse_weak_reward(entry)
                    if inferred is not None and entry.get("combo_rating") is None:
                        entry["combo_rating"] = inferred
                        entry["_weak_reward_inferred"] = True
                    entries.append(entry)
                except json.JSONDecodeError as e:
                    print(f"⚠️  {f.name}: parse error: {e}", file=sys.stderr)
    return entries


def analyze(entries, min_ratings=3):
    """分析每個 skill 的平均 rating。"""
    skill_ratings = defaultdict(list)   # skill_name -> [ratings]
    combo_ratings = []
    total_tasks = 0
    weak_inferred = 0

    for e in entries:
        total_tasks += 1
        if e.get("_weak_reward_inferred"):
            weak_inferred += 1
        if e.get("combo_rating") is not None:
            combo_ratings.append(e["combo_rating"])
        for skill, rating in (e.get("individual_ratings") or {}).items():
            skill_ratings[skill].append(rating)

    print(f"\n📊 Skill Usage Tracker 分析報告")
    print(f"=" * 60)
    print(f"分析時間: {datetime.now().isoformat(timespec='seconds')}")
    print(f"資料來源: {LOG_DIR}")
    print(f"累積任務數: {total_tasks}")
    print(f"組合評分樣本數: {len(combo_ratings)}")
    if weak_inferred:
        print(f"  (含 {weak_inferred} 筆自動推斷自 comment 欄位)")
    print(f"個別 skill 評分總筆數: {sum(len(v) for v in skill_ratings.values())}")
    print(f"被評分過的 skill 數: {len(skill_ratings)}")
    print()

    if combo_ratings:
        avg_combo = sum(combo_ratings) / len(combo_ratings)
        print(f"⭐ 整體組合平均評分: {avg_combo:.2f} / 5.0")
        print(f"   樣本: {combo_ratings}")
        print()

    # 個別 skill 排名
    skill_stats = []
    for skill, ratings in skill_ratings.items():
        if len(ratings) < min_ratings:
            continue
        avg = sum(ratings) / len(ratings)
        skill_stats.append((skill, avg, len(ratings), ratings))

    if not skill_stats:
        print(f"⚠️  沒有任何 skill 累積到 ≥ {min_ratings} 個評分。")
        print(f"    目前評分過的 skill:")
        for skill, ratings in sorted(skill_ratings.items(), key=lambda x: -len(x[1])):
            print(f"      - {skill}: {len(ratings)} 個評分(平均 {sum(ratings)/len(ratings):.2f})")
        # SOP-C (2026-06-21): 強制產出——若 0 筆 combo_rating，說明從未執行交付後 SOP
        if not combo_ratings:
            print()
            print("⚠️  [SOP-C ALERT] 0 筆 combo_rating！")
            print("    這代表從未在任務完成後邀請評分。")
            print("    立即執行：python3 ~/.hermes/skills/skill-usage-tracker/scripts/post_delivery.py --session <session_id> --write")
        return

    skill_stats.sort(key=lambda x: -x[1])

    print(f"🏆 個別 skill 排名(需 ≥ {min_ratings} 個評分):")
    print(f"-" * 60)
    for skill, avg, n, ratings in skill_stats:
        emoji = "🥇" if avg >= 4.5 else "🥈" if avg >= 4.0 else "🥉" if avg >= 3.5 else "⚠️ " if avg >= 3.0 else "❌"
        print(f"  {emoji} {skill:35s}  {avg:.2f} / 5.0  (n={n}, ratings={ratings})")
    print()

    # 偏好清單(三類)
    high = [s for s in skill_stats if s[1] >= 4.0]
    mid = [s for s in skill_stats if 3.0 <= s[1] < 4.0]
    low = [s for s in skill_stats if s[1] < 3.0]

    print(f"📋 hoonsoropenclaw 偏好清單:")
    print(f"-" * 60)
    print(f"  ✅ 偏好(平均 ≥ 4.0,未來預設載入):")
    for s, avg, n, _ in high:
        print(f"     - {s} ({avg:.2f}, n={n})")
    print(f"  ⚖️  中性(3.0-4.0,視任務決定):")
    for s, avg, n, _ in mid:
        print(f"     - {s} ({avg:.2f}, n={n})")
    print(f"  ❌ 不偏好(< 3.0,預設不載入):")
    for s, avg, n, _ in low:
        print(f"     - {s} ({avg:.2f}, n={n})")
    print()

    # 最近 5 筆任務的 rating trend
    if len(entries) >= 5:
        print(f"📈 最近 5 筆任務評分趨勢:")
        print(f"-" * 60)
        for e in entries[-5:]:
            ts = e.get("ts", "?")[:16]
            task = (e.get("task_summary") or e.get("task") or "")[:30]
            cr = e.get("combo_rating", "?")
            inferred = "🔁" if e.get("_weak_reward_inferred") else "  "
            result = e.get("result", "?")
            print(f"  {inferred}[{ts}] {task:30s}  組合:{cr}  結果:{result}")
        print()


def main():
    min_ratings = 3
    if "--min-ratings" in sys.argv:
        idx = sys.argv.index("--min-ratings")
        min_ratings = int(sys.argv[idx + 1])

    entries = load_entries()
    if not entries:
        print("⚠️  還沒有任何 skill-usage log 紀錄。")
        print(f"    預期位置: {LOG_DIR}")
        return

    analyze(entries, min_ratings=min_ratings)


if __name__ == "__main__":
    main()
