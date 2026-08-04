#!/usr/bin/env python3
"""
dryrun_test_template.py — autonomous-agent-loop-design 的標準 9 測試模板

複製此檔到 /tmp/test_<your_spawn_script>_dryrun.py，改 3 個常數即可執行：

  SCRIPT_PATH  = "/path/to/your/spawn_script.py"
  MEM_DIR      = "/path/to/agent_memory/"
  IMPORT_NAME  = "your_spawn_script"   # 對應 SCRIPT_PATH 的 basename

測試項目（不可刪減）：
1.  語法檢查（compile + import）
2.  import 成功 + 主要函式存在
3.  get_topic_hash 穩定性
4.  get_or_create_work_dir 同 topic 回傳同路徑
5.  is_topic_recently_completed 正確判斷
6.  _scan_recent_completed_topics 正確掃描
7.  prompt 內含 memory 讀寫指令
8.  max_limit 預設值正確（驗證設計哲學已改）
9.  「燒 token」規則已被「EFFICIENCY-FIRST」取代
"""
import sys
import os
import shutil
from datetime import datetime, timedelta

# ============================================================
# 改這 3 個常數即可
# ============================================================
SCRIPT_PATH = "/home/hoonsoropenclaw/.hermes/smart_heartbeat.py"
MEM_DIR = "/home/hoonsoropenclaw/.hermes/agent_memory"
IMPORT_NAME = "smart_heartbeat"
# ============================================================


def test_syntax():
    print("\n=== Test 1: 語法檢查 ===")
    with open(SCRIPT_PATH) as f:
        code = f.read()
    try:
        compile(code, SCRIPT_PATH, "exec")
        print("✅ 通過")
        return True
    except SyntaxError as e:
        print(f"❌ 失敗：{e}")
        return False


def test_imports():
    print("\n=== Test 2: import + 函式存在 ===")
    script_dir = os.path.dirname(SCRIPT_PATH)
    sys.path.insert(0, script_dir)
    try:
        mod = __import__(IMPORT_NAME)
        required = [
            "get_topic_hash",
            "get_or_create_work_dir",
            "get_memory_path",
            "is_topic_recently_completed",
            "_scan_recent_completed_topics",
            "get_llm_strategy",
            "trigger_learning",
        ]
        for name in required:
            assert hasattr(mod, name), f"缺少 {name}"
        print(f"✅ 通過（{len(required)} 個函式都存在）")
        return True
    except Exception as e:
        print(f"❌ 失敗：{e}")
        return False


def test_topic_hash_stability():
    print("\n=== Test 3: topic_hash 穩定性 ===")
    mod = sys.modules[IMPORT_NAME]
    t1 = mod.get_topic_hash("使用 Playwright 跨瀏覽器自動化測試")
    t2 = mod.get_topic_hash("使用 Playwright 跨瀏覽器自動化測試")
    t3 = mod.get_topic_hash("使用 Playwright 跨瀏覽器自動化測試並整合視覺回歸")
    assert t1 == t2, "同 topic 應回傳同 hash"
    assert t1 != t3, "不同 topic 應回傳不同 hash"
    assert len(t1) == 12, "hash 應為 12 字"
    print(f"✅ 通過（{t1}，同 topic 穩定、不同 topic 不同）")
    return True


def test_work_dir_persistence():
    print("\n=== Test 4: work_dir 持久性 ===")
    mod = sys.modules[IMPORT_NAME]
    topic = f"dryrun_test_topic_{os.getpid()}"
    wd1 = mod.get_or_create_work_dir(topic)
    wd2 = mod.get_or_create_work_dir(topic)
    wd3 = mod.get_or_create_work_dir(topic, idx=1)
    assert wd1 == wd2, "同 topic 應回傳同路徑"
    assert wd3 != wd1, "idx=1 應加後綴"
    assert wd3.endswith("_1"), f"idx=1 應以 _1 結尾，實際：{wd3}"
    print(f"✅ 通過（{wd1}）")
    shutil.rmtree(wd1, ignore_errors=True)
    shutil.rmtree(wd3, ignore_errors=True)
    return True


