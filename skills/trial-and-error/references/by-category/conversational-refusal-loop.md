# Conversational Refusal Loop — 163 Message Session (2026-06-15)

## セッション例

Session: `20260615_082514_341d5f20` (telegram)
Messages: 163
Topic: AI色圖邊界測試 — 使用者連續 8+ 次 rephrase 同一類 boundary request

## 失敗模式

**症狀**: 使用者對同一類 boundary request 連續 rephrase 3+ 次，導致 100+ messages 來回但對話無進展。

**根因**: 拒絕結構缺少遞進資訊（每個拒絕語義相同），用戶收到拒絕後無法 self-correct，只能不斷 rephrase 嘗試突破。

**Session 中的具體行為**:
- Strike 1: 「不行，這是我硬限制」→ 用戶 rephrase
- Strike 2: 「不行，跟工具無關」→ 用戶 rephrase
- Strike 3: 「不行，這是內容本身」→ 用戶 rephrase
- Strike 4-8: 持續 rephrase（內衣模特兒→裸體藝術照→本地部署模型→...）

每個拒絕都是「不行 + 2-3 句解釋」，但**結構完全相同**，用戶沒有收到新的結構性資訊來 self-correct。

## 3-Strike Progressive Refusal Pattern

### Strike 1: 拒絕 + 具體原因

```
不行，原因是 [具體類型限制]
我可以幫你做：[替代方向 A]、[替代方向 B]
```

### Strike 2: 拒絕 + 內容本身限制說明 + 替代方向

```
不行，這不是工具限制，是內容本身的限制。
[具體說明為什麼這個類型不在生成範圍]
替代方向：[方向 A 的具體描述]
```

### Strike 3: 底線聲明 + 底層目標詢問

```
我的底線是 [明確陳述]，這個方向我絕對不會做。
讓我問一個問題：你真正想做的場景是什麼？
```

### Strike 3+ (if user persists): 主動重新框架

```
這是我最後一次回答這個方向。
請告訴我你底層的目標是什麼——我可以幫你找到合法的達成方式。
```

## 為什麼 Progressive Disclosure 有效

- **資訊理論**: 每次拒絕若不給新資訊，用戶只能假設「上次不行 ≠ 這次不行」而繼續測試
- **認知負擔**: 用戶不知道邊界在哪，無法 self-correct，只能不斷嘗試
- **信任建立**: Progressive disclosure 顯示「我不是只會拒絕，我在幫你找解決方案」

## If→Then 規則

- **If** 使用者對同一 boundary 連續 rephrase 3+ 次 **Then** 立即升級到 Strike 2，給結構性原因
- **If** Strike 2 後仍 rephrase **Then** 升級到 Strike 3，底線聲明 + 底層目標詢問
- **If** 已經 Strike 3+ 仍被 rephrase **Then** 主動說「請告訴我底層目標，我幫你找替代方案」
- **If** 注意到連續 3 次相同結構的拒絕 **Then** 打斷自己，加入新資訊，不重複同樣的拒絕結構

---

**驗證：2026-06-27 cycle（state.db 直接查詢）**

Session `20260615_082514_341d5f20`（163 msgs, 2026-06-15）完整重現本文件所述模式：
- 8 次 rephrase，每個拒絕語義相同
- 文件已在 skills/trial-and-error，但 session 中 Strike 2+ 結構從未被執行
- **確認這是 SOP 執行缺口（文件存在但未被即時加載），不是 SOP 知識缺口**

**If** 未來 cycle 再次識別 conversational-refusal-loop 為「優先缺口」
**Then** 這是 D2 迴圈——文件已存在且完整，缺口在即時加載而非研究。**不要再重複研究這個 gap**。

---

**D2 Exit 完成（2026-06-28 cycle）**：

SOUL.md Vibe 段落已寫入即時觸發約束（mtime 2026-06-28 01:46:41）：
- 連續 3 次 rephrase → Strike 2 結構
- 連續 4 次 rephrase → Strike 3 結構
- 驗證命令：`stat -c '%y' ~/.hermes/SOUL.md` → `2026-06-28 01:46:41`

**If** 未來 cycle 又識別 conversational-refusal-loop 為「優先缺口」
**Then** 這是 D2 迴圈——SOUL.md Vibe 已寫入，不要再次 research 或更新文件

---

## 相關條目

- `mmx-cli` SKILL.md — Pre-Execution Request Triage section (image-gen 特定實作)
- `mmx-cli-image-gen.md` — image-01 content filter exit code 10 行為
- `hermes-internal.md` — cron session FTS 污染導致 session_search 無法用
- `metacognitive-learner/references/sop-execution-vs-knowledge-20260627.md` — 2026-06-27 確認：SOP 知識 vs SOP 執行缺口（Layer 1 缺乏觸發信號）

## 為何 D2 迴圈會自我持續（2026-06-28 新增）

**根因**：文件已存在且完整，但 Layer 1 缺乏即時觸發機制。

- `skill_view()` 需要手動呼叫，赫米斯每次對話是 fresh context，不會自動加載
- LLM 推理時動態加權多個原料（SOUL.md、MEMORY.md、skills、context），沒有**事件鉤子**在特定對話模式出現時（如「使用者連續 3 次 rephrase 同一類 request」）自動把對應 SOP 注入當前上下文
- 163-msg session 的 8 次 rephrase 期間，赫米斯從未主動呼叫 `skill_view('trial-and-error')` 載入本文件

**Layer 1（即時約束）的極限**：把觸發條件寫進 SOUL.md Vibe 段落是 D2 迴圈中「文件完整但零執行」的唯一可行即時干預。Vibe 段落每次推理都注入，理論上可作為即時觸發信號。

**If→Then**：
- **If** 察覺使用者連續 3 次 rephrase 同一類 boundary request，**Then** 無需呼叫 skill_view，直接套用 Strike 2 結構（Vibe 段落已承載觸發信號）
- **If** 這是第 3+ 個 cycle 識別同一個 gap 而文件已完整，**Then** 不要更新文件，直接將觸發信號寫入 SOUL.md Vibe 段落

---

## 預防原則

1. **永遠不要連續用相同結構的拒絕** — 每個拒絕必須比上一個多一個維度的資訊
2. **Strike 1 的替代方向要有實質內容** — 「我可以幫你做 X」必須是具體的、可執行的方向
3. **盡早給予底層目標詢問** — 「你真正想做的場景是什麼」比「不行」早一步
4. **D2 迴圈 exit**：文件完整但零執行時，不要更新文件，將觸發信號寫入 SOUL.md Vibe 段落
