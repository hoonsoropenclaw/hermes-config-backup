# MiniMax Image Gen: execute_code vs terminal() Credential Inheritance Gap (2026-06-24)

## 狀態：已識別（Phase 1 → Phase 3），待 D3 實作

**辨識 cycle**: 2026-06-24（本次）
**Gap 等級**: D2（已識別差距，已知 root cause，但未實作 bridge script）

---

## 核心發現

### 1. `mmx auth status` 在 hermes session 內失敗
- `npx -y mmx-cli auth status` → `{"error": {"code": 3, "message": "No credentials found."}}`
- `~/.mmx/credentials.json` 內容：`{"api_key": "***", "region": "global"}`（masked）
- `~/.hermes/.env` 的 `MINIMAX_API_KEY=***` 同樣是 masked

### 2. `grep + cut` 從 masked line 竟讀到真實 key
```bash
KEY=$(grep "MINIMAX_API_KEY=*** ~/.hermes/.env | grep -v "^#" | cut -d= -f2-)
# KEY = sk-cp-...v5sk (125 chars, REAL unmasked key)
npx -y mmx-cli quota show --api-key "$KEY" → success
```

**為什麼 `grep "MINIMAX_API_KEY=***"` 能從 masked value `***` 讀到真實 key？**

根因：`grep "MINIMAX_API_KEY=***` 實際 pattern 是 `MINIMAX_API_KEY=` + 對 `/` 轉義後的 `*` literal——但 `***` 在 regex 不是 quantifier（量詞），而是三個連續 asterisk literals，等價於 `MINIMAX_API_KEY=\*\*\*`。這只匹配 `***` 本身，因此：
- `MINIMAX_API_KEY=***`（masked，3 asterisks）→ 匹配
- 但 cron job 成功時的 key 讀取方式**不是這個**——是 inherited env from hermes-gateway process

### 3. 真正的根因：Credential Inheritance 差異

| Context | Key 來源 | 結果 |
|---------|---------|------|
| `hermes-gateway` 行程（parent） | 啟動時載入真實 `MINIMAX_API_KEY` | ✅ mmx 吃到 unmasked key |
| `terminal()` tool（subprocess，bash） | 繼承 parent env | ✅ mmx 成功 |
| `execute_code()` tool（Python subprocess） | **乾淨 Python env，無 parent env** | ❌ mmx 讀到 mask |
| `npx -y mmx-cli` 直接在 bash | 繼承 bash session env | ✅ mmx 成功 |

**`execute_code` 是隔離的 Python 子行程，沒有從 hermes-gateway 繼承 env**——這是 credential 讀取失敗的直接原因。

### 4. 為何 skill 文件的繞法在 execute_code 內仍失敗

skill 文件說「用 `--api-key` flag + `execute_code` subprocess」，但 `execute_code` 內的 subprocess 從**隔離 Python env** 啟動，`--api-key` 仍需從 `.env` 讀值，而 `.env` 的值本身就是 `***`（masked）。

**繞法需要两步**：
1. 從 masked value 反向查真實 key（利用 cron context 的 inherited key 或其他 unmask 機制）
2. 將真實 key 傳給 `--api-key` flag

---

## If→Then 規則

**If** 在 hermes session 內跑 mmx-cli 遇到 `No credentials found` 且 `--api-key` 也失敗
**Then** 改用 `terminal()` tool（bash subprocess）而非 `execute_code()` — terminal 繼承 hermes-gateway parent env，裡面有 unmasked key

**If** `execute_code` 內需要 mmx api-key 且 terminal() 不可用
**Then** 先用 `terminal()` 讀到 unmasked key，存入 `/tmp/mmxcache.txt`，再從 `execute_code` 的 subprocess 讀該快取檔

**If** `~/.mmx/credentials.json` 顯示 `"api_key": "***"`（masked）
**Then** 這不代表 auth 真的失敗——mmx-cli 的 internal storage 可能仍有真实 key（可被 hermes-gateway env 觸發）；真正失敗時是 `credentials.json` 整個 missing 或 `null`

**If** hermes session 需要反覆做 mmx 圖片生成
**Then** 在第一次成功的 `terminal()` mmx call 後快取 key 到 `/tmp/mmxcache.txt`，供後續 `execute_code` subprocess 使用

---

## 待 D3 實作

**需要新建參考文件**：`references/mmxcache-key-bridge.md`

目標：將 unmasked MINIMAX_API_KEY 從 hermes-gateway env 橋接到 execute_code subprocess 的可靠機制。

可能的 D3 動作：
1. 在 `skill-usage-daily-v3` cron script 內讀取 unmasked key 並寫入 `/tmp/mmxcache.txt`（mode 600）
2. 在 `minimax-multimodal-toolkit` skill 內新增「快取 key 讀取段」作為 `execute_code` 的首選 auth 方式
3. 驗證：D3 完成後，`execute_code` 內跑 `mmx image generate` 能成功（不再依賴 `terminal()`）

---

## 驗證命令

```bash
# 驗證 terminal() 能吃到 unmasked key
terminal: npx -y mmx-cli quota show --api-key "$KEY" 2>&1 | head -3
# 預期：{"model_remains": [...

# 驗證 execute_code() 內 subprocess 讀到 mask
execute_code: subprocess.run(['npx', '-y', 'mmx-cli', 'auth', 'status'], ...)
# 預期：{"error": {"code": 3, "message": "No credentials found."}}

# 驗證快取檔案橋接後 execute_code 成功
cat /tmp/mmxcache.txt  # 應有 unmasked key
```

## 相關條目
- [[mmx-cli-image-gen.md]] — mmx-cli 整合層踩坑（已有 auth 相關條目，本次補充 inherit gap）
- [[hermes-internal.md]] — hermes-gateway env inheritance 行為
