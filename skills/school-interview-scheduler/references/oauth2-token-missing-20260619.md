# school-interview-scheduler OAuth2 Token Gap (2026-06-19)

## 狀態：Google OAuth2 Device Flow 未執行

`~/.hermes/google_token.json` **不存在**（`ls -la` 確認）。

`create_interview.py` 期望在此路徑讀取 OAuth2 user credentials：
```python
TOKEN_FILE=os.environ["HERMES_HOME"] + "/google_token.json"
```

## 根因

D2 迴圈陷阱：SKILL.md 在 2026-06-17 cycle 建立（SOP 寫了，Google OAuth2 Device Flow 從未執行驗證）。

## 前置條件

要讓 `create_interview.py` 可用，需完成 Google OAuth2 Device Flow：

1. 在 Google Cloud Console 建立 OAuth 2.0 Client ID（Application type: Desktop 或 Web）
2. 啟用 Google Calendar API
3. 執行 OAuth2 授權流程產生 `~/.hermes/google_token.json`
4. 驗證：`python3 create_interview.py --help` 且無 auth 錯誤

## 驗證命令

```bash
# 檢查 token 是否存在
ls -la ~/.hermes/google_token.json && echo "TOKEN_EXISTS" || echo "TOKEN_MISSING"

# 測試腳本基本執行（排除 auth 錯誤）
python3 ~/.hermes/skills/school-interview-scheduler/scripts/create_interview.py --help
```

## 相關條目

- D3 exit 記錄：`trial-and-error/references/school-interview-scheduler-d3-exit-20260617.md`
- `school-interview-scheduler/SKILL.md` — 完整 workflow 文件
