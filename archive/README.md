# archive/

`~/.hermes/` 根目錄的「棄用備份歸檔」。

## 歸檔規則

- **什麼進來**：被新版取代的 config.yaml 備份（`__DEPRECATED__*.bak.*`）、已過期的過渡檔、不再需要的歷史快照
- **什麼不進來**：有效的 config 備份（按 hermes-config-layout § 備份慣例保留近 5 個在 cron/ 或原地）、快取檔、可重建的派生資料

## SOP 參考

- `~/.hermes/skills/devops/hermes-config-layout/SKILL.md` § 備份慣例
- `~/.hermes/skills/workspace-folder-layout/SKILL.md` § 搬移 SOP
