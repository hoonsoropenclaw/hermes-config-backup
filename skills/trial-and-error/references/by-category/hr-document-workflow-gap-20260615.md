---

### hr-document-workflow gap — D3 EXIT (2026-06-18)

**原本 Gap**: 履歷 → 候選人 Linear issue 的 `resume-to-linear.py` script 從未建立（HR workflow 缺最後一環）

**D3 Exit (2026-06-18)**:
- ✅ `resume-to-linear.py` 已建立於 `~/.hermes/skills/hr-document-workflow/scripts/`
- ✅ mtime: `2026-06-18 15:50:58`（本次 cycle 實作）
- ✅ `hr-document-workflow` SKILL.md version 升至 1.2.0
- ✅ `python3.12 resume-to-linear.py <pdf> --dry-run` 實測成功（10804 chars extracted）
- ✅ 支援 OCR fallback（pdftoppm + tesseract for 掃描件）
- ✅ Linear GraphQL mutation 建構正確（dry-run 驗證）

**驗證命令**:
```bash
stat -c '%y' ~/.hermes/skills/hr-document-workflow/scripts/resume-to-linear.py
# → 2026-06-18 15:50:58.490923823 +0800
```

**預防**: SKILL.md 裡的 code snippets ≠ 可執行 script。D3 標準：必須是 `python3.12 <file.py>` 實際跑成功並附上 `stat` mtime。

**If→Then**: **If** SKILL.md 有 workflow 邏輯但 scripts/ 目錄是空的 **Then** 這是 D2 文件狀態，需建立對應 .py scripts 並驗證 exit code 0

**相關條目**: [[hermes-internal#hr-document-workflow 端到端完整鏈路]], [[hr-document-automation-d3-exit-20260618]]


**症狀**: 使用者（學校 HR）說「幫我約張三面試」「候選人沒收到邀請」→ 赫米斯沒有對應腳本，需要手動在 Google Calendar 建立 event

**根因**: `google-workspace` skill 覆蓋 Gmail 但沒有 Calendar/Meet 的腳本；`hr-document-workflow` skill 已補足「錄取後文件產出」；兩者之間的「面試安排 + 發送 Meet 邀請」是獨立缺口

**解法**: 
1. 新建 `school-interview-scheduler` skill（2026-06-16 完成，mtime 2026-06-16 04:20）
2. 核心腳本 `create_interview.py` — 使用 Google Calendar API v3 + `conferenceDataVersion=1` 建立 Meet URL，`sendUpdates="all"` 自動寄送邀請給候選人
3. 依賴 `google-workspace` skill 的 OAuth2 設定（`google_token.json`）或 Service Account + Domain-Wide Delegation

**預防**: 未來 HR 相關需求進來時，先檢查 `school-interview-scheduler` skill 是否存在，不重複 research

**驗證**:
```bash
ls -la ~/.hermes/skills/school-interview-scheduler/scripts/create_interview.py
python3 -m py_compile ~/.hermes/skills/school-interview-scheduler/scripts/create_interview.py
```

**If→Then**: **If** 使用者提到「面試邀請」「約面試」「Google Meet」但沒有 Calendar API 腳本 **Then** 啟用 `school-interview-scheduler` skill

**相關條目**: [[hermes-internal#hr-document-workflow 端到端完整鏈路]]

---

### hr-document-workflow gap — missing end-to-end candidate pipeline (2026-06-15)

**症狀**: 使用者提到「候選人」時，赫米斯需要履歷但沒有從 email 自動解析候選人資料的流程

**根因**: `himalaya`（email收取）、`linear-hr-workflow`（候選人追蹤）、`hr-document-workflow`（錄取文件產出）三者是斷裂的，沒有端到端 pipeline

**解法**: 新建 `hr-document-workflow` skill（2026-06-15 完成，mtime 2026-06-15 22:04），補足「履歷 → 候選人 record → 錄取文件產出」完整鏈路

**預防**: HR 工作流需求進來時，先確認 `himalaya` + `linear-hr-workflow` + `hr-document-workflow` + `school-interview-scheduler` 四個 skill 都已覆蓋

**驗證**:
```bash
ls -la ~/.hermes/skills/hr-document-workflow/SKILL.md
stat -c '%y' ~/.hermes/skills/hr-document-workflow/SKILL.md
```

**If→Then**: **If** 使用者提到「候選人」「履歷」「錄取通知」但沒有對應 workflow **Then** 啟用 `hr-document-workflow` skill

**相關條目**: [[hermes-internal#school-interview-scheduler gap — missing Calendar + Meet automation]]
