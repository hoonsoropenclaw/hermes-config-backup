# CAMFOX 環境變數設定參考

## 核心環境變數

| 變數 | 預設值 | 說明 |
|------|--------|------|
| `CAMFOX_URL` | `http://localhost:9377` | Camofox REST API 端點 |
| `CAMFOX_API_KEY` | （無） | 生產環境認證用 key；本機開發可設 `NODE_ENV=development` 繞過 |
| `CAMOUFOX_EXECUTABLE` | （使用內建） | 外部執行檔路徑；設定後 npm install 和啟動時跳過下載 |
| `NODE_ENV` | production | 設為 `development` 可跳過本機 CAMFOX_API_KEY 驗證 |

## 設定位置

所有赫米斯相關環境變數統一寫入 `~/.hermes/.env`（不是 `~/.openclaw/`）。

```bash
# ~/.hermes/.env
CAMFOX_URL=http://localhost:9377
CAMFOX_API_KEY=your_api_key_here
```

## 健康檢查

```bash
# 檢查 Camofox 是否正常運行
curl http://localhost:9377/health

# 預期輸出：
# {"ok":true,"running":true,"browserConnected":true,"browserRunning":true}
```

## 常見錯誤

| 錯誤 | 原因 | 解法 |
|------|------|------|
| `401 Unauthorized` | 本機未設 `NODE_ENV=development` 且無 API key | 啟動時加 `-e NODE_ENV=development` 或設定 `CAMFOX_API_KEY` |
| `Connection refused` | Camofox container 未運行 | `docker ps \| grep camofox` 確認 container 存在 |
| `CAMFOX_URL` vs `CAMOFOX_URL` | 變數名拼字錯誤 | 正確名稱是 `CAMFOX_URL`（FOX 非 FO） |

## 與 Hermes Agent 整合

Hermes Agent 的瀏覽器工具透過 `CAMFOX_URL` 連線到 Camofox REST API。設定正確後，browser tools 自動使用 Camofox 而非其他瀏覽器後端。

**驗證流程**：
1. 啟動 Camofox：`cd ~/camofox-browser && make up`
2. 檢查健康：`curl http://localhost:9377/health`
3. 在赫米斯中使用 browser tools 操作頁面