# SOP Enforcement Architecture

## 核心問題

LLM 決策時從多個原料（soul.md、MEMORY.md、skills、context）動態加權，導致輸出不穩定。沒有外部驗收機制的「學習」只是裝飾。

---

## 三層服從架構

### 第一層：技能加載（最低保障）
- **機制**：SOP 寫在技能文件裡，LLM 遇到觸發條件時自動加載
- **限制**：LLM 這次會參考，下次不一定
- **提升方法**：觸發條件越詳細，遵守率越高

### 第二層：約束執行
- **機制**：`config.yaml` 中的 `tool_use_enforcement: auto`
- **作用**：某些場景必須用指定工具，減少「只說不做」
- **限制**：對 MiniMax 模型無效（`auto` 只針對 GPT/Codex/Grok/Gemini）
- **提升方法**：改為 `true` 可強制所有模型遵守

### 第三層：外部驗收（真正有意義）
- **機制**：任務完成後對照 SOP 檢查，發現偏移要求重新執行
- **限制**：目前未實作，需要自己建
- **提升方法**：建立 SOP Enforcer sub-agent

---

## tool_use_enforcement 設定參考

| 設定值 | 行為 |
|--------|------|
| `"auto"`（預設）| 只有 GPT/Codex/Grok/Gemini 收到 enforcement 引導 |
| `true` | 所有模型強制收到 enforcement 引導 |
| `false` | 完全關閉 |
| `["gpt", "codex"]` | 只有名稱包含這些字串的模型才收到 |

**當前限制**：MiniMax（M2.7）使用 `"auto"` 時不會收到 enforcement 引導，因為 MiniMax 不在 TOOL_USE_ENFORCEMENT_MODELS 列表中。

---

## SOP 偏移檢查清單

每次完成任務後，自我檢查：

```
1. 這個任務有沒有對應的 SOP/技能文件？
   - 有 → 對照檢查：我有沒有按照步驟執行？
   - 沒有 → 標記「待補 SOP」，不要假裝完成了
   
2. 我的輸出有沒有偏離確定的流程？
   - 有 → 記錄「錯誤：X，正確應該是 Y」
   - 無 → 標記「confirmed」
   
3. 這個任務的成功有没有外部驗證？
   - 有 → 標記「verified」
   - 沒有 → 標記「unconfirmed」，不要說「完成」
```

---

## 驗收機制設計原則

如果要做真正的 SOP 強制執行系統：

1. **觸發鉤子**：每個技能完成後自動觸發對照檢查
2. **量化指標**：記錄偏移次數、偏移類型、發現率
3. **學習封閉**：每次偏移被糾正後，自動更新 SOP（不是只記錄，要實際更新）
4. **獨立性**：驗收者不能是執行者本人（避免自我偏置）

---

## If→Then 快速參考

```
If: 用戶問「系統是不是越用越聰明」
Then: 先確認有沒有外部驗收機制，再回答
原理: 沒有外部驗收的自我改進聲明 = LLM 正向幻覺

If: 任務完成後沒有對照 SOP 檢查
Then: 標記為「unconfirmed」而非「success」

If: 要提升 agent 決策可靠性
Then: 增加外部強制約束，而非只改善 skill 文件
原理: 約束性 enforcement 比 soft guidance 更穩定
```