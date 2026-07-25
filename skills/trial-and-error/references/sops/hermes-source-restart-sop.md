# Hermes Source Code Restart SOP (SOP-7)

**用途**：當修改了 `hermes-agent/*.py` 原始碼或 `~/.hermes/config.yaml` 後，如何正確重啟 gateway 使變更生效。  
**觸發條件**：任何對 hermes-agent 原始碼或 config.yaml 的修改完成後。

---

## 為什麼修改後要重啟

Hermes 是 Python 程式，模組在 `import` 時載入記憶體。修改磁碟上的 `.py` 檔案不會自動更新已經在跑的 process——必須重啟 gateway 才能讓新程式碼生效。

config.yaml 同理：gateway 啟動時讀一次，不會熱重載。

---

## 7 步重啟流程

### Step 1：觸發重啟
```bash
sudo systemctl restart hermes-gateway.service &
```
**背景執行**（`&`）：因為這個命令會卡 90-210 秒，背景執行才不會 timeout。

---

### Step 2：等待 30 秒，第一次檢查
```bash
sleep 30
pgrep -af "hermes_cli.main gateway"
systemctl status hermes-gateway | grep -E "Active:|Main PID:"
```
預期：PID 还没換（graceful shutdown 還在跑）。

---

### Step 3：等待 60 秒，第二次檢查
```bash
sleep 60
pgrep -af "hermes_cli.main gateway"
```
預期：看到**新的 PID**（舊的被 kill，新啟動）。

---

### Step 4：驗證新 PID 啟動 log
```bash
journalctl -u hermes-gateway -n 10 --no-pager | tail -5
```
預期：看到 `Started hermes-gateway.service` 或類似啟動成功的 log。

---

### Step 5：驗證 Telegram 連線恢復
gateway 重啟後，Telegram long polling 會重新連線。
```bash
# 發一個測試訊息確認 bot 回應
curl -s "https://api.telegram.org/bot<TOKEN>/getMe" | grep '"ok":true'
```
或者直接對 bot 發訊息，觀察是否有回應。

---

### Step 6：驗證修改的程式碼生效（針對性）
根據你改了什麼，驗證對應功能：
- 改了 `*.py` → 執行對應功能確認行為正確
- 改了 `config.yaml` → `hermes config list` 確認設定已載入

---

### Step 7：清理
```bash
# 確認没有殘留的舊 gateway process
ps aux | grep "hermes_cli.main" | grep -v grep
```

---

## 為什麼 restart 要卡 90-210 秒

`hermes-gateway.service` 的 systemd 設定是 `Type=simple`，沒有設 `TimeoutStopSec`。

systemd 預設在 SIGTERM 發出 90 秒後才會 SIGKILL。

gateway 收到 SIGTERM 後要：
1. 等 in-flight agent request 跑完（30-90 秒）
2. 等 Telegram API 釋放 long polling 連線（30-60 秒）
3. 才真正退出

**所以 90-210 秒的等待是正常的，不是 bug。**

---

## 常見錯誤

### 錯誤 1：在 gateway 內部執行 restart
```bash
# 這個命令會失敗
sudo systemctl restart hermes-gateway.service
# 錯誤：Refusing to restart from inside gateway process
```
**解法**：從外部執行（透過 cron job 或另一個 terminal session）。

### 錯誤 2：等待 30 秒就以為重啟完成
**解法**：有時候 graceful shutdown 會拖到 90-210 秒。30 秒不够，要等 60 秒再查。

### 錯誤 3：修改 .py 但没重啟
```bash
# 改了程式碼
vim ~/.hermes/hermes-agent/hermes_agent/tools/foo.py

# 直接測試——没效！
# 因為 gateway 還在用記憶體裡的舊版
```
**解法**：每次改完 .py 都要重啟 gateway。

---

## 一鍵三段驗證命令

```bash
# 整合驗證（任何時候想知道 gateway 狀態就跑這個）
python3 -c "
import subprocess, json

# 1. PID 確認
pids = subprocess.run(['pgrep', '-af', 'hermes_cli.main gateway'], capture_output=True, text=True)
print('=== PID ===')
print(pids.stdout.strip() or '無')

# 2. systemd 狀態
status = subprocess.run(['systemctl', 'status', 'hermes-gateway'], capture_output=True, text=True)
for line in status.stdout.split('\n')[1:4]:
    print(line)

# 3. jobs.json 中的 cron last_status
try:
    d = json.load(open('/home/hoonsoropenclaw/.hermes/cron/jobs.json'))
    errors = [j['name'] for j in d.get('jobs', []) if j.get('last_status') == 'error']
    print(f'=== Cron Errors ({len(errors)}) ===')
    print('\n'.join(errors) or '無')
except: pass
"
```

---

## If→Then 規則

**If→Then**: **If** 修改了 `hermes-agent/*.py` 或 `config.yaml` **Then** 立即執行 `sudo systemctl restart hermes-gateway.service &`，不等

**If→Then**: **If** restart 命令發出後 30 秒內沒有新 PID **Then** 等 60 秒再查，不要焦慮重複觸發

**If→Then**: **If** 重啟後 Telegram bot 沒有回應 **Then** 先等 30 秒（Telegram 重連需要時間），再發測試訊息

**If→Then**: **If** 修改 .py 檔案後功能沒有變化 **Then** 第一件事：確認有没有重啟 gateway，不要假設「改了 code 就應該有效」

**If→Then**: **If** 從 gateway 內部需要重啟自己 **Then** 使用 `nohup sudo systemctl restart hermes-gateway.service &` 背景執行，或透過 cron job 從外部觸發