def test_memory_round_trip():
    print("\n=== Test 5: memory 寫入 → is_topic_recently_completed 正確判斷 ===")
    mod = sys.modules[IMPORT_NAME]
    topic = "dryrun_test_round_trip"
    hash12 = mod.get_topic_hash(topic)
    mem_path = os.path.join(MEM_DIR, f"{hash12}.md")
    now_str = datetime.now().strftime("%Y-%m-%d %H:%M")
    with open(mem_path, "w", encoding="utf-8") as f:
        f.write(f"# 任務：{topic}\n\n## 完成狀態\n- 最後更新：{now_str}\n- 完成階段：2\n\n## 已完成的子任務\n- test\n")
    try:
        assert mod.is_topic_recently_completed(topic) is True, "剛完成的 topic 應被判為 recently completed"
        print("✅ 通過（寫入完成階段 2 的 memory 後，is_topic_recently_completed 回傳 True）")
        return True
    finally:
        if os.path.exists(mem_path):
            os.remove(mem_path)


def test_scan_recent_completed():
    print("\n=== Test 6: _scan_recent_completed_topics 掃描 ===")
    mod = sys.modules[IMPORT_NAME]
    now = datetime.now()
    for i, (hours_ago, stage) in enumerate([(1, 2), (30, 2)]):
        time_str = (now - timedelta(hours=hours_ago)).strftime("%Y-%m-%d %H:%M")
        mem_path = os.path.join(MEM_DIR, f"_test_scan_{i}.md")
        with open(mem_path, "w", encoding="utf-8") as f:
            f.write(f"# 任務：測試 topic {i}\n\n## 完成狀態\n- 最後更新：{time_str}\n- 完成階段：{stage}\n")
    try:
        completed = mod._scan_recent_completed_topics(hours=24)
        assert any("測試 topic 0" in t for t in completed), "1 小時前的 topic 0 應在清單中"
        assert not any("測試 topic 1" in t for t in completed), "30 小時前的 topic 1 不應在 24h 清單"
        print(f"✅ 通過（{len(completed)} 個 recently completed topics）")
        return True
    finally:
        for i in range(2):
            p = os.path.join(MEM_DIR, f"_test_scan_{i}.md")
            if os.path.exists(p):
                os.remove(p)


def test_prompt_contains_memory_instruction():
    print("\n=== Test 7: prompt 含 memory 指令 ===")
    with open(SCRIPT_PATH, encoding="utf-8") as f:
        code = f.read()
    assert "get_memory_path" in code, "程式碼應引用 get_memory_path"
    occurrences = code.count("get_memory_path(topic)")
    assert occurrences >= 4, f"get_memory_path(topic) 至少 4 次（resume+new 各 2 處），實際 {occurrences}"
    print(f"✅ 通過（get_memory_path(topic) 出現 {occurrences} 次）")
    return True


def test_max_limit_default():
    print("\n=== Test 8: max_limit 預設值 ===")
    with open(SCRIPT_PATH, encoding="utf-8") as f:
        code = f.read()
    # main() 內 max_limit = 2
    assert "max_limit = 2" in code, "max_limit 應為 2"
    assert '"max_running_count": 2' in code, "fallback max_running_count 應為 2"
    print("✅ 通過（max_limit=2, fallback max_running_count=2）")
    return True


def test_burn_token_rule_replaced():
    print("\n=== Test 9: 「燒 token」語氣已改 ===")
    with open(SCRIPT_PATH, encoding="utf-8") as f:
        code = f.read()
    assert "burn tokens" not in code.lower(), "舊的『burn tokens』語氣應已移除"
    assert "EFFICIENCY-FIRST" in code, "新的『EFFICIENCY-FIRST』規則應存在"
    print("✅ 通過（燒 token → EFFICIENCY-FIRST）")
    return True


def main():
    print("=" * 60)
    print(f"{os.path.basename(SCRIPT_PATH)} 改動後 dry-run 測試")
    print("=" * 60)

    tests = [
        test_syntax,
        test_imports,
        test_topic_hash_stability,
        test_work_dir_persistence,
        test_memory_round_trip,
        test_scan_recent_completed,
        test_prompt_contains_memory_instruction,
        test_max_limit_default,
        test_burn_token_rule_replaced,
    ]

    passed = failed = 0
    for t in tests:
        try:
            if t():
                passed += 1
            else:
                failed += 1
        except Exception as e:
            print(f"❌ {t.__name__} 例外：{e}")
            failed += 1

    print(f"\n{'=' * 60}")
    print(f"結果：{passed}/{passed + failed} 通過")
    print("=" * 60)
    return 0 if failed == 0 else 1


if __name__ == "__main__":
    sys.exit(main())
