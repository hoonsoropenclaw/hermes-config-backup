# Cron-Only Script 環境變數設計守則

**適用場景**：任何 `~/.hermes/scripts/*.sh` 且 `no_agent: true` 的 cron job script。  
**對應案例**：2026-06-15，`verify-recovery-chain.sh` 在 cron 環境 100% 失敗（`HERMES_USER_KEY` 拿不到）。

---

## 核心原則

cron 環境的三大限制：
1. **無 TTY** — 無法 `read -s` 互動取得密碼
2. **無登入 shell 環境** — `.bashrc` / `.bash_profile` / `.profile` 不會被執行
3. **最小化 PATH** — `which` 可能失效，需要用絕對路徑

**結論**：任何 cron script 需要 secrets，必須自己實現 2-3 層 fallback。

---

## 標準 3 層 fallback 模板

```bash
#!/usr/bin/env bash
set -euo pipefail

# ============================================
# 環境變數 3 層 fallback（cron-safe）
# ============================================
#
# Layer 1: 環境變數（hermes cron 注入，或人工 export）
# Layer 2: ~/.hermes/config/.hermes-<KEYNAME> 檔（chmod 600）
# Layer 3: 錯誤退出（找不到就失敗，不默默繼續）
#
# 用法：
#   KEY_VALUE="${KEY_VALUE:-$(cat "$HOME/.hermes/config/.hermes-<KEYNAME>" 2>/dev/null || echo '')}"
#   if [[ -z "$KEY_VALUE" ]]; then
#     echo "ERROR: <KEYNAME> not set and ~/.hermes/config/.hermes-<KEYNAME> not found" >&2
#     exit 1
#   fi
#
# ============================================

# HERMES_USER_KEY 範例
HERMES_USER_KEY="${HERMES_USER_KEY:-$(cat "$HOME/.hermes/config/.hermes-user-key" 2>/dev/null || echo '')}"
if [[ -z "${HERMES_USER_KEY}" ]]; then
  echo "ERROR: HERMES_USER_KEY not set and ~/.hermes/config/.hermes-user-key not found" >&2
  echo "  Set via: export HERMES_USER_KEY=\"<your_key>\"" >&2
  echo "  Or write key to: ~/.hermes/config/.hermes-user-key (chmod 600)" >&2
  exit 1
fi
```

---

## Bash Parameter Expansion 語法速查

| 語法 | 行為 | 適用場景 |
|------|------|----------|
| `${VAR:-default}` | VAR 為空或未設定時，**使用** default，但**不設值** | 讀取但不改變 VAR |
| `${VAR:=default}` | VAR 為空或未設定時，**使用並設值** default | 一次性初始化 |
| `${VAR:-$(cmd)}` | 為空時執行 command substitution | 兩層降級（env → 檔案）|

**本次案例的正確用法**：
```bash
# ✅ 正確：env 優先，env 空的話讀檔，讀不到才失敗
HERMES_USER_KEY="${HERMES_USER_KEY:-$(cat "$HOME/.hermes/config/.hermes-user-key" 2>/dev/null || echo '')}"

# ❌ 錯誤：這只在 VAR 已存在的情況下替換，不做 fallback
HERMES_USER_KEY="${HERMES_USER_KEY:-default}"
```

---

## 與 hermes-backup-v4.sh 的對比

| 腳本 | 位置 | 需求 | 實現方式 |
|------|------|------|----------|
| `hermes-backup-v4.sh` | `~/.hermes/scripts/` | Tier 2 加密上傳 | 3 層 fallback + 互動式 prompt（Layer 3） |
| `verify-recovery-chain.sh` | `~/.hermes/scripts/` | 鏈路驗證 | 原本只有 Layer 1（env 強制要求），**2026-06-15 修補後新增 Layer 2** |
| `hermes-backup-coverage-check.sh` | `~/.hermes/scripts/` | 路徑覆蓋率 | 無 secrets，依賴相對路徑 |
| `hermes-restore-v4.sh` | `~/.hermes/scripts/` | 還原 | 3 層 fallback + 互動式 prompt |

**教訓**：`verify-recovery-chain.sh` 原本沒有 Layer 2 降級，導致每次 cron 執行都失敗（`last_status: error`），而手動執行可正常運作（因為有 TTY 注入 env）。

---

## 驗證命令

```bash
# 測試 Layer 2 fallback（無 HERMES_USER_KEY 環境變數）
unset HERMES_USER_KEY && bash ~/.hermes/scripts/verify-recovery-chain.sh
# 預期：EXIT:0，HERMES_USER_KEY 從 ~/.hermes/config/.hermes-user-key 讀取

# 測試 Layer 1 優先（環境變數存在時）
HERMES_USER_KEY=test bash ~/.hermes/scripts/verify-recovery-chain.sh
# 預期：使用環境變數，不讀檔

# 確認檔案存在且權限正確
stat ~/.hermes/config/.hermes-user-key
# 預期：Access: (0600/-rw-------)，非 root 可讀
```

---

## 與 §10.10 的差異

§10.10 描述的是 `backup_passphrase_recovery()` 的 3 層 fallback 設計（hermes-backup-v4.sh 內）。

本文檔描述的是**獨立的 cron-only script**（如 verify-recovery-chain.sh）需要自己實現 fallback，而不是依賴呼叫端的環境。

簡言之：
- §10.10 = 被呼叫方（hermes-backup-v4.sh 內的函式）
- 本文檔 = 獨立 script 自己要有 fallback

---

## 預防規則

1. **任何需要 secrets 的 cron script，設計時就要有 fallback**，不要等失敗了再補
2. **Layer 2 檔案路徑要統一**：`~/.hermes/config/.hermes-<KEYNAME>`（chmod 600）
3. **不要假設 cron 有 TTY**：互動式 prompt 在 cron 環境會直接失敗
4. **每個新 cron script 都要跑 `unset VAR; bash script.sh` 驗證 Layer 2 fallback**
