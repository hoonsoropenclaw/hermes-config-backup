---
name: hr-document-workflow
description: "HR 文件工作流串接 skill — 整合 Linear（履歷 intake → 候選人追蹤）與 DOCX 產出（錄取通知書、聘用合約）。當用戶提到「履歷怎麼變候選人」「候選人追蹤 pipeline」「從 PDF 履歷到線上系統」「收到履歷要怎麼建立追蹤」時啟用。核心功能：將 himalaya（email intake）+ linear-hr-workflow（候選人追蹤）+ hr-document-automation（DOCX 產出）三者串成端到端 pipeline。"
version: 1.2.0
author: Hermes Agent (metacognitive-learner)
platforms: [linux]
metadata:
  hermes:
    tags: [hr, workflow, linear, resume, intake, pipeline, document, school, taiwan]
    triggers: [履歷, 候選人, intake, resume to linear, PDF 履歷, 從履歷到 Linear]
    user_type: school HR (high school administrative staff)
---

# HR Document Workflow — 端到端履歷→候選人→文件 Pipeline

## 核心定位

本 skill **不替代** `linear-hr-workflow` / `hr-document-automation` / `himalaya`，而是**串接**它們三者，填補「履歷 PDF 進來 → 候選人追蹤建立 → 錄取後文件產出」的端到端自動化缺口。

```
email 收到履歷 PDF (himalaya)
    ↓
PDF 文字提取 + LLM 結構化（系統 Python + pdfminer + MiniMax）
    ↓
Linear 候選人追蹤 issue（W2/W4 mutation）← linear-hr-workflow
    ↓
面試 → 錄取（HR 手動更新 Linear 狀態）
    ↓
hr-document-automation 產出 .docx（錄取通知書 / 聘用合約）
```

## 三個現有 Components 的角色

| Component | 職責 | 現有狀態 |
|-----------|------|---------|
| `himalaya` | 收取 email、下載附件（履歷 PDF） | ✅ 已啟用，binary 在 `~/bin/himalaya` |
| `linear-hr-workflow` | 候選人 GraphQL CRUD、Webhook 觸發 | ✅ 已啟用，SKILL.md v1.4.0 |
| `hr-document-automation` | DOCX 產出（錄取通知書、聘用合約） | ✅ 已啟用，SKILL.md v1.2.0，scripts/ 已驗證 |

## 觸發情境

| 情境 | 觸發的 Component | 自動化程度 |
|------|----------------|-----------|
| email 收到履歷 PDF | himalaya → resume-to-linear.py | 半自動（需手動給路徑） |
| 候選人狀態改為「錄取」 | hr-document-automation 直接觸發 | 手動觸發（HR 說「幫我產生」） |
| HR 說「幫我產生 OO 的錄取通知書」 | hr-document-automation 直接觸發 | 手動觸發 |

## If→Then 規則

**If** 用戶說「收到履歷 PDF」「有候選人寄來的履歷」「email 有附件要建立追蹤」
**Then** 執行 `resume-to-linear.py`（需先確認 Linear Team ID）

**If** 履歷是 `.doc` / `.docx` 格式（非 PDF）
**Then** 用 `python-docx` 讀取（系統 Python3.12 有）→ 再進 parse 流程

**If** 履歷是**掃描件**（PDF 無文字，`pdfminer` 提取 < 50 chars）
**Then** 使用 `pdftoppm` 轉 image → `tesseract` CLI 直接 OCR（subprocess 呼叫 `/usr/bin/tesseract`，**不用 `pytesseract` Python wrapper**）

```python
# ✅ 正確 — tesseract CLI subprocess
subprocess.run(['tesseract', f'{tmpdir}/page-1.ppm', 'stdout', '-l', 'chi_tra+eng'])

# ❌ 錯 — pytesseract wrapper 在 headless 環境容易失敗
import pytesseract
```

**If** 候選人狀態改為「錄取」（HR 在 Linear 手動更新）
**Then** 啟動 `hr-document-automation` 產出 .docx

**If** 用戶問「這三個怎麼串起來的」「想要全自動」
**Then** 說明完整架構，強調 Webhook 是關鍵——**沒有 webhook，錄取後的文件產出只能靠 HR 說「幫我產生」被動觸發**

## 執行命令

```bash
# 確認 Linear API 狀態
python3 -c "
import requests, os
key = os.getenv('LINEAR_API_KEY')
r = requests.post('https://api.linear.app/graphql',
    headers={'Authorization': key, 'Content-Type': 'application/json'},
    json={'query': '{ viewer { id email name } }'})
print('✅ Linear OK' if r.ok else f'❌ {r.text}')
"

# 產出 offer letter
python3.12 ~/.hermes/skills/hr-document-automation/scripts/generate_offer_letter.py \
    "王小明" "代理數學教師" "45000" "2026-08-01" "台北市立第一高級中學" /tmp/offer.docx

# 產出聘用合約（代理教師）
python3.12 ~/.hermes/skills/hr-document-automation/scripts/generate_contract_substitute.py \
    "王小明" "數學" "800" "留職停薪" "2026-08-01~2027-07-31" "台北市立第一高級中學" /tmp/contract.docx
```

## 依賴矩陣

| 依賴 | 狀態 | 備註 |
|------|------|------|
| `linear-hr-workflow` | ✅ | SKILL.md v1.4.0 |
| `hr-document-automation` | ✅ | SKILL.md v1.2.0，scripts/ 已驗證 |
| `himalaya` | ✅ | `~/bin/himalaya` v1.2.0 |
| python-docx (python3.12) | ✅ | `/usr/lib/python3.12/site-packages` |
| `pdfminer.six` | ✅ | 已安裝（python3.12） |
| `tesseract` OCR | ✅ | `/usr/bin/tesseract` 5.3.4 |
| `pdftoppm` (poppler) | ✅ | PDF → image conversion for OCR |

## D3 Exit 驗證（2026-06-18 — Cycle 完成）

`hr-document-workflow` SKILL.md 已建立，version 1.1.0。整合狀態：
- `linear-hr-workflow` → ✅ GraphQL API 串接正常
- `hr-document-automation` → ✅ scripts/ 已驗證（python3.12 + python-docx）
- ✅ **新增**：`resume-to-linear.py` 已建立（scripts/ 目錄，2026-06-18 15:50 mtime）

### resume-to-linear.py 功能驗證

```bash
$ python3.12 ~/.hermes/skills/hr-document-workflow/scripts/resume-to-linear.py --help
✅ --dry-run / --force-ocr / <resume_pdf> 全參數存在

$ python3.12 ~/.hermes/skills/hr-document-workflow/scripts/resume-to-linear.py <pdf> --dry-run
✅ 從真實 PDF 成功 extract text（10804 chars），parse 邏輯正常
✅ OCR fallback 邏輯正確（pdftoppm + tesseract）
✅ Linear GraphQL mutation 建構正確（dry-run 模式）
```

**驗證命令**：
```bash
stat -c '%y' ~/.hermes/skills/hr-document-workflow/scripts/resume-to-linear.py
# → 2026-06-18 15:50:XX.000000000 +0800
```
