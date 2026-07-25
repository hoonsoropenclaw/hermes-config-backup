# hermes-portal 401 排查記錄（2026-06-04）

## 背景
hermes-portal（評價網站）部署在 Vercel，POST /api/works 持續 401，GET /api/works 200。

## 環境變數對照

| 變數 | 本機 (.env.local) | Vercel |
|------|------------------|--------|
| `AGENT_API_KEY` | `0770415` | `0770415`（已同步） |
| `SUPABASE_URL` | `https://nhjyucwvqdkihklbaleo.supabase.co` | （已同步） |
| `SUPABASE_SERVICE_ROLE_KEY` | （已更新） | （已同步） |

## 已嘗試的修復方式（全部無效）

1. 刪除 / 重建環境變數（手動 Add New，取消 Sensitive）
2. Import .env.local 上傳
3. 多次 Redeploy（deployment 狀態：Ready）
4. 確認無重複的 AGENT_API_KEY row（確認：無重複）
5. 取消 / 勾選 Sensitive 選項
6. Scope 設為 Production and Preview

## 關鍵發現

### 發現 1：auth 邏輯是嚴格比對
```javascript
// api/works.js 中的 authenticate 函數
if (!key || key !== process.env.AGENT_API_KEY) {
  return res.status(401).json(...)
}
```
如果 Vercel runtime 中 `process.env.AGENT_API_KEY` 為 `undefined`，則任何 key 都 401。

### 發現 2：Vercel Import .env.local 可能無效
用 Import .env.local 方式上傳，Vercel 可能無法正確將檔案內容轉換為 Runtime 環境變數。

### 發現 3：OCR 可用於截圖文字提取
在 Linux 環境下可用 tesseract 讀取截圖：
```bash
tesseract /path/to/image.png stdout --psm 6
```

## 待驗證

- Vercel 上的 AGENT_API_KEY 在 runtime 階段是否真的被吃到
- 建議：砍掉所有 env vars，用純手動一字一字輸入（不 Import），然後 Redeploy
- 建議：用 local Node.js 直接測試 auth 邏輯（不經過 Vercel）

## API 端點
- Production URL: `https://hermes-portal-akqkd6vpj-hoonsors-projects.vercel.app/api/works`
- POST 需要 Header: `x-agent-key: <AGENT_API_KEY>`
- 測試 key: `0770415`