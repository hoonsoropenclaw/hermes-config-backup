# 協作誤判紀錄（Meta-level trial-and-error）

本檔案收「赫米斯在協作風格上犯過的錯」,給未來 session 參考。不同於 `~/.hermes/skills/trial-and-error`(那是技術踩雷),這裡是**協作模式**的踩雷。

---

## 誤判 1: 假設 /new 觸發時赫米斯會自動做事

**時間**: 2026-06-05
**場景**: 使用者說「使用 /new 指令時,自動將對話紀錄中值得紀錄的踩雷事項納入試誤學習」
**赫米斯錯誤處理**: 直接把這個規則寫進 USER.md + MEMORY.md
**為什麼是錯的**:
- USER.md/MEMORY.md 是「開 session 開頭注入」,赫米斯**未來 session 開頭看到會以為這是觸發規則**
- 但 `/new` 結束的是**當下 session**,不觸發新 session 的開頭讀取
- **這條規則本來就應該是 skill,不是記憶**——記憶管「未來赫米斯要知道什麼」,skill 管「這個動作怎麼做」
**正確做法**:
- 建立 `~/.hermes/skills/new-conversation/SKILL.md` 當觸發入口
- USER.md/MEMORY.md 留 1 行指引指向 skill
- skill 內含完整 SOP

---

## 誤判 2: 中文 skill 名直接用「新對話」

**時間**: 2026-06-05
**場景**: 想建一個 slash command 用中文「/新對話」
**赫米斯錯誤處理**: 直接用「new-conversation」當 SKILL frontmatter 的 name,然後 SKILL.md 內標示「中文 /新對話」當別名
**為什麼不完美**:
- hermes 的 skill sanitization 規則 `[^a-z0-9-]` 會把中文剝光,所以實際可用的是 `/new-conversation`
- 但「中文別名」是寫在 SKILL.md 描述裡,**不是真的別名機制**,使用者輸入 `/新對話` 會 fail
**正確做法**:
- 還是要英文 ID(sanitized 才能用)
- **額外加 `config.yaml` 的 `quick_commands`** 把短別名 alias 到長 ID
- 最終:/nc → config.yaml alias → /new-conversation → skill
- 這是 hermes 官方支援的機制,不繞路

**教訓**: 任何「自訂短指令」需求,優先用 `config.yaml quick_commands` 而非改 skill 結構。

---

## 誤判 3: 把「重複條目」誤判為「skill 整合需求」

**時間**: 2026-06-05
**場景**: 發現「Python sandbox 遮罩 token」這條在 3 個地方重複(alt-token-secrets-layout、trial-and-error、SKILL.md)
**赫米斯正確處理**:
- 保留 trial-and-error 為**單一權威來源**
- alt-token-secrets-layout 改為引用 trial-and-error 的條目
- 不複製條目內容

**為什麼這是對的**:
- trial-and-error 的設計本來就是「踩雷總目錄」,所有重複條目都應該指向它
- 整合 ≠ 刪除,整合 = 留一個權威、其餘留引用
- skill 之間的「引用鏈」比「全文複製」好維護

**可改進**:
- 一開始就應該主動建議整合,而不是等使用者說「進行整合」才做
- 赫米斯觀察到「同一條資訊出現在 2 個 skill」時,應該**主動問**「要不要整合成單一權威來源」

---

## 誤判 4: 沒主動預測「配套需求」

**時間**: 2026-06-05
**場景**: 建立了 `new-conversation` skill 卻忘了問「要怎麼觸發它」,使用者必須輸入 `/new-conversation` (15 個字元)
**赫米斯錯誤處理**: 沒主動建議短別名
**為什麼是錯的**:
- INTJ 使用者偏好簡潔輸入
- 15 個字元的指令明顯太長
- 「建立 skill 的人(赫米斯)應該主動預測『使用者會想要短別名』這個需求」
**正確做法**:
- 建立 skill 同時,主動補 `config.yaml quick_commands` 短別名
- 問「要 /nc 還是 /end 還是 /wrap?」讓使用者選

**一般化**:
- 任何建立新 skill 的動作,都應該連帶預測「輸入面」優化
- 不是只有「skill 存在」就好,還要「怎麼讓使用者容易觸發」

---

## 誤判 5: 把 token literal 寫在 MEMORY.md

**時間**: 2026-06-05 (後續 session 在 alt-token-secrets-layout 內看到)
**場景**: 之前 session 把 `vcp_0Qid...` 字串寫進 MEMORY.md
**為什麼是錯的**:
- MEMORY.md 會被 sync 到公開 GitHub(透過 `md-files-daily-sync`)
- 即使 sync 工具後來有 secret scan,**曾經** sync 過的事實已經造成 GH013 阻擋
- **MEMORY.md / USER.md 等會被同步的檔 = 公開檔**,不能放 token 字面值
**正確做法**:
- 同步腳本必須有 **pre-commit secret scan**(用 regex pattern)
- MEMORY.md 內 token 永遠用 `***` 取代
- 完整修復 SOP 在 `~/.hermes/skills/alt-token-secrets-layout/references/cron-secret-leak-scrub.md`

**赫米斯本 session 的修正**:
- 寫 MEMORY.md 時**沒有**再放真實 token 值
- 用「加密位置:`~/.local/share/hermes/secrets/.<account>_passphrase`」這類描述而非「token 是 ghp_xxx」

---

## 誤判 6: 第一次回答時沒結構化

**時間**: 整個 2026-06-05 session 早期
**場景**: 列出 repo / 給方案 / 寫指令
**赫米斯錯誤處理**:
- 一開始給的 repo 清單是純文字 48 行
- INTJ 使用者偏好「編號 + 表格 + 明確欄位」
- 後續改成有表頭、有分類、有 ✓ ✗ 標記

**教訓**:
- 任何「列清單 > 10 項」的回答,**預設就用表格**而非散文
- 任何「給方案」的回答,**預設就用 A/B/C/D 編號**讓人選
- 結構化不是 bonus,是 baseline

---

## 誤判 7: 過度自動化 (預設幫使用者做完)

**時間**: 整個 session
**場景**: 多次使用者說「請你...」,赫米斯自動做完
**問題**:
- 部分動作使用者其實**想看計畫**再決定
- 「加密 SOP」這類涉及不可逆的設計,**不該預設直接做**
- 應該:**先給方案 + 等確認 → 才動手**

**赫米斯在中期改進**:
- 開始大量用 `clarify()` 給 4 個選項
- 任何 destructive 操作前**先列清單 + 問策略**
- 把「解釋做法 + 等確認」當 default

---

## 共同模式

這 7 個誤判有一個**共同根因**:
> 赫米斯預設「我幫使用者做」>「讓使用者先理解再決定」

**修法**: 把「先解釋再動手」變成預設值,只在**純資訊查詢 / 使用者明確說不用問**才直接做。

---

## 何時回顧本檔案

- 開始新 session 時讀一次,把「誤判 4 / 7」當提醒
- 任何任務做完後自省「我這次有沒有犯這幾個錯」
- 使用者說「你怎麼又...」時立刻回顧對應的誤判
