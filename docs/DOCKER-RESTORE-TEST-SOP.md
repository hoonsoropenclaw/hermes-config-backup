# Docker 異機還原測試 SOP（2026-06-06 制定）

> **目的**：用 docker 容器模擬「新主機」，從 Google Drive 下載 hermes_backup，跑 hermes-restore.sh，**完整驗證**異機還原流程能跑通。
>
> **重要**：**用 subagent 跑這個測試**，不要在主 session 跑。
> 理由：測試會動到 ~/.hermes/、rclone config、跑 hermes-gateway，**跟主 session 正在運行的 hermes-agent 衝突**。
> 用 subagent（delegate_task）跑失敗也不會污染主對話、還能從 subagent 回報看詳細 log。

## 0. 環境檢查（在主 session 做）

確認 docker 可用、確認 rclone 連線正常、確認備份存在：

```bash
# 確認 docker
docker --version
docker ps  # 不需要跑 container，只看 daemon 有沒起

# 確認 rclone 連線（必須在主 session 做，subagent 用同一份 config）
rclone lsf crypt_hermes: --config /home/hoonsoropenclaw/documents/rclone.conf

# 確認備份存在
rclone lsf "crypt_hermes:hermes_backup_20260606_211411_full/" --config /home/hoonsoropenclaw/documents/rclone.conf
```

**預期**：
- `docker --version` 顯示版本
- `docker ps` 沒 error
- `rclone lsf crypt_hermes:` 顯示 `HERMES-BACKUP-README.md`、`hermes-restore.sh`、`hermes_backup_20260606_211411_full/`
- 211411_full 內有 `hermes_backup_20260606_211411_full.tar.gz`、`RESTORE.md`、`restore_hermes.sh/`

## 1. 在主 session 做的事

