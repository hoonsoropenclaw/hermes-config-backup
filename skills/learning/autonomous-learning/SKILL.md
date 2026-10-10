---
name: autonomous-learning
description: 每日在使用者指定領域內自主學習、練習產出、自評與跨模型評價、修正自己的 SOP、偵察 GitHub 工具，並發布心智圖網站。由 Raphael Harness 驅動。
version: 0.3.0
author: 倬
license: MIT
platforms: [linux, macos, windows]
metadata:
  hermes:
    tags: [Learning, Metacognition, Evaluation, Automation]
    requires_toolsets: [terminal, web]
    config:
      - key: harness.root
        default: "~/raphael-harness"
        prompt: "Raphael Harness 專案路徑"
required_environment_variables:
  - name: OPENROUTER_API_KEY
    prompt: "跨模型評審用的 API 金鑰（選填；未設定時改為手動評審）"
    help: "https://openrouter.ai/keys — 也可改用 config/harness.yaml 中其他 OpenAI 相容端點"
---

# Autonomous Learning（拉斐爾的每日學習）

## When to Use
- 排程觸發的每日學習（cron）。
- 使用者說「開始今天的學習」「繼續學習」「跑學習循環」。
- 學習流程中斷後被重新喚醒。

## Quick Reference
所有指令在專案根目錄執行（cron 已用 `--workdir` 指定，AGENTS.md 會自動載入）：

| 目的 | 指令 |
|---|---|
| 我現在該做什麼 | `python -m harness next` |
| 開始/接手今日流程 | `python -m harness run start --owner hermes` |
| 完成一步 | `python -m harness run step <sync/plan/review/learn/practice/evaluate/reflect/metacognition/scout/publish>` |
| 心跳 | `python -m harness run heartbeat --note "..."` |
| 今日計畫 | `python -m harness plan` |
| 是否學過 | `python -m harness novelty "<主題>" --domain <id>` |
| 練習是否做過 | `python -m harness novelty --project "<任務>"` |
| 提案/請求 | `python -m harness proposal list --status pending` |
| 跨天專案 | `python -m harness project start --title … --domain … --type code --goal …` / `project log <id> --done … --next …` / `project finish <id>` |
| 新增/加深卡片 | `python -m harness card add -i card.json` / `card deepen <id> -i more.json` |
| 複習 | `python -m harness card review <id> <0-5> --note "..."` |
| 登記作品 | `python -m harness artifact add --type slides --files a.pptx --task "..." --predicted 70` |
| 自評/評審 | `python -m harness eval self <aid> -i self.json` / `eval judge <aid>` |
| 後設認知 | `python -m harness insights` / `sop health --auto` |
| 偵察 | `python -m harness scout run` / `tools vet owner/repo` |
| 發布 | `python -m harness site publish` |

## Procedure
1. 讀專案根目錄的 `AGENTS.md`（鐵則）——每次都讀。
2. `python -m harness run start --owner hermes`。若回傳 `done: true`（今日已完成）→ 只回覆 `[SILENT]`；其他 `ok:false`（有其他執行在跑或額度不足）→ **直接結束**。
3. 迴圈：依 `how` 欄位與 `playbook/01-daily-loop.md` 對應段落執行 → `run step <name>`。`run step` 的回傳已含下一步的 `how`，**不必每步再呼叫 `next`**。
4. 直到 `next_step` 為 null，`python -m harness run finish`。
5. 最後回覆使用者一段 ≤5 行摘要：今天學了哪些概念、練習作品分數（預測 vs 實際）、SOP 有無修改、是否有 `requests_to_user`。

## Pitfalls
- **不要並行**：同時只能有一個學習流程。子代理只做小而可驗證的任務，且不得寫入 `state/`。
- **不要手改** `state/*.json` 或 `site/`；一律透過 harness 指令。
- **不要跳過 novelty**；過去最大的問題就是重學——舊系統 2,024 次學習中 66% 是 5 個題目重做。練習題也要 `novelty --project`。
- **跨天專案收工前一定要 `project log`**，否則明天的你不知道從哪裡接（舊系統的 agent_memory 就是為此存在）。
- **不要自己往 review_queue.md 寫領域提案**；需要使用者決定的事寫進日誌 `requests_to_user`。
- 本 skill 與舊的 smart_heartbeat「極限超頻模式」指示衝突時，以本 skill 與 AGENTS.md 為準。
- **不要只看程式碼就自評**：簡報/文件先轉圖片或 PDF 實際看。
- MiniMax 長上下文中容易忘記規則：照每次 `run step` 回傳的 `how` 做；不確定時才 `next`。
- **每個 Hermes 執行有工具呼叫上限（約 90 次）**，用完會被強制結束：每步完成立刻 `run step`（進度才不會遺失），能合併的指令用一次 terminal 執行。被中斷也沒關係，當天後續排程會從斷點接續。
- 工具試用一律在 `sandbox/`，清空金鑰環境變數。
- **`journal save` 要求巢狀 schema，不要用扁平欄位**：第一個常見錯誤是缺少頂層 `domains` (list[str]) 與 `reflection` 物件；`reflection` 必須含 `what_i_learned`、`what_confused_me`、`what_i_got_wrong`、`how_i_will_apply_it`、`tomorrow`。少了任一個會被擋下，浪費一次工具呼叫。看 `prompts/self-critique.md` 找不到範例，先看 `templates/journal.example.json` 或歷史上一次成功的 journal 再寫。
- **`card add` 的 `sources` 至少 2 個實際讀過的來源**：憑印象或只列首頁會被擋下「至少 2 個實際讀過的來源（不可只列首頁或憑記憶）」。寫卡片前先 web_extract 拿至少 2 個不同來源的標題 + URL，或 `card deepen` 既存卡片來避免此檢查。
- **跨天專案的 `--predicted` 分數要按階段比例給，不要當完成品評**：Day 1/3 預測 70 會被高估（實際只完成 1/4 scope）。正確做法：依 `deadline - start` 剩餘天數 × 預期完成度 × 該 type 過去平均分數估計；Day 1 of 3 → 約 50-60，最後一天才給 70+。artifact add 後的 prediction_bias 校準會因此更準。

