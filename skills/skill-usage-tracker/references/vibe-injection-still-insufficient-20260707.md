# SOUL.md Vibe Injection 仍未生效（2026-07-07 cycle）

**cycle**: metacognitive-learner cycle 2026-07-07
**問題**：06-29 已執行 SOUL.md Vibe 寫入（SOP-A 觸發約束 → SOUL.md Vibe §95-106），但 07-02 backup modification session（D3，132 msgs）仍 0 invite sent。

## 驗證數據

- `analyze.py`：combo_rating 樣本 3（皆為 weak reward inferred），0 explicit invite
- 07-02 session（`20260702_221910_b4729405`）：132 msgs，包含 D3 deliverable（`hermes-backup-v4.sh --brief` + wrapper scripts + jobs.json patch）
- 該 session 全程無「⭐ 請評分」邀請
- 使用者只說了 2 句話：「請問...」「直接動手」

## 根因分析

**觸發場景**：使用者說「直接動手」→ 赫米斯服從執行 → 完成後沒停等用戶回覆就繼續下一個步驟（直接開始下一個 D3 子步驟）→ SOP-A 邀請被跳過。

**問題本質**：這不是「Vibe 段落沒被注入」的問題，而是 **Rule 12 偏移**（自作主張執行）在 D3 任務中特別容易觸發。當使用者說「直接動手」，赫米斯理解成「加速前進、跳過所有非必要步驟」，而 SOP-A 邀請被歸類為「非必要步驟」。

## 為何 SOUL.md Vibe 不足

SOUL.md Vibe 是 Layer 1 soft guidance，赫米斯每次推理都注入——但當使用者在同一 session 說「直接動手」，赫米斯會產生「疊加服從」效應：服從執行的衝力壓過了「停下來問評分」的約束。

Layer 1 注入在「使用者明確指示加速」的情境下被選擇性忽略，這是 LLM 推理的置信度偏差問題，不是「Vibe 沒注入」。

## 架構事實（再次確認）

- logger 正常：06-16 session combo=4 logged ✅
- 工具正常：`post_delivery.py` 功能正確 ✅
- 文件完整：SOUL.md Vibe + SKILL.md SOP-A ✅
- 缺口：在「使用者說直接動手 + D3 高強度執行」的組合下，SOP-A 邀請被跳過

## 下一步（待下次 main session 執行）

在下次 main session，主動問「我是否在 07-02 跳過了評分邀請？」——這是取得外部驗證反饋的最低成本方式。

## If→Then（防止下次掉進同一陷阱）

**If** 使用者在 D3 任務中說「直接動手」並且赫米斯服從執行
**Then** D3 完成後**仍必須**先附上 SOP-A 評分邀請，再繼續下一個步驟
**Then** 「使用者說直接動手」= 同意執行，不等於「放棄交付後 SOP」

**If** 赫米斯在 D3 任務中已完成多個子步驟
**Then** 每個子步驟完成後都可以附上 SOP-A 邀請，不需等到整個 D3 完成
**Then** 這樣即使使用者中途打斷，也不會完全錯過評分機會

**If** 連續 3+ cycles 都識別同一個 gap 且已有完整 D3 exit 記錄（SOP-A 已寫入 SOUL.md Vibe）但缺口仍未解決
**Then** 這不是「研究不足」而是「Layer 1 注入失效」— 需考慮外部驗證（直接問使用者）
