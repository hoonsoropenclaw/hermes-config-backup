# Cron-to-Telegram 精簡格式缺口（2026-07-10）

**Level**: D3 — Structured SOP creation
**Gap**: Session 2026-07-02 (132 msgs, "排程備份回報精簡化") 只修了 backup job 的 prompt 讓它們自己輸出精簡，但**沒有建立「赫米斯如何格式化 cron-to-Telegram 輸出」的標準格式**。導致：不同 cron job 對「精簡」的定義不一致。

---

## 發現的事實

**2026-07-02 brief mode 成果**（hermes-internal-20260702-addendum.md）：
- 3個 backup job：從 ~2400 bytes → ~170 bytes
- 但 `hermes-backup-coverage-check` 仍輸出 ~444 bytes（含詳細警告列表）

**現有 Telegram 格式化參考**（`api_quota_monitor.sh`、`system_monitor.sh`）：
```bash
# Emoji + HTML bold + 換行 = 赫米斯用戶的「精簡」標準
send_telegram "💾 <b>磁碟空間警告</b>\nN100 磁碟使用率：${usage}%\n儘早清理空間！"
send_telegram "🧠 <b>記憶體警告</b>\nN100 記憶體使用率：${usage}%\n注意可能記憶體洩漏！"
```

**格式要素**（5項）：
1. **單一 emoji** 前綴（一目了然）
2. **`<b>bold</b>` 標題**（核心狀態）
3. **換行分隔**（每訊息 2-4 行）
4. **無 Markdown**（用 HTML parse_mode）
5. **數字/路徑直出**（不用額外裝飾）

**當前 cron-to-Telegram 問題**：
- 即使 brief mode，scheduler.py 的 `deliver_content` 仍發送 Markdown 格式（`**粗體**`、列表 `-`）
- 使用者要的是 `✅/❌ + 1句核心訊息`，不是格式化過的 Markdown

---

## If→Then 規則

**If** 任何 cron job 需要對赫米斯用戶發 Telegram 報告
**Then** 遵循以下格式（赫米斯精簡標準）：

```
[Emoji] <b>標題</b>
內容行1
內容行2（可選）
```

| 場景 | Emoji | 標題範例 | 內容 |
|------|-------|---------|------|
| 備份成功 | ✅ | `<b>備份完成</b>` | `Tier1 OK, Tier2 OK, 3.2MB` |
| 備份失敗 | ❌ | `<b>備份失敗</b>` | `Tier1 error at step 3, log: ~/...` |
| Coverage 警告 | ⚠️ | `<b>覆蓋率警告</b>` | `6 warnings, see log` |
| 健康檢查 | 🟢 | `<b>健康</b>` 或 `<b>異常</b>` | `all jobs OK` |
| 配額預警 | 🔴 | `<b>配額不足</b>` | `20% left, ~6h remain` |

**不要**：長列表（3+ 項用 `…+N more` 截斷）、Markdown 列表語法（`- item`）、過程說明段落。

---

## 實作：hermes-backup-coverage-check 精簡化

**現狀**（444 bytes，verbose）：
```
# Cron Job: hermes-backup-coverage-check
⚠️  WARN  備份覆蓋率不完整（6 個 warning）
建議修法：
  1. 看哪些本機新路徑 v4 沒列
  2. 編輯 ~/.hermes/docs/INVENTORY.md...
  ...
```

**目標**（<200 bytes）：
```
⚠️ <b>覆蓋率警告</b>
6 warnings — see ~/.hermes/logs/backup-coverage.log
修法：edit INVENTORY.md + hermes-backup-v4.sh
```

---

## 驗證命令

```bash
# 檢視最近一次 coverage check 輸出大小
wc -c ~/.hermes/cron/output/651713da919d/2026-07-10_04-00-33.md
# → 444 bytes（需精簡化）

# 檢查 system_monitor.sh 的 Telegram 格式（參考）
grep -A3 'send_telegram.*<' ~/.hermes/scripts/system_monitor.sh
```

---

## 預防規則

**If** 未來任何 cron job 新增或修改
**Then** 確認其 Telegram 輸出符合「赫米斯精簡標準」：
- 每則訊息 ≤ 3 行
- Emoji 前綴
- HTML bold 標題
- 無 Markdown 裝飾
- 路徑/數字直出

**If** 發現 cron job 輸出 > 500 bytes 且非錯誤狀態
**Then** 立即觸發「精簡化」，不要等到用戶抱怨。