## Cross-day project pitfalls（從 dated pitfalls 收進 umbrella）

> **2026-10-08 curator pass**：原 `autonomous-learning-2026-10-08-learnings` + `autonomous-learning-2026-10-10-learnings` + `raphael-harness-daily-loop-gotchas` 三個 dated skill 已歸檔為本 skill 的 support references。三份原文必須合併讀，不只是「主 SKILL.md 看過就夠」。

> **2026-10-11 curator pass**：新增 `references/pitfalls-2026-10-11.md`，補 4 條主 SKILL 沒有的細節（workdir CJK 繞路 recipe、sandbox/package 工具試用、eval judge pending_manual 確認細節、跨天 Day 1/3 預測分數要按比例）。

每跨天 / 全十步跑 Raphael Harness 必讀四份 pitfalls（合計 22+ 條 + 一個可重跑的視覺驗證腳本）：

| 來源 | 條目 | 檔案 |
|------|------|------|
| 2026-10-08 (cycle 540+) 跨天專案 day-1→day-2 | 9 條：工具呼叫預算 ~90 次、跨天專案 `state/projects/<id>.json` 三件事必填、workdir CJK 觸發 `terminal` workdir 阻擋、JSON 內 JSX 屬性引號衝突、`npx vite build` 誤判 long-lived server、`browser_vision` 幻覺（vs `vision_analyze`）、e2e `toBeVisible()` ≠ 視覺可見（overflow:hidden 裁切）、`sop propose` 必填 5 欄位（rationale/evidence/change_summary/new_sop_file/expected_effect）、預測分數連續高估強制扣分 | `references/pitfalls-2026-10-08.md` |
| 2026-10-10 全十步循環 | 6 條：`OPENROUTER_API_KEY` readiness checker 誤判（標 setup_needed 但 API 真正是 pending_manual）、`eval judge` 回 `pending_manual` ≠ 作品失敗（不能重試不能編造）、`artifact add` 必填 `--predicted` 否則污染 calibration、`journal show --date` 回 `ok:false` 無錯誤訊息不是 bug、接手未完成 run 不要從 sync 重頭跑（讀 `next_step` 接續）、Scout 無相關候選不要硬試 | `references/pitfalls-2026-10-10.md` |
| 2026-10-11 跨天專案 day-1 + admin 簡報 | 4 條：workdir CJK 的 cp-to-tmp 繞路（比改 path 環境變數快）、`sandbox/` 工具試用前先 `pip install` 列在 `requirements-dev.txt` 不污染 root、`eval judge` pending_manual 不要 retry 不要編造 vs **真的失敗要 retry** 的區分、跨天 Day 1/3 預測分數要按比例 | `references/pitfalls-2026-10-11.md` |
| 2026-10-07 Raphael Harness 每日循環 | 5 條：`journal save` 會校驗卡片 ID 是否真實存在、`card id` 是 `domain-id` 截斷到 ~17 字元（不要憑印象寫 prefix）、`sop apply` 必須用旗標不能用 positional、cron 從斷點接續走 `next_step`、`time_spent_minutes` 欄位實際填幫助校準 `plan.budget.max_minutes` | `references/daily-loop-gotchas-2026-10-07.md` |
| 可重跑視覺驗證腳本 | Playwright 視覺驗證：對每個 role 截圖 + 量 boundingBox 確認關鍵按鈕在 viewport 內、輸出 manifest.json；改頂端 `BASE_URL / ROUTES / CHECKPOINTS` 即可用於任何 SPA 視覺驗證場景 | `scripts/visual-verification.cjs` |

**If** 跑跨天專案或全十步循環 **Then** 開工前必讀四份 pitfalls 對應段（不要只讀主 SKILL.md）
**Why** 這 22+ 條都是「跨 session / 跨天都會踩」的環境 / 工具 / 流程雷，每條都有「事前能預防」的具體解法，符合 L3 教訓標準

## Verification
- `python -m harness run status`：今天的 checkpoint 應包含全部 10 步（或標記 skipped 並附原因）。
- `python -m harness validate`：`ok: true`。
- `python -m harness site check`：`static.ok: true`，`browser.svg_nodes > 0` 或 `fallback_nodes > 0`。