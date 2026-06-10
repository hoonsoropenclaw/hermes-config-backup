---
name: local-rag-system
description: 本地 RAG 文件檢索系統 — 在 N100 迷你電腦上使用 Ollama + ChromaDB 建構、移植、與維運。
triggers:
  - "架設 RAG"
  - "Ollama ChromaDB"
  - "遷移 RAG"
  - "Obsidian vault 索引"
  - "本地知識庫"
  - "embeddings 向量資料庫"
category: mlops
tags: [rag, local-llm, ollama, chromadb, embeddings, knowledge-base]
version: "1.1"
author: hermes
pinned: false
created: 2026-05-31
last_updated: 2026-06-07
---

# Local RAG System（本地 RAG 文件檢索系統）

## 📋 系統概述

在 N100 迷你電腦（無 GPU，純 CPU）上部署的本地 LLM + RAG 文件檢索系統。

### 硬體環境
- **主機**：N100 迷你電腦（4 核心）
- **RAM**：31GB（可用 27GB）
- **儲存**：231GB

### 已安裝模型
```
ollama list:
  - qwen2.5:1.5b              (LLM, 986MB)
  - herald/dmeta-embedding-zh  (中文 Embedding, 204MB)
  - nomic-embed-text          (備用 Embedding, 274MB)
```

---

## 🗂️ 目錄結構

```
~/.hermes/rag/
├── rag_system/
│   ├── main.py                      # 主程式
│   ├── obsidian_bulk_import_sync.py  # Obsidian Vault 批量掃描腳本
│   └── test.py                       # 測試腳本
├── chroma_db/                        # 向量資料庫（chroma.sqlite3 + embeddings）
├── test_docs/                        # 測試文件
├── monitor_import.py                # Import 監控腳本
└── check_import.sh                  # 狀態檢查 Shell 腳本
```

---

## 🚀 核心操作

### 查詢知識庫
```bash
/usr/bin/python3.12 ~/.hermes/rag/rag_system/main.py query "你的問題" --top-k 5
```

### 新增文件
```bash
/usr/bin/python3.12 ~/.hermes/rag/rag_system/main.py add /path/to/file.txt
```

### 列出已索引文件
```bash
/usr/bin/python3.12 ~/.hermes/rag/rag_system/main.py list
```

### 刪除文件
```bash
/usr/bin/python3.12 ~/.hermes/rag/rag_system/main.py delete doc_id
```

### 重置知識庫
```bash
/usr/bin/python3.12 ~/.hermes/rag/rag_system/main.py reset
```

### 批量匯入一整個目錄（2026-06-07 新增工作流）
```bash
# 用 for 迴圈 add 全部 .md（**不要**用 `>/dev/null 2>&1` 隱藏錯誤！見下方防禦性陷阱）
for f in /path/to/vault/*.md; do
    /usr/bin/python3.12 ~/.hermes/rag/rag_system/main.py add "$f"
done

# 然後用 list 確認
/usr/bin/python3.12 ~/.hermes/rag/rag_system/main.py list
```

**Obsidian Vault 路徑**（2026-06-07 更新）：
- 預設 vault（已建索引）：`/home/hoonsoropenclaw/.openclaw/workspace/MainComputer/Hoonsor`
- YouTube 學習用 vault：`~/AutoLearningKnowledge/youtube/`（**每次新主題建子資料夾**：`~/AutoLearningKnowledge/youtube/2026-06-07/`、`2026-06-08/` 等）
- 通用學習 vault：`~/AutoLearningKnowledge/<topic>/<date>/` 命名規則（從 2026-06-07 YouTube digest 開始建立）

---

## ⚠️ 關鍵陷阱：Python 解釋器

### 問題
Hermes Agent 的 `python3` 是 venv 中的 **Python 3.11**，但 `chromadb`、`langchain` 等套件安裝在系統 **Python 3.12**（`/usr/bin/python3.12`）。

直接用 `python3` 執行會得到：
```
ModuleNotFoundError: No module named 'chromadb'
```