**只做這些，不要碰 ~/.hermes/**：

1. 確認 hermes-gateway 在跑（**不要 kill 它**）：
   ```bash
   ps aux | grep hermes-gateway | grep -v grep
   ```

2. 把 rclone.conf 複製到一個 subagent 可讀的位置（其實它在 /home/hoonsoropenclaw/documents/rclone.conf，subagent 透過 delegate_task 會自動能讀）

3. **把這份 SOP 整個交給 subagent**，告訴它：
   - 跑 docker 容器
   - 從 Drive 下載 hermes-restore.sh
   - 跑 hermes-restore.sh（**互動式選全部 yes**）
   - 驗證還原成功
   - **測試完** docker rm 容器
   - 詳細回報每一步的真實輸出

## 2. Subagent 跑的完整 SOP

### Step 1: 準備 docker 容器

```bash
# 拉 Ubuntu 24.04（最小）
docker pull ubuntu:24.04

# 啟動容器（**不要掛載主機 ~/.hermes/，要測試真的從 Drive 下載還原**）
docker run -itd --name hermes-restore-test \
  -v /home/hoonsoropenclaw/documents:/test-rclone-conf:ro \
  ubuntu:24.04 bash

# 進容器
docker exec -it hermes-restore-test bash
```

### Step 2: 在容器內安裝必要工具

```bash
apt update && apt install -y rclone git python3 python3-pip curl
```

### Step 3: 把 rclone.conf 從掛載目錄複製到正確位置

```bash
mkdir -p /root/documents
cp /test-rclone-conf/rclone.conf /root/documents/rclone.conf
chmod 600 /root/documents/rclone.conf
# 確認能列 remote
rclone listremotes --config /root/documents/rclone.conf
# 預期看到 crypt_hermes: 跟 hoonsorasus:
```

### Step 4: 下載 hermes-restore.sh

```bash
mkdir -p /tmp/restore-test
cd /tmp/restore-test
rclone copy "crypt_hermes:hermes-restore.sh" . --config /root/documents/rclone.conf
# 這裡 rclone crypt 會自動解密 .sh 檔
ls -la
# 預期看到 hermes-restore.sh
```

### Step 5: 準備 hermes_home（**用 /tmp 模擬新主機的 ~/.hermes**）

```bash
# 在容器內 /tmp 模擬新主機
export HERMES_HOME="/tmp/hermes-restore"
mkdir -p "$HERMES_HOME"
```

### Step 6: 編輯 hermes-restore.sh 的頂部變數

**必須改**：
```bash
# 把這行
HERMES_HOME="$HOME/.hermes"
# 改成
HERMES_HOME="/tmp/hermes-restore"

# 把這行
RCLONE_CONFIG="$HOME/documents/rclone.conf"
# 改成
RCLONE_CONFIG="/root/documents/rclone.conf"

# 改完檢查
grep -E "^HERMES_HOME=|^RCLONE_CONFIG=" hermes-restore.sh
```

### Step 7: 跑 hermes-restore.sh

```bash
chmod +x hermes-restore.sh
./hermes-restore.sh
```

**互動式回答**（依序）：
- 設定正確嗎？ → `yes`
- 還原核心設定？ → `Y`（Enter 預設）
- 還原 .env？ → `Y`
- 還原 state.db？ → `Y`
- 還原 hermes-agent（含 venv）？ → `Y`（**重要**：要驗證含 venv）
- 還原 GPG token？ → `Y`
- 還原 sparc-methodology？ → `Y`

### Step 8: 驗證還原結果

跑這些確認真的還原成功：

```bash
# 1. 目錄結構
ls -la /tmp/hermes-restore/
# 預期: config/ memories/ skills/ scripts/ data/ docs/ + full_backups/

# 2. .env 還原（mode 600）
ls -la /tmp/hermes-restore/.env
# 預期: mode 600

# 3. 7 個核心 MD
ls /tmp/hermes-restore/memories/
# 預期: AGENTS.md HEARTBEAT.md IDENTITY.md MEMORY.md SOUL.md TOOLS.md USER.md

# 4. 333 個 skill
ls /tmp/hermes-restore/skills/ | wc -l
# 預期: 333 個目錄（或子目錄）

# 5. hermes-agent 含 venv
ls /tmp/hermes-restore/full_backups/hermes-agent/venv/
# 預期: bin/ include/ lib/ pyvenv.cfg 等

# 6. state.db 大小
ls -la /tmp/hermes-restore/state.db
# 預期: ~166 MB

# 7. 還原的 hermes-agent 真的能跑
/tmp/hermes-restore/full_backups/hermes-agent/venv/bin/python --version
# 預期: Python 3.11.x

# 8. 跑實際指令
/tmp/hermes-restore/full_backups/hermes-agent/venv/bin/python -c "import sys; print(sys.path)"
# 預期: 印出 sys.path
```

### Step 9: 測試 hermes-gateway 啟動

```bash
# 還原的 hermes-agent 能否啟動
cd /tmp/hermes-restore
ls full_backups/hermes-agent/
# 看有沒有 run_agent.py
python full_backups/hermes-agent/run_agent.py --version 2>&1 | head -5
# 或跑 hermes CLI
PYTHONPATH=full_backups/hermes-agent ./full_backups/hermes-agent/venv/bin/python -m hermes_cli.main --version
```

**注意**：在新主機的 hermes-gateway **不應該啟動**（避免跟主機搶 Telegram session）。
只驗證能 import + CLI 能跑，不真的啟動。

### Step 10: 清理

```bash
# 容器內
exit  # 離開容器 shell

# 容器外
docker stop hermes-restore-test
docker rm hermes-restore-test
docker rmi ubuntu:24.04  # 選擇性，刪 image
```

## 3. Subagent 必須回報的東西

回主 session 時要包含：
- 每個 Step 的真實輸出（不要「✅」emoji，要有真實 stdout）
- 任何錯誤、warning、卡住
- 最終驗證的 8 項檢查結果
- 清理的 docker 指令輸出

## 4. 失敗時怎麼辦

**If** Step 4 下載 hermes-restore.sh 失敗
**Then** 確認 rclone.conf 是不是真的有 crypt_hermes remote

**If** Step 7 hermes-restore.sh 卡在「找最新備份」
**Then** 用 `rclone lsd crypt_hermes:` 手動確認備份資料夾存在

**If** Step 7 報「找不到 .env」
**Then** 確認 Drive 上 211411_full 內的 tar.gz 真的有 .env

**If** Step 8 第 5 項失敗（venv 沒還原）
**Then** v3.1 的 venv 進備份邏輯可能出問題，需重跑備份

**If** 任何時候 docker 卡住
**Then** `docker stop hermes-restore-test && docker rm hermes-restore-test` 強制清掉

## 5. 注意事項

- **不要 kill 主機的 hermes-gateway**（你說要避免衝突、但測試容器是獨立的、不需要關主機）
- **不要掛載主機 ~/.hermes/ 到容器**（要測試真的異機還原）
- 容器跑完 `docker rm` 真的刪除（避免累積）
- subagent 跑失敗也沒關係、可以再跑

---

最後更新：2026-06-06
設計者：赫米斯（給未來跑異機還原測試的 subagent 用）
