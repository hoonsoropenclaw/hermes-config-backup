# HR Automation — D2 Trap Discovery & Gap Analysis (2026-07-11)

## 發現：D2 迴圈陷阱

Cycle 480（2026-07-11）發現 `hr-automation-workflow` 存在 D2 迴圈陷阱：

### 問題
| 項目 | 狀態 |
|------|------|
| SKILL.md 嵌入式代碼 | ✅ 完整（resume_parser.py、interview_generator.py、onboarding_tracker.py） |
| scripts/ 目錄 | ❌ 為空（無實際可執行檔案） |
| school-interview-scheduler | ❌ 目錄不存在 |
| hr-document-workflow | ❌ 目錄不存在 |
| linear skill scripts/linear_api.py | ✅ 功能正常（--help exit 0） |

### 根本原因
skill 作者將完整 Python 代碼寫入 SKILL.md（作為文件內容），但未在 `scripts/` 建立實際檔案。這形成 D2 陷阱：知識存在但執行環境不存在，導致「看起來已完成，實際上無法執行」。

### 修復動作（D3）
從 SKILL.md 嵌入式代碼區塊手動建立 scripts/ 檔案。

---

## 依賴缺口

| Skill | 狀態 | 需建立 |
|-------|------|--------|
| school-interview-scheduler | ❌ 不存在 | ✅ |
| hr-document-workflow | ❌ 不存在 | ✅ |
| linear scripts/linear_api.py | ✅ 正常 | — |

---

## 學校 HR 核心痛點

**代理教師 24-48 小時緊急填補**是學校 HR 最高優先自動化需求，企業 ATS 不適用此場景。

---

## Linear API

LINEAR_API_KEY 未設定時直接 exit code 2，需至 https://linear.app/settings/api 建立。
