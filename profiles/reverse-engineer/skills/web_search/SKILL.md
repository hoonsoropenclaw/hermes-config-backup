---
name: web_search
description: "雙軌 Web 搜尋技能：Ollama Web Search（主） + Tavily（備）。當需要查詢網路資訊、驗證最新消息、搜尋技術文件時使用。"
version: 1.0.1
date_added: "2026-02-27"
date_updated: "2026-05-30"
---

# 網路搜尋（雙軌備用系統）

## 雙軌架構

### 主用：Ollama Web Search API
- **Endpoint**: `POST https://ollama.com/api/web_search`（無 `/v1/` 前綴）
- **驗證**: 2026-05-30 ✅ 成功，3 results 回傳

### 備用：Tavily Search API
- **Endpoint**: `POST https://api.tavily.com/search`
- **額度**: 1000 searches/day（免費方案）
- **觸發條件**: Ollama 失敗、超時、或額度用盡

### 切換邏輯
```
1. 嘗試 Ollama Web Search API
   → 成功 → 回傳結果
   → 失敗（錯誤/超時）→ 自動切換 Tavily
2. Tavily Search API（備用）
   → 成功 → 回傳結果
   → 失敗 → 回傳錯誤
```

## 環境變數配置

Keys 統一寫入 `~/.hermes/.env`（赫米斯讀這個位置，不是 `~/.openclaw/...`）。

```bash
# 主用
OLLAMA_WEB_SEARCH_API_KEY=your_key_here

# 備用
TAVILY_API_KEY=your_key_here
TAVILY_API_ENDPOINT=https://api.tavily.com/search
```

## 驗證指令（2026-05-30 實測正常）

```bash
# Ollama Web Search（endpoint 無 /v1/ 前綴，否則 404）
curl -s -X POST "https://ollama.com/api/web_search" \
  -H "Content-Type: application/json" \
  -H "Authorization: Bearer $OLLAMA_WEB_SEARCH_API_KEY" \
  -d '{"query":"stock market today","max_results":3}'

# Tavily（當 Ollama 額度用盡時）
curl -s -X POST "https://api.tavily.com/search" \
  -H "Content-Type: application/json" \
  -d '{"query":"stock market today","max_results":3,"api_key":"'"$TAVILY_API_KEY"'"}'
```

## 輸出格式

### Ollama 格式
```json
[
  {"title": "標題", "url": "https://...", "description": "描述", "source": "來源"}
]
```

### Tavily 格式
```json
{
  "results": [
    {"title": "標題", "url": "https://...", "content": "內容片段"}
  ]
}
```

## 實用範例

### 基本搜尋函數（Bash）
```bash
search_web() {
    local query="$1"
    local max_results="${2:-5}"

    # 嘗試 Ollama
    local ollama_result=$(curl -s --max-time 30 \
        -X POST "https://ollama.com/api/web_search" \
        -H "Content-Type: application/json" \
        -H "Authorization: Bearer $OLLAMA_WEB_SEARCH_API_KEY" \
        -d "{\"query\": \"$query\", \"max_results\": $max_results}" 2>/dev/null)

    if [ $? -eq 0 ] && [ -n "$ollama_result" ]; then
        echo "$ollama_result"
        return 0
    fi

    # Ollama 失敗，切換 Tavily
    curl -s --max-time 30 \
        -X POST "https://api.tavily.com/search" \
        -H "Content-Type: application/json" \
        -d "{\"query\": \"$query\", \"max_results\": $max_results, \"api_key\": \"$TAVILY_API_KEY\"}"
}
```

### 在 Python 學習腳本中使用
```python
import json, subprocess, os

def search_web(query, max_results=5):
    # 嘗試 Ollama
    result = subprocess.run(
        ["curl", "-s", "--max-time", "30", "-X", "POST",
         "https://ollama.com/api/web_search",
         "-H", "Content-Type: application/json",
         "-H", f"Authorization: Bearer {os.environ['OLLAMA_WEB_SEARCH_API_KEY']}",
         "-d", json.dumps({"query": query, "max_results": max_results})],
        capture_output=True, text=True
    )
    if result.returncode == 0 and result.stdout.strip():
        return json.loads(result.stdout)

    # 備用 Tavily
    result = subprocess.run(
        ["curl", "-s", "--max-time", "30", "-X", "POST",
         "https://api.tavily.com/search",
         "-H", "Content-Type: application/json",
         "-d", json.dumps({"query": query, "max_results": max_results,
                           "api_key": os.environ["TAVILY_API_KEY"]})],
        capture_output=True, text=True
    )
    return json.loads(result.stdout) if result.returncode == 0 else {}
```

## 安全考量
- 所有網路操作 30 秒超時
- API Key 存在 `~/.hermes/.env`，不在程式碼中硬編碼
- Ollama endpoint 是 `ollama.com`（非 `api.ollama.com`）

## 已知陷阱（2026-05-30 更新）

| 陷阱 | 說明 |
|------|------|
| Twelve Data endpoint | 是 `price`，不是 `/v1/price` — 否則 404 |
| Ollama endpoint | 是 `ollama.com/api/web_search`，不是 `api.ollama.com` |
| YAML off 解析 | `hermes config set approvals.mode off` 會寫成布林 `false`，需用 `sed` 修正 |

## API 故障排除（2026-05-31 更新）

### Ollama Web Search API 返回 `unauthorized`

**跡象**：
- HTTP response: `{"error": "unauthorized"}`
- 可能原因：API key 過期、被撤銷、或達到額度限制

**處理順序**：
1. **檢查 key 是否仍有效**：`echo $OLLAMA_WEB_SEARCH_API_KEY | cut -c1-10`（應顯示非空字串）
2. **若 key 存在但仍 unauthorized**：key 可能已過期，切換 Tavily 作為主用
3. **Tavily 備用方案**：編輯 `~/.hermes/.env`，將 `TAVILY_API_KEY` 替換失效的 `OLLAMA_WEB_SEARCH_API_KEY`
4. **若兩個都失敗**：記錄錯誤，返回空結果，不阻斷主流程（使用 `set +e`）

⚠️ **不要將 API key 過期固化為「工具無法使用」的永久陳述**。這是環境/憑證問題，更換 key 即可恢復。

## 備用方案

當兩個 API 都失敗時：
1. 記錄錯誤到日誌
2. 返回空結果
3. 不阻斷主流程（使用 `set +e` 臨時禁用錯誤退出）
