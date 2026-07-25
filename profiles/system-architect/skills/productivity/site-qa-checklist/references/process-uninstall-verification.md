# 卸載後 Process State 驗證 SOP

> 從 2026-06-08 OpenClaw 反安裝任務的親身踩坑提煉
> 對應 SKILL.md「⚠️ 卸載 / 反安裝後 process state 驗證 SOP」段（陷阱 G/H/I/J）

## 為什麼這份文件重要

「卸載某個套件 / service」聽起來像「跑個指令就好」— 實際上**卸載後的 process state 驗證**才是真正的工作。指令回報成功 ≠ 沒有殘留。

卸載失敗的後果：
- 磁碟空間沒釋放（檔案 / 資料夾沒刪）
- Port 被佔用（service 沒停）
- 依賴的 MCP / API / CLI 認證被誤刪（auth.json、token）
- 同名 service 重新啟動時衝突（systemd unit 殘檔）
- 監控誤報（pgrep false positive → 誤以為漏網之魚 → 多花時間查）

## 4 個核心陷阱（速查）

| 陷阱 | 症狀 | 修正 |
|------|------|------|
| G | `pgrep -f <name>` 報 N 個進程誤判 | 用 `pgrep -f '<name>/dist'` 精準查、看 `pgrep -af <name>` 完整指令 |
| H | 推論「X 是被誰啟動的」推論錯 | `ps -o pid,ppid,cmd -p <X_pid>` 看 PPID 鏈 |
| I | 套件卸載後 systemd unit 殘檔 | `rm -f unit 檔 + daemon-reload + reset-failed` |
| J | 卸載才發現動太多東西 | `--dry-run` 或 `which/readlink/dpkg -L/npm list` 先 list target |

## 5 步完整驗證 SOP（卸載後必跑）

```bash
# Step 1: 套件本身已刪
command -v <package> 2>&1 || echo "✓ CLI 找不到"
which <package> 2>&1 || echo "✓ 套件路徑找不到"

# Step 2: 沒殘留 process（精準查法）
pgrep -f '<package>/dist' 2>&1 || echo "✓ 無 process"
pgrep -af <package> 2>&1 | head -5

# Step 3: systemd 沒殘檔
find ~/.config/systemd -name '*<package>*' 2>&1 || echo "✓ 無 unit 殘檔"
systemctl --user list-unit-files | grep <package> || echo "✓ systemd 不認得"

# Step 4: 依賴該套件的關鍵服務仍活
# 必用工具實際呼叫驗證（不要只看 process state）

# Step 5: 使用者面向的功能仍正常（從 production URL 測）
```

## 卸載前 3 個必問問題

1. **「X 是被誰啟動的」** — `ps -o ppid -p <X_pid>` 查
2. **「X 的卸載會動到哪些檔 / 服務 / process」** — `--dry-run` 或 list target
3. **「X 卸載後有誰會被連帶影響、需要備份 / 轉移 / 重啟」** — 跑 Step 4-5

**If** 3 個問題沒答案 **Then** 不要開始卸載

## 完整卸載決策樹

```
[使用者請求卸載 X]
        │
        ▼
[問 3 個問題 / 自己查]
        │
        ├── 不知 owner → ps -o ppid
        ├── 不知動到什麼 → --dry-run
        └── 不知連帶誰 → 用工具實測依賴服務
        │
        ▼
[卸載指令]
        │
        ▼
[5 步驗證]
        │
        ├── 任一失敗 → 補救（陷阱 G-J 的修正）
        └── 全部通過 → 才能回報「完成」
```

## 真實案例：2026-06-08 OpenClaw 反安裝

**背景：** OpenClaw 2026.5.4 套件 + 3.8GB workspace + 11 條 cron + 3 個 systemd unit + gateway port 18789

**卸載前 3 個問題的答案（從這次真實任務驗證過）：**

1. **owner 是誰？** OpenClaw gateway 跟 mempalace MCP 共享 process group。但 mempalace 的 PPID 是**赫米斯主進程**（不是 OpenClaw）→ 卸載 OpenClaw 不會影響 mempalace
2. **動到什麼？** `openclaw uninstall --all --dry-run` 列出 3 個動作（gateway service / ~/.openclaw / workspace）
3. **連帶影響？** 11 條 cron 會報 error log（路徑找不到）、status_dashboard 執行期輸出會失、YouTube token 跟 mempalace 仍可用

**卸載 5 步驗證實際結果：**

| 步驟 | 結果 |
|------|------|
| 1. CLI 找不到 | ✓ `command -v openclaw` 報 not found |
| 2. 沒 process | ✓ `pgrep -f 'openclaw/dist'` 空（但 `pgrep -f openclaw` 報 6 個 false positive — 陷阱 G 實證）|
| 3. systemd 沒殘檔 | ❌ **發現卸載 bug**：3 個 unit 檔還在 → 補陷阱 I 修正 |
| 4. 依賴服務仍活 | ✓ mempalace MCP 自動 re-spawn（PID 從 1872205 變 1896464）|
| 5. 生產端功能 | ✓ status site 仍 HTTP 200、赫米斯 14 個 mempalace 工具仍可用 |

## 教訓

1. **「卸載指令回報成功」≠「卸載完成」**。5 步驗證才是卸載完成
2. **`pgrep -f` 一定會誤報**。任何「卸載後驗證 process 真的清乾淨」必須用精準查法（陷阱 G）
3. **systemd unit 殘檔是卸載 bug**。100% 套件卸載後都要手動清（陷阱 I）
4. **卸載會 kill child process 副作用波**。mempalace MCP 換 PID 是「副作用波」+「自動 re-spawn」的正常訊號、不要當成錯誤
5. **卸載前 3 個必問問題** 5 分鐘內能查清楚,跳過 3 分鐘的查 → 浪費 30 分鐘的故障排除
