# Vercel 部署調試參考

## 快速診斷：環境變數狀態測試端點

當 API 返回 `FUNCTION_INVOCATION_FAILED` 時，先部署這個端點確認環境變數：

```javascript
// api/test.js
module.exports = async (req, res) => {
  return res.status(200).json({
    env: {
      SUPABASE_URL: !!process.env.SUPABASE_URL,
      SUPABASE_SERVICE_ROLE_KEY: !!process.env.SUPABASE_SERVICE_ROLE_KEY,
      AGENT_API_KEY: !!process.env.AGENT_API_KEY,
    },
    timestamp: new Date().toISOString()
  })
}
```

部署後：
```bash
curl -s https://<url>/api/test
```

預期輸出：
```json
{"env":{"SUPABASE_URL":true,"SUPABASE_SERVICE_ROLE_KEY":true,"AGENT_API_KEY":true},"timestamp":"..."}
```

如果某個變數是 `false`，代表那個變數沒有正確設定或還沒 Redeploy。

## 環境變數設定後必須 Redeploy

Vercel Dashboard 設定環境變數後，**不會自動套用到現有部署**。必須手動 Redeploy：
1. Dashboard → Deployments
2. 選最新部署 → 三個點選單 → "Redeploy"

或 CLI：`vercel --token <token>`（直接部署 preview）

## Authentication Protection 阻擋

若訪問網站或 API 看到 Vercel 登入頁：
- Settings → Protection → Authentication → 設為 **Public**

## Vercel CLI Token 失效

症狀：`vercel --token <token>` → `The token provided via --token argument is not valid`

解決：產生新 token（格式：`vcp_` 開頭）
https://vercel.com/account/tokens → Create Token

## Supabase 環境變數參考（Hermes Portal）

| 變數名 | 格式 | 說明 |
|--------|------|------|
| `SUPABASE_URL` | `https://<ref>.supabase.co` | 專案 URL（非 REST URL） |
| `SUPABASE_SERVICE_ROLE_KEY` | `sb_secret_...` | Service role key（非 anon key） |
| `AGENT_API_KEY` | `hms_...` | Agent 認證用 |

**確認方法**：在 `.env.local` 確認有正確值後，確認 Vercel Dashboard 的名稱完全一致。