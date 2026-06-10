---
name: obsidian
description: Read, search, create, and edit notes in the Obsidian vault.
platforms: [linux, macos, windows]
version: 1.1
last_updated: 2026-06-07
---

# Obsidian Vault

Use this skill for filesystem-first Obsidian vault work: reading notes, listing notes, searching note files, creating notes, appending content, and adding wikilinks.

## Vault path

Use a known or resolved vault path before calling file tools.

The documented vault-path convention is the `OBSIDIAN_VAULT_PATH` environment variable, for example from `~/.hermes/.env`. If it is unset, use `~/Documents/Obsidian Vault`.

File tools do not expand shell variables. Do not pass paths containing `$OBSIDIAN_VAULT_PATH` to `read_file`, `write_file`, `patch`, or `search_files`; resolve the vault path first and pass a concrete absolute path. Vault paths may contain spaces, which is another reason to prefer file tools over shell commands.

If the vault path is unknown, `terminal` is acceptable for resolving `OBSIDIAN_VAULT_PATH` or checking whether the fallback path exists. Once the path is known, switch back to file tools.

### ⚠️ Vault 路徑 3 個選擇（按優先序）

赫米斯在 N100 上有三個**合法**的 Obsidian vault 路徑，**根據任務性質**挑一個：

1. **`~/Documents/Obsidian Vault`**（**最常用**）— 使用者的「個人 / 通用」 vault
2. **`~/.openclaw/workspace/MainComputer/Hoonsor`**（拉斐爾的 vault，已建 RAG 索引）— 拉斐爾代理的 vault，**不要亂寫**（除非使用者明確說要寫這裡）
3. **`~/AutoLearningKnowledge/<topic>/<date>/`**（2026-06-07 新增工作流）— **學習型內容專用 vault**（YouTube 摘要、課程筆記、教科書摘錄）

#### 自動學習 vault 的命名規則（2026-06-07 從 YouTube digest 工作流建立）

```
~/AutoLearningKnowledge/
├── youtube/
│   ├── 2026-06-07/         ← 今天的 YouTube 訂閱 digest
│   │   ├── 00-index.md
│   │   ├── 00-mindmap.md
│   │   ├── <Channel>__<title>.md
│   │   └── README.md
│   ├── 2026-06-08/         ← 明天的
│   └── ...
├── course/                  ← 課程筆記
│   └── <date>-<course-name>/
└── textbook/                ← 教科書摘錄
    └── <date>-<book-chapter>/
```

**為什麼**：
- 每次新主題建**日期子資料夾**（避免 dump 在同一層難找）
- **topic 子分類**（youtube / course / textbook）比純日期好讀
- 跟 RAG 索引友好（`obsidian_bulk_import_sync.py` 會自動撈）

**預防**：
- **不要**把每天的 YouTube digest 全部 dump 在 `~/AutoLearningKnowledge/youtube/` 根目錄（會爆炸）
- **不要**假設 vault 已經建好 — 先用 `terminal` 檢查 `ls ~/AutoLearningKnowledge/<topic>/` 確認
- 寫新資料夾前用 `Path.mkdir(parents=True, exist_ok=True)` 確保上層路徑存在

---

## Read a note

Use `read_file` with the resolved absolute path to the note. Prefer this over `cat` because it provides line numbers and pagination.

## List notes

Use `search_files` with `target: "files"` and the resolved vault path. Prefer this over `find` or `ls`.

- To list all markdown notes, use `pattern: "*.md"` under the vault path.
- To list a subfolder, search under that subfolder's absolute path.

## Search

Use `search_files` for both filename and content searches. Prefer this over `grep`, `find`, or `ls`.

- For filenames, use `search_files` with `target: "files"` and a filename `pattern`.
- For note contents, use `search_files` with `target: "content"`, the content regex as `pattern`, and `file_glob: "*.md"` when you want to restrict matches to markdown notes.

## Create a note

Use `write_file` with the resolved absolute path and the full markdown content. Prefer this over shell heredocs or `echo` because it avoids shell quoting issues and returns structured results.

## Append to a note

Prefer a native file-tool workflow when it is not awkward:

- Read the target note with `read_file`.
- Use `patch` for an anchored append when there is stable context, such as adding a section after an existing heading or appending before a known trailing block.
- Use `write_file` when rewriting the whole note is clearer than constructing a fragile patch.

For an anchored append with `patch`, replace the anchor with the anchor plus the new content.

For a simple append with no stable context, `terminal` is acceptable if it is the clearest safe option.

## Targeted edits

Use `patch` for focused note changes when the current content gives you stable context. Prefer this over shell text rewriting.

## Wikilinks

Obsidian links notes with `[[Note Name]]` syntax. When creating notes, use these to link related content.

## 跟其他系統的整合

- **RAG 索引**：寫完筆記後跑 `/usr/bin/python3.12 ~/.hermes/rag/rag_system/main.py add <file>` 加入向量資料庫。**注意陷阱**：見 `local-rag-system` skill 的「for 迴圈 + 2>/dev/null 會吞掉路徑錯誤」章節。
- **Mermaid 心智圖**：Obsidian 內建支援 Mermaid（` ```mermaid ` code block）。產出心智圖時用此語法比 Graphviz 簡單、跨平台。
- **NotebookLM 上傳**：`00-index.md` 設計成可以直接複製貼到 NotebookLM（每個影片一個段落、有完整 metadata）。
