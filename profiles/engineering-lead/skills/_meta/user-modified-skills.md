# Profile Skill 修改紀錄

> 哪些 skill 被 hand-edited、避免 hermes update 重新 seed 時覆蓋。
> 配合 `.user-modified` marker 使用（每個被改的 skill 內都有 marker 檔）。

## 2026-06-11（首次建立）
- `debug` (opt-in from anthropic-plugins/engineering/skills/debug) — 2026-06-11 cp -r
- `systematic-debugging` (opt-in from software-development/systematic-debugging) — 2026-06-11 cp -r
- `writing-plans` (opt-in from software-development/writing-plans) — 2026-06-11 cp -r
- `tech-debt` (opt-in from anthropic-plugins/engineering/skills/tech-debt, 作為 refactor-patterns 替代品) — 2026-06-11 cp -r

> 上述 4 個 skill opt-in 完已加 `.user-modified` marker、目前 SKILL.md 內容跟 default 一致。
> 任何未來 hand-edit 請：
> 1. 先確認 `.user-modified` 還在
> 2. 改完在這裡記日期 + 改了什麼
