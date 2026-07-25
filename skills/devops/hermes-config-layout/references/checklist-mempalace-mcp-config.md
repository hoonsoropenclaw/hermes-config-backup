# MemPalace MCP Server 配置參考

## 語法格式（關鍵教訓）

**正確格式** — `args` 必須是 YAML list：
```yaml
mcp_servers:
  mempalace:
    command: python3
    args:
      - -m
      - mempalace.mcp_server
    enabled: true
```

**錯誤格式** — args 是 JSON 字串（導致 `Input should be a valid list, input_value='["-m",...]'` 錯誤）：
```yaml
args: '["-m", "mempalace.mcp_server"]'   # ❌ 字串，不是 list
```

## 新增 MCP Server 步驟

```bash
# 1. 測試 server 是否正常運行（直接呼叫）
echo '{"jsonrpc":"2.0","id":1,"method":"tools/list","params":{}}' | python3 -m mempalace.mcp_server

# 2. 嘗試透過 hermes mcp add 新增（互動模式）
hermes mcp add mempalace --command python3 --args="-m,mempalace.mcp_server"
# 會失敗但會建立設定，之後手動修正 config.yaml

# 3. 手動編輯 config.yaml 修正 args 格式為 list
```

## MemPalace 工具列表（29 tools）

| 工具 | 用途 |
|------|------|
| `mempalace_search` | **語意搜尋** — 主要備援工具 |
| `mempalace_kg_query` | 知識圖譜查詢 |
| `mempalace_kg_add` | 新增知識圖譜事實 |
| `mempalace_kg_stats` | 知識圖譜統計 |
| `mempalace_graph_stats` | 圖譜概覽 |
| `mempalace_diary_read` | 讀取代理日記 |
| `mempalace_diary_write` | 寫入代理日記 |
| `mempalace_list_wings` | 列出所有翅膀 |
| `mempalace_list_rooms` | 列出房間 |
| `mempalace_list_drawers` | 列出抽屜 |
| `mempalace_add_drawer` | 新增抽屜 |
| `mempalace_get_drawer` | 取得抽屜內容 |
| `mempalace_delete_drawer` | 刪除抽屜 |
| `mempalace_traverse` | 穿越房間圖譜 |
| `mempalace_find_tunnels` | 找到跨翅膀隧道 |
| `mempalace_follow_tunnels` | 跟隨隧道 |
| `mempalace_create_tunnel` | 建立跨翅膀隧道 |
| `mempalace_list_tunnels` | 列出隧道 |
| `mempalace_status` | Palace 狀態 |
| `mempalace_get_taxonomy` | 完整分類學 |
| `mempalace_get_aaak_spec` | AAAK 格式規格 |
| `mempalace_check_duplicate` | 檢查重複 |
| `mempalace_update_drawer` | 更新抽屜 |
| `mempalace_kg_invalidate` | 廢除知識事實 |
| `mempalace_kg_timeline` | 知識時間線 |
| `mempalace_delete_tunnel` | 刪除隧道 |
| `mempalace_hook_settings` | Hook 設定 |
| `mempalace_memories_filed_away` | 檢查checkpoint |
| `mempalace_reconnect` | 強制重新連線 |

## 測試指令

```bash
# 測試連線
hermes mcp test mempalace

# 測試搜尋（直接呼叫 MCP）
echo '{"jsonrpc":"2.0","id":2,"method":"tools/call","params":{"name":"mempalace_search","arguments":{"query":"測試關鍵字","limit":3}}}' | python3 -m mempalace.mcp_server 2>/dev/null | python3 -c "import sys,json; d=json.load(sys.stdin); print(json.dumps(d.get('result',{}), indent=2, ensure_ascii=False)[:1000])"
```

## 權限設定

```bash
# 啟用 MCP server
hermes config set mcp_servers.mempalace.enabled true

# 若 args 被寫成字串，手動修正為 list 格式
```

## 與 OpenClaw 的差異

| 項目 | OpenClaw | Hermes |
|------|----------|--------|
| 設定檔 | `~/.openclaw/openclaw.json` | `~/.hermes/config.yaml` |
| MCP 設定位置 | `mcp.servers` | `mcp_servers` |
| args 格式 | JSON array string | YAML list |
| 測試命令 | `openclaw mcp test mempalace` | `hermes mcp test mempalace` |