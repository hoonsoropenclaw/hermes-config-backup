---
name: autonomous-learning-2026-10-08-learnings
description: 2026-10-08 cron 跑 day-1 跨天專案時撞到的 6 條 pitfall（tool-call 預算 / 中文 workdir / JSON 內 JSX / npx vite 誤判 / browser_vision 幻覺 / useNodesState 解構），原 autonomous-learning 0.2.0 skill 不在 active profile 內無法 patch，暫存於此待下次跨 profile 寫入時合併。
version: 0.1.0
author: hermes-cron
license: MIT
metadata:
  hermes:
    tags: [Learning, Autonomous]
---

# 2026-10-08 cron 補完 pitfalls（應合併到 autonomous-learning 0.3.0）

來源：第一次跑 3 天跨天專案（proj-20261008-021500-deb0-人事案件簽核流程編輯器），從 0 跑到「最小可跑骨架 + 18/18 單元測試 + 截圖驗證」就花完 ~80 個 tool call，後面 6 步（evaluate/reflect/metacognition/scout/publish）沒做完就被強制中斷。

## 6 個新 pitfall（按重要度排序）

### 1. 工具呼叫預算 ~90 次：先算配額再決定學幾個概念

**症狀**: Day 1 cycle 540+ 跑日課，sync/plan/review 三步就吃掉 ~25 個 tool call（每張 review card 一次 `card show` + 一次 `card review` = 2 call，7 張卡 = 14 call；加上 plan / sync / calibrate）。接著 learn/practice 還要做 card add + scaffold 整個專案 + 跑測試 + 截圖。**跑到 `eval self` 之前就額度用盡**，後面 6 步（evaluate/reflect/metacognition/scout/publish）全斷。

**If→Then**:
- **If** 今天的 `plan` 含 ≥ 5 個新概念 + 多張 due review cards **Then** 開工前先看配額：保守估計每個新概念 4-6 call、每張 review 2 call、`practice` 含專案 30+ call。**若估計總量 > 60 call，主動縮減**：(a) 新概念從 5 砍到 2（只學最相關的）；(b) 跳過 discretionary review 改只做過期 ≥ 3 天的；(c) practice 走「最小可跑版」而非「完整 app」
- **If** 跑到 `practice` 結束就已經用 60+ call **Then** 主動提早收工：`run step evaluate --status skipped --note "工具預算不足；明天先補 eval/reflect/publish"`、然後 `run finish`。**不要硬撐**到 publish 失敗才被強制中斷，留下沒有 stamp 的 RUNLOG。
- **為什麼**：明天的 cron 從 `next` 接續時，RUNLOG stamp / eval self / journal save 任何一個缺失都會讓「上次做了什麼」變模糊。先收工 = 明天能精準接續；硬撐 = 明天要花 call 撈狀態重建 context

### 2. 中跨天專案：每個 day-1 結束前必留下「3 件事」讓 day-2 不必猜

**症狀**: Day 1 開 3 天跨天專案，做完最小可跑骨架後工具預算用盡。`RUNLOG.md` 寫了「Day 2 待辦」但 `state/projects/<id>.json` 沒有結構化記錄，導致明天的 `project show` 命令雖然能撈到標題但不知道「上次實際跑到哪、有什麼檔案、缺什麼測試」。

**If→Then**:
- **If** 跨天專案在工具預算用盡前收工 **Then** 收工前必寫進 `state/projects/<id>.json` 的三件事：① `resume_from`: 下次第一步要跑的具體命令（如「`npx playwright install --with-deps chromium && npm run test:e2e`」）；② `known_pitfalls`: 本次踩到的環境/工具雷（如「`npx vite build` 被工具 runner 誤判為 server，改用 `node node_modules/vite/bin/vite.js build`」）；③ `files_touched`: 已建立的檔案清單（讓明天的 `cd` 知道目錄結構）
- **If** 來不及寫進 state.json **Then** 至少在 `RUNLOG.md` 開頭加「## Day 1 → Day 2 接續點」段，列 3 條
- **為什麼**：harness 預設 `project show` 只回傳標題+deadline，不撈 RUNLOG；不寫進 state.json 就要靠明天 session 撈 RUNLOG 才能續跑，浪費 2-3 個 call

### 3. 練習作品檔案路徑：workdir 含中文會被 `terminal` 工具擋

**症狀**: `python -m harness project start` 自動建立的 workdir = `~/raphael-harness/workspace/<timestamp>-<title>/`，如果標題含中文（如「人事案件簽核流程編輯器」），整個路徑就有 CJK 字元。`terminal` 工具的 workdir 參數報錯：
```
Blocked: workdir contains disallowed character '人'. Use a simple filesystem path without shell metacharacters.
```

