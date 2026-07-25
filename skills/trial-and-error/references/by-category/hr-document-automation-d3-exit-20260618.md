# hr-document-automation D3 Exit — 2026-06-18

## D2 迴圈陷阱：D2→D3 實作缺口

**症狀**: `hr-document-automation` SKILL.md 已有完整的 Python `generate_offer_letter()` 和 `generate_contract_substitute()` 函數，但：
- `python-docx` 在 system Python (3.11) 上**不存在**
- `minimax-docx` 依賴 `dotnet-sdk`，但主機**未安裝**
- SKILL.md 的「執行命令」段落**從來沒有被驗證過**

**根因**: D2 迴圈陷阱——識別缺口（cycle 1）→ 寫文件（cycle 2）→ 但文件只是 code snippets 而非實際可運作的 scripts，技能處於「看起來完整但無法觸發」的狀態。

**解法**: 
1. 確認 `python-docx` 存在於 `python3.12`（不是 `python3`）
2. 將 code snippets 重寫為獨立的、可執行的 scripts
3. 驗證：`python3.12 <script.py>` 實際產出 .docx 檔案

**預防**: 
- SKILL.md 裡的 code snippets ≠ 可執行 scripts
- **D3 驗證標準**：必須是 `python3.12 <file.py>` 實際跑成功，附上 `ls -la <output.docx>` 的 exit code 和 size

**If→Then**:
- **If** SKILL.md 有 `from docx import Document` 但從未建立 `.py` script
- **Then** 這是 D2 文件狀態，不是 D3 實作——需建立 scripts 並驗證
- **If** `python-docx` import 失敗時，先確認是 python3.11 vs python3.12 的路徑差異
- **Then** 用 `python3.12 -c "from docx import Document; print('OK')"` 確認無誤後再寫 wrapper script

---

## python-docx 路徑陷阱：system python3 vs python3.12

**症狀**: 
```
python3 -c "import docx"  → ModuleNotFoundError
python3.12 -c "import docx"  → OK
```

**根因**: 
- Hermes N100 系統 Python 是 3.11（`/usr/bin/python3`），`python-docx` 只安裝在 python3.12 的 site-packages (`/usr/lib/python3.12/site-packages`)
- `uv pip install --break-system-packages` 把包裝進了 python3.12 路徑，不是 3.11

**解法**: 所有 hr-document-automation scripts **必須**用 `python3.12` 作為 shebang / 呼叫方式

**預防**: 
- 任何提到 `python-docx` 的 skill，在「依賴」段落**必須**標明 `python3.12` 而非泛稱 `python3`
- 驗證指令：`python3.12 -c "import docx; print('OK')"`

**If→Then**:
- **If** `python-docx` import 報 `ModuleNotFoundError` 且 `python3 --version` 顯示 3.11
- **Then** 改用 `python3.12` 重新 import

---

## C# OpenXML 依賴陷阱：minimax-docx 沒有 dotnet

**症狀**: `hr-document-automation` 依赖 `minimax-docx`（C# OpenXML），但 N100 主機無 `dotnet-sdk`，導致 minimax-docx 的 `env_check.sh` 顯示 `[FAIL] dotnet not found`。

**根因**: C# OpenXML SDK 需要 .NET runtime + SDK，但 N100 環境只裝了 CLI tools 沒有 SDK。

**解法**: 繞過 C#，直接用 `python-docx`（python3.12）產出 .docx，兩者功能重疊且 Python 路徑已驗證。

**預防**: 
- 若 skill 文件說「使用 minimax-docx」，先跑 `bash minimax-docx/scripts/env_check.sh` 確認 dotnet 可用
- 不可用的果：立即在依賴矩陣中標為 `⚠️`，並找到替代方案

**If→Then**:
- **If** `dotnet --version` 回傳 `command not found` 且 skill 依赖 C# OpenXML
- **Then** 該 pipeline 無法使用，立即找 Python 替代方案
- **If** 多個 skill 都說「依賴 minimax-docx」但 dotnet 未裝
- **Then** 這是系統性瓶頸，不只是單一 skill 的問題
