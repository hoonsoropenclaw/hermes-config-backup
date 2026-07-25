# Hermes Internal Addendum（2026-07-02 補強）

補強 `hermes-internal.md` 的兩個新發現 — 同根因或新行為。

---

## 強化 §10.13：hermes cron `script` 欄位更深陷阱（連 flag 都不吃）

**症狀**：`jobs.json` 寫 `"script": "hermes-backup-v4.sh --brief --tier1"`，cron 跑出 `Script not found: /home/hoonsoropenclaw/.hermes/scripts/hermes-backup-v4.sh --brief --tier1`。

**根因**：hermes cron 的 `script` 欄位是**單一字串、不解析、不切 token**。`_run_job_script()` 直接把整段當路徑接到 `~/.hermes/scripts/` 後面找。所以：
- 絕對路徑（`/home/...`）→ `~/.hermes/scripts//home/...` 找不到
- 相對子目錄（`foo/bar.sh`）→ `~/.hermes/scripts/foo/bar.sh` 找不到
- 含 flags（`script.sh --flag`）→ 整段當檔名 `script.sh --flag` 找不到

**§10.13 原文只說「不支援絕對路徑」→ 不夠**：連同個欄位字串裡的 flag 也算進去、同根因的更深變體。2026-07-02 實測中。

**解法**：用 **wrapper script** 把 flag 組合封進 `~/.hermes/scripts/<wrapper>.sh`，jobs.json 只放純檔名：

```bash
# 範例：把 hermes-backup-v4.sh --brief --tier1 封成 wrapper
cat > ~/.hermes/scripts/hermes-backup-v4-brief-tier1.sh <<'EOF'
#!/usr/bin/env bash
exec /home/hoonsoropenclaw/.hermes/scripts/hermes-backup-v4.sh --brief --tier1
EOF
chmod +x ~/.hermes/scripts/hermes-backup-v4-brief-tier1.sh
# jobs.json: "script": "hermes-backup-v4-brief-tier1.sh"  （純檔名、無 flag）
```

**驗證**：
```bash
hermes cron run <job_name>          # 觸發
sleep 65 && cat $(ls -t ~/.hermes/cron/output/<job_id>/*.md | head -1)
# ✅ 看到 Mode: no_agent (script) + 預期輸出
# ❌ 看到 Script not found: ... → 又是這條 bug
```

**If→Then**：
- **If** 想讓 skill 內的 script 能被 hermes cron 跑 **Then** 必建 symlink 到 `~/.hermes/scripts/`（§10.13 原解）
- **If** cron job 需要傳 flag 給 script **Then** 必建獨立 wrapper script，不要把 flag 塞進 jobs.json `script` 欄位（§10.13 同根因的更深變體，2026-07-02 實測）
- **If** `hermes cron run <name>` 後看到 `Script not found:` **Then** 先看 jobs.json 的 `script` 欄位是不是「純檔名」，有 flag / 路徑就中招

---

## `patch` tool 對中文字串的 unicode normalization（2026-07-02 新發現）

**症狀**：用 `patch` tool 改 `~/.hermes/cron/jobs.json` 內的中文 prompt 欄位：
- OLD（git 備份）：`請照平常 cron 腳本跑、輸出透過 telegram 送達,不要做任何其他事`
- NEW（patch 寫入）：`請照平時 cron 腳本跑、輸出透過 telegram 送達，不要做任何其他事`

差異 2 字：
- `平常` → `平時`
- `,`（半形逗號）→ `，`（全形逗號）

**根因**：`patch` tool 對 old_string / new_string 的中文字串做 unicode normalization（如 NFC → NFD 或全/半形轉換），差異化**人類眼睛看得到、patch 比對時可能視為相同**。patch 工具內部 fuzzy match 容忍了 normalization 差異，但**寫入**時用 normalize 後的字串覆蓋，導致 prompt 內容被悄悄改。

**危險**：
- 中文 prompt / SOUL.md / MEMORY.md / SKILL.md 任何 patch 都可能中
- Diff 紀錄會顯示「這個檔被改了」但 review 不容易看到 1-2 字差異
- 如果 patch 是**無聲污染**（patch 工具報告成功），git log 可能靜默記錄變化

**解法**：
1. **patch 前必備份**（`cp foo.json foo.json.bak`），改後用 `python3` 對**欄位級**比對：
   ```python
   import json
   new = json.load(open('foo.json'))
   old = json.load(open('foo.json.bak'))
   def find(j, name): return [x for x in j['jobs'] if x['name']==name][0]
   for n in ['job1', 'job2']:
       o, n_ = find(old, n), find(new, n)
       print(f'{n}:')
       print(f'  field_changed: {o.get("X") != n_.get("X")}')
       if o.get("X") != n_.get("X"):
           print(f'    OLD: {o.get("X")!r}')
           print(f'    NEW: {n_.get("X")!r}')
   ```
2. **發現差異立刻還原**整個欄位（用 `old_value` 蓋回 `new_value`），不要試圖「手動修幾字」
3. **任何 patch 後對中文檔案**先 `diff <(git show HEAD:path) path` 全文比對

**預防**：
- 改 jobs.json / SKILL.md 等含中文檔時，**避免用 patch tool 改「不打算改的中文字段」**
- 若 old_string 需要包含中文長字串才能精準定位，先**縮到最小中文字串**（例：只找關鍵動詞），把要改的東西用 new_string 傳過去
- 高風險檔（jobs.json、SOUL.md、MEMORY.md、USER.md）patch 後必跑欄位級比對

**If→Then**：
- **If** patch tool 改中文檔、field 比對發現有 unicode normalization 差異 **Then** 用 `python3` 直接寫入 backup 的原值、不要糾結 patch 為何「成功」
- **If** 必須改中文檔 **Then** 改前 `cp` 備份、改後 python 欄位比對、發現差異立刻還原

---

## 觀察到的附帶問題（記錄、不修）

1. **`v4-backup-full-weekly` prompt 與 script 不一致**（pre-existing）：
   - `prompt` 欄位說「跑 hermes-backup-v4.sh --upload-tier2」
   - `script` 欄位實際是「hermes-backup-v4.sh」（沒帶 `--upload-tier2`）
   - 結果：週日全量備份實際跑的是「Tier 1 + Tier 2 本地加密」沒上 Drive
   - 跟 brief 任務無關

2. **`hermes-secrets-encrypt.sh` 的 `rclone | tail -3` + `set -euo pipefail` 互動**（pre-existing）：
   - rclone 內部 retry 成功時，整段 pipe 仍回非 0 exit
   - secret 加密成功落本地，但 script exit code 失敗
   - 詳跑版有同樣問題、跟 brief 無關

3. **v4 備份輸出冗長**（已於 2026-07-02 完成 brief 化）：三個 job（v4-backup-tier1-daily / tier2-daily / full-weekly）Telegram 訊息從 ~2400 bytes 簡化到 ~170 bytes。