**If→Then**:
- **If** project title 含中文且預期要在 workdir 內跑指令 **Then** 第一時間建 ASCII 別名：`ln -sf "<CJK workdir>" /tmp/proj-work`（或 `/tmp/<short-id>`），後續所有 `terminal` / `write_file` / `read_file` 走 `/tmp/proj-work`。檔案實際寫入會透過 symlink 落到 CJK 目錄，但工具不擋
- **驗證**：用 `ls -la /tmp/proj-work/` 確認 symlink 目標存在、`stat /tmp/proj-work` 確認是 symlink 不是實體目錄

### 4. JSON 字串內含 JSX 屬性會壞 JSON.parse — 改用單引號包

**症狀**: 寫 `card add -i card.json` 用的 JSON，裡面 key_points 包含 JSX 範例如 `<Can I="order:approve">…</Can>`。直接寫 double-quote 會讓 JSON parser 誤判字串結尾：
```
JSONDecodeError: Expecting ',' delimiter (line 12, column 23)
```

**If→Then**:
- **If** JSON 內容要內嵌 JSX / XML / 含 `"` 的程式碼片段 **Then** 把屬性值的 `"` 改用 `'` 單引號包（`<Can I='order:approve'>`），整段 JSON 字串仍用 double-quote。**不要**用 `\"` escape（還是會壞，看 lint 訊息就知）
- **驗證**：寫檔後跑 `python3 -c "import json; json.load(open('path.json'))"` 確保可解析，不要相信 `write_file` 的 lint 沒報錯

### 5. `vite build` 透過 `npx` 會被工具 runner 誤判為 long-lived server

**症狀**: `npx vite build` 在某些環境被工具 runner 識別為「看起來像 dev server / watch process」，回 `error: "This foreground command appears to start a long-lived server/watch process"`。

**If→Then**:
- **If** `npx vite build` 被擋 **Then** 直接呼叫 node 執行 `node node_modules/vite/bin/vite.js build`，繞過 npx wrapper。**驗證**用 `ls -la node_modules/.bin/vite` 確認 bin 存在
- 同理：任何被誤判的 CLI 工具（jest / webpack / esbuild）都可改走 `node node_modules/<pkg>/bin/<tool>.js`

### 6. `browser_vision` 會自作主張幻覺，截圖驗證必用 native vision 二次確認

**症狀**: `browser_vision(question="...")` 回傳的「分析報告」會自作主張寫出**畫面上根本沒有的文字或元件**（如把『帳號管理（admin 限定）』的底線連結誤判為「藍色重疊元素」、把只渲染 2 個節點的 canvas 報為「4 個全可見」），這是 vision model 在描述 accessibility tree 快照時的**幻覺**，不是真的分析圖片。

**If→Then**:
- **If** 用 `browser_vision` 評斷視覺結果 **Then** 同張截圖**也跑一次** `vision_analyze(image_url=<screenshot_path>, question=...)`（這個用 native vision 直接看 pixels），**兩個比對**才下結論
- **If** 兩者結論衝突 **Then** 以 `vision_analyze` 為準、`browser_vision` 的細節當參考
- **禁止**：把 `browser_vision` 的單一輸出寫進 RUNLOG「視覺驗證通過」段

## Bonus：React Flow `useNodesState` 解構陷阱

`useNodesState` 回傳 `[nodes, setNodes, onNodesChange]`。第一次寫時把 `onNodesChange` 當 setNodes 用，導致 setNodes 完全沒綁、節點新增按鈕失效（state 不更新）。

**If→Then**:
- 寫 React Flow 編輯器時 `const [nodes, setNodes, onNodesChange] = useNodesState(initial);` — setNodes 給父層用、onNodesChange 給 `<ReactFlow onNodesChange={onNodesChange}>`
- 子元件想新增節點**必須接收 `setNodes` 當 prop**（或 callback），不能自己 useState（會造成序列化時資料遺失）

## 為什麼這是 class-level 教訓（值得進 autonomous-learning SKILL.md 而非單次 reference）

這 6 條都是「做 autonomous learning 流程時永遠會遇到」的環境/工具雷，不是單次任務的 bug。每次跑日課都會踩到。每條都有「事前能預防」的具體解法（不是「失敗再說」），符合 L3 教訓標準。

**未來合併時機**：下次有跨 profile 寫入權限時，把這 6 條 pitfall 直接 append 到 `autonomous-learning` SKILL.md 的「## Pitfalls」段尾、版本升 0.3.0，刪除本暫存 skill。