### 解決方式
**所有 RAG 相關腳本都必須用 `/usr/bin/python3.12` 執行**，而非 `python3`。

```bash
# ✅ 正確
/usr/bin/python3.12 ~/.hermes/rag/rag_system/main.py list

# ❌ 錯誤（ModuleNotFoundError）
python3 ~/.hermes/rag/rag_system/main.py list
```

---

## ⚠️ 防禦性陷阱：for 迴圈 + `2>/dev/null` 會吞掉路徑錯誤（2026-06-07 學到）

### 問題
批次跑 RAG `add` 指令時，**很多人會這樣寫**：
```bash
for f in /path/*.md; do
    /usr/bin/python3.12 ~/.hermes/rag/rag_system/main.py add "$f" > /dev/null 2>&1
done
# 然後看 exit code 0 就以為「成功」
```

**慘案**：路徑打錯（例：`hoonsorpenclaw` vs `hoonsoropenclaw` 一字之差）時，`/usr/bin/python3.12` 找不到檔案會**直接報 "No such file" 到 stderr**，但被 `2>/dev/null` 吞掉 → 整個 for 迴圈跑 27 個檔案**全部失敗**，但 `exit code 0`（bash 預設的 command not found 在子 shell 仍會傳 0 嗎？**要看 subshell 模式**）。

### 解法
**任何批次操作一定要 verify**：
```bash
COUNT=0
FAILED=0
FAILED_FILES=()
for f in /path/*.md; do
    if /usr/bin/python3.12 ~/.hermes/rag/rag_system/main.py add "$f" > /dev/null 2>&1; then
        COUNT=$((COUNT + 1))
    else
        FAILED=$((FAILED + 1))
        FAILED_FILES+=("$f")
    fi
done
echo "✅ 成功: $COUNT / 失敗: $FAILED"
[ $FAILED -gt 0 ] && printf '  ❌ %s\n' "${FAILED_FILES[@]}"
```

或者**完全不要** redirect，先看到錯誤再說：
```bash
for f in /path/*.md; do
    echo "→ $f"
    /usr/bin/python3.12 ~/.hermes/rag/rag_system/main.py add "$f"
done
```

**預防**：
- 批次腳本最後**永遠**加一個 `verify count`（用 `list` 或 `du` 確認真的有寫入）
- 路徑很長時**用 `ls` 或 `echo` 先驗證**再 for
- 路徑含特殊字元（中文、emoji）時用 `search_files` 而非 `find` / `for`

詳見 `trial-and-error/references/by-category/bash-defensive-patterns.md` 的「for+2>/dev/null 語法錯」條目。

---

## 🔄 從 OpenClaw 移植到 Hermes 的流程

當需要將 RAG 系統從 `~/.openclaw/workspace/llm/` 移植到 `~/.hermes/rag/` 時：

### Step 1：複製檔案
```bash
mkdir -p ~/.hermes/rag/{rag_system,chroma_db,test_docs}

# 複製腳本
cp ~/.openclaw/workspace/llm/rag_system/main.py ~/.hermes/rag/rag_system/
cp ~/.openclaw/workspace/llm/rag_system/obsidian_bulk_import_sync.py ~/.hermes/rag/rag_system/
cp ~/.openclaw/workspace/llm/rag_system/test.py ~/.hermes/rag/rag_system/
cp ~/.openclaw/workspace/llm/monitor_import.py ~/.hermes/rag/
cp ~/.openclaw/workspace/llm/check_import.sh ~/.hermes/rag/

# 複製測試文件
cp ~/.openclaw/workspace/llm/test_docs/*.txt ~/.hermes/rag/test_docs/

# 複製向量資料庫
cp -r ~/.openclaw/workspace/llm/chroma_db ~/.hermes/rag/
```

### Step 2：更新所有腳本中的路徑
需要修改的檔案和路徑：

