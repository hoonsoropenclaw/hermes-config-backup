# Linear API Key 缺失 — 2026-06-19 發現

## 症狀

`linear-hr-workflow` 的 W2/W4/W5/W9 任務執行時，Linear API 返回：
```
{"errors":[{"message":"Authentication required","statusCode":401}]}
```

## 根因

`LINEAR_API_KEY` 不在 `~/.hermes/.env`（該檔只有 MINIMAX_API_KEY），也不在 `~/.hermes/.env.local`。

`linear-hr-workflow` SKILL.md v1.4.0 說「存入 `~/.hermes/.env`」，但 `.env` 內的 key 全是 `#` 註解狀態（被 `***` mask 覆蓋）。

## 解法

1. 用戶在 `linear.app/settings/account/security` 建立 Personal API key
2. 寫入 `~/.hermes/.env.local`（LINEAR_API_KEY 不走 `***` mask）：
   ```
   LINEAR_API_KEY=lin_api_xxxxxxxxxxxx
   ```
3. 驗證：
   ```bash
   curl -s -X POST https://api.linear.app/graphql \
     -H "Content-Type: application/json" \
     -H "Authorization: $(grep LINEAR_API_KEY ~/.hermes/.env.local | cut -d= -f2)" \
     -d '{"query":"{ viewer { id name } }"}'
   ```
   期望：`{"data":{"viewer":{"id":"...","name":"..."}}}`

## 預防

- **不能用 `.env`**（LINEAR_API_KEY 會被 `***` mask 吃掉，變成無效 key）
- 正確位置：`~/.hermes/.env.local`
- SKILL.md 已更新（v1.4.1）加入 401 時的 If→Then 修正

## If→Then

**If** Linear API 返回 401 且 `grep LINEAR ~/.hermes/.env.local` 無輸出 **Then** key 未設定，請用戶到 `linear.app/settings/account/security` 建立並寫入 `.env.local`
