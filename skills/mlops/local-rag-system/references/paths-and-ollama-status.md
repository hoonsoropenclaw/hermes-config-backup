# RAG 系統路徑速查（2026-05-31）

## 主要路徑

| 項目 | 路徑 |
|------|------|
| RAG 根目錄 | `~/.hermes/rag/` |
| 主程式 | `~/.hermes/rag/rag_system/main.py` |
| 批量匯入腳本 | `~/.hermes/rag/rag_system/obsidian_bulk_import_sync.py` |
| 向量資料庫 | `~/.hermes/rag/chroma_db/` |
| 測試文件 | `~/.hermes/rag/test_docs/` |
| 原始路徑（已移植） | `~/.openclaw/workspace/llm/` |

## Obsidian Vaults

| Vault | 路徑 | 狀態 |
|-------|------|------|
| 主要 Vault | `/home/hoonsoropenclaw/.openclaw/workspace/MainComputer/Hoonsor` | ✅ 已索引（282 文件，3212 embeddings） |
| YouTube 學習 | `~/AutoLearningKnowledge/youtube/` | 🔲 待建 RAG |

## Ollama 服務狀態檢查

```bash
# 服務是否運行
ps aux | grep ollama | grep -v grep

# Ollama PID（2026-05-31）
# PID: 2801371

# 測試 API
curl http://localhost:11434/api/version

# 列出已安裝模型
ollama list
```

## 執行命令速查

```bash
# 查詢（記得用 python3.12）
/usr/bin/python3.12 ~/.hermes/rag/rag_system/main.py query "問題" --top-k 5

# 列出文件
/usr/bin/python3.12 ~/.hermes/rag/rag_system/main.py list

# 新增文件
/usr/bin/python3.12 ~/.hermes/rag/rag_system/main.py add /path/to/file.txt
```

## Python 環境

| 解釋器 | 路徑 | 版本 | 用途 |
|--------|------|------|------|
| Hermes venv python3 | `~/.hermes/hermes-agent/venv/bin/python3` | 3.11.15 | Hermes 主程式 |
| 系統 python3.12 | `/usr/bin/python3.12` | 3.12.3 | RAG 腳本執行 |

**重要**：RAG 腳本必須用 `/usr/bin/python3.12`，不能用 `python3`（會 ModuleNotFoundError）。
