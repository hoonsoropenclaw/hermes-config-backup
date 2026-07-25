# Cron Secret Leak 真實案例（2026-06-05 skill-usage-daily-v3 失敗）

> 完整修復 SOP 見 `~/.hermes/skills/alt-token-secrets-layout/references/cron-secret-leak-scrub.md`
> 本檔是 metacognitive-learner 內部的「為何這件事很重要」記錄

## 事件時間軸

- **2026-06-05 00:01:01**：`skill-usage-daily-v3` cron 執行 → exit code 1
- **last_error**：`GH013: Repository rule violations found for refs/heads/main.`
- **洩漏位置**：`assets/md-files.json:40` 內含 `vcp_***REDACTED***`
- **影響**：連續 4+ 天失敗、公開 GitHub repo 有 secret leak 痕跡（即使 commit 被擋下，本地 commit object 仍含 token）

## 為何 metacognitive-learner 之前沒抓

**檢討**：
1. 之前學習識別了 `hermes cron edit --script` bug，但**沒有把「cron 失敗需主動追蹤」變成持續流程**
2. `sync_md_files.py` 沒內建 secret scan（`sync_md_files.py` 內 line 59-64 寫法是直接拷貝 content 進 JSON）
3. `MEMORY.md` 內有 `vcp_` token 字面值（教訓見 `alt-token-secrets-layout`）
4. 沒有「cron 失敗立即 alert 機制」

## 此案例對未來的啟示

1. **Sync 到公開 GitHub repo 的腳本必加 pre-commit secret scan**（見 `references/secrets-in-sync.md`）
2. **MEMORY.md 等被同步的檔案不放具體 token 值**，一律 `***` 取代
3. **Phase 1.5 必跑 cron 健康掃描**（已在 metacognitive-learner SKILL.md 加入）
4. **新 skill `cron-job-health-monitor`** 專責 cron 失敗分類 + 修復

## 修復進度追蹤

- [ ] `hermes cron edit <md-files-daily-sync id> --enabled false`
- [ ] `git rm --cached assets/md-files.json` + sed 取代 token
- [ ] 用 `bfg-repo-cleaner` 清歷史
- [ ] 撤銷被洩漏的 Vercel token
- [ ] 修補 `sync_md_files.py` 加 `mask_secrets()` 函數
- [ ] 把 MEMORY.md 內 token 字串改成 `***`
- [ ] 重啟 cron 驗證
