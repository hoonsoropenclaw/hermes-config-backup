---
# HR Document Workflow Gap — 端到端履歷→候選人→文件 Pipeline 缺口識別與填補

## 缺口識別（2026-06-15）

**問題**: 三個現有 skill (`himalaya` + `linear-hr-workflow` + `hr-document-automation`) 各自完整，但沒有人負責串接它們。從履歷 PDF 到候選人追蹤到錄取文件，沒有一個 skill 涵蓋端到端流程。

**D2 迴圈陷阱**（已連續 2+ cycle 識別同一缺口）:
- 前兩個 cycle 都識別了「hr-document-workflow gap」
- 前兩個 cycle 都寫了「建議新建 hr-document-workflow skill」
- 但 SKILL.md 從未建立

**根因**: 識別（Phase 1）→ 研究（Phase 3）→ 記錄（Phase 4）是閉環，但缺少「真的動手做」的強制環節。「提出建議」等於「彌補了」——這是認知偏差。

## D3 實作終結（2026-06-15 22:04）

**動作**: 建立 `~/.hermes/skills/hr-document-workflow/SKILL.md`（125 行，mtime 2026-06-15 22:04:31）

**驗證**:
```bash
stat ~/.hermes/skills/hr-document-workflow/SKILL.md
# Modify: 2026-06-15 22:04:31.336023031 +0800
```

**L3 教訓**: 同一缺口連續 2 個 cycle 被識別為「優先缺口」時，第 3 個 cycle 必須升級到 D3（實作型），具體動作：先 install script 或建立 SKILL.md，再迭代功能。不要再次 research → 浪費 40+ 分鐘在同樣的資料上。

## 三個現有 Components

| Component | 職責 | 現有狀態 |
|-----------|------|---------|
| `himalaya` | 收取 email、下載附件（履歷 PDF） | ✅ 已啟用 |
| `linear-hr-workflow` | 候選人 GraphQL CRUD、Webhook 觸發 | ✅ W9 履歷 intake 完整 |
| `hr-document-automation` | DOCX 產出（錄取通知書、聘用合約） | ✅ `generate_offer_letter()` 可用 |

## 端到端流程

```
email 收到履歷 PDF (himalaya)
    ↓
PDF 文字提取 + LLM 結構化（系統 Python + pdfminer + MiniMax）
    ↓
Linear 候選人追蹤 issue（W2/W4 mutation）← linear-hr-workflow
    ↓
面試 → 錄取（HR 手動更新 Linear 狀態）
    ↓
Webhook 觸發自動產出檔案（Pipedream）← hr-document-automation
```

## 仍存在的缺口

1. **Pipedream webhook 尚未設定**：候選人狀態變「錄取」後的文件產出仍需 HR 口頭觸發
2. **OCR 準確度有限**：手寫掃描件建議人工校對關鍵欄位
3. **Batch 履歷處理**：暑期大量招聘建議用 `linear-hr-workflow` W4 `issueBatchCreate` 批次

## If→Then

**If** 用戶說「收到履歷 PDF」「有候選人寄來的履歷」「email 有附件要建立追蹤」
**Then** 執行 `resume-to-linear.py`（`linear-hr-workflow` W9 已實作）→ 從 PDF 提取文字 → MiniMax 結構化 → Linear issue

**If** 履歷是**掃描件**（PDF 無文字）
**Then** 使用 `pytesseract` OCR（系統 Python 有 `/usr/bin/tesseract`）→ 再進 parse 流程

**If** 同一缺口被連續 2 個 cycle 識別
**Then** 第 3 個 cycle 必須 D3 實作（建立 SKILL.md / install script），不再 research