| 檔案 | 舊路徑 | 新路徑 |
|------|--------|--------|
| `main.py` | `~/.openclaw/workspace/llm/chroma_db` | `~/.hermes/rag/chroma_db` |
| `test.py` | `sys.path 指向舊目錄` | `sys.path 指向新目錄` |
| `test.py` | `~/.openclaw/workspace/llm/test_docs/` | `~/.hermes/rag/test_docs/` |
| `obsidian_bulk_import_sync.py` | `~/.openclaw/workspace/llm/chroma_db` | `~/.hermes/rag/chroma_db` |
| `monitor_import.py` | `~/.openclaw/workspace/llm/chroma_db/chroma.sqlite3` | `~/.hermes/rag/chroma_db/chroma.sqlite3` |
| `monitor_import.py` | `~/.openclaw/workspace/llm/.import_state` | `~/.hermes/rag/.import_state` |
| `check_import.sh` | `~/.openclaw/workspace/llm/chroma_db/` | `~/.hermes/rag/chroma_db/` |
| `check_import.sh` | `~/.openclaw/workspace/llm/.import_state` | `~/.hermes/rag/.import_state` |
| `check_import.sh` | `~/.openclaw/workspace/llm/.import_log` | `~/.hermes/rag/.import_log` |

### Step 3：驗證
```bash
# 確認向量資料庫可讀取
/usr/bin/python3.12 ~/.hermes/rag/rag_system/main.py list

# 測試新增文件
/usr/bin/python3.12 ~/.hermes/rag/rag_system/main.py add ~/.hermes/rag/test_docs/about.txt

# 測試查詢
/usr/bin/python3.12 ~/.hermes/rag/rag_system/main.py query "測試問題" --top-k 3
```

---

## 🔧 依賴安裝

```bash
# 安裝在系統 Python 3.12（非 venv）
/usr/bin/python3.12 -m pip install chromadb langchain langchain-community --break-system-packages
```

---

## 📊 效能數據

| 指標 | 數值 |
|------|------|
| 模型載入時間 | ~30 秒 |
| 向量化速度 | ~0.5 秒/chunk |
| 查詢回應時間 | ~3-5 秒 |
| 記憶體使用 | ~2GB（模型 + ChromaDB） |

---

## 📎 參數設定

| 參數 | 預設值 |
|------|--------|
| Chunk 大小 | 500 字元 |
| Chunk 重疊 | 50 字元 |
| Top-K | 5 個相關區塊 |
| Temperature | 0.3（穩定輸出） |
| LLM Model | qwen2.5:1.5b |
| Embedding Model | herald/dmeta-embedding-zh |

---

## 🔍 故障排除

### Q1：Ollama 服務未運行
```bash
# 檢查
ps aux | grep ollama | grep -v grep

# 啟動
ollama serve &

# 確認
curl http://localhost:11434/api/version
```

### Q2：ModuleNotFoundError: chromadb
→ 見上方「⚠️ Python 解釋器」章節。用 `/usr/bin/python3.12` 而非 `python3`。

### Q3：記憶體不足
N100 有 31GB RAM，目前足夠。如遇問題：
- 減少 Top-K 值
- 增加 swap

### Q4：ChromaDB 錯誤
```bash
# 重置知識庫
/usr/bin/python3.12 ~/.hermes/rag/rag_system/main.py reset
```

### Q5：批次 add 看起來都成功但 list 沒新文件（2026-06-07 新增）
**症狀**：for 迴圈跑 27 個檔案都「成功」（exit 0），但 `list` 沒新增任何東西
**根因**：通常是 (a) 路徑打錯被 `>/dev/null 2>&1` 吞掉、或 (b) `add` 的子 process 沒真的把 stdout/stderr 寫回
**解法**：
1. **不要**用 `>/dev/null 2>&1` 隱藏輸出，先看完整 log
2. 加 `COUNT=0; FAILED=0; FAILED_FILES=()` 收集失敗清單
3. 最後跑 `list` 確認文件數真的有增加
4. 跑一個小查詢確認 chunks 真的被索引（不是只有 doc_id 沒 chunk）
