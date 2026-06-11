# Test Engineer Profile — Skill 精瘦紀錄

> 2026-06-11 初次建立。

## 建立歷程

| 階段 | 時間 | 動作 | skill 數變化 |
|------|------|------|------------|
| 建立 | 11:38 | `hermes profile create test-engineer --clone`（從 default 帶 195 個） | 0 → 195 |
| Opt-out bundled | 11:39 | `hermes -p test-engineer skills opt-out --remove --yes`（自動刪 bundled 65 個） | 195 → 194 |
| 精瘦 opt-out | 11:42 | 依白名單刪除 156 個跟測試無關的 skill | 194 → 38 |

## 精瘦決策（為什麼保留這 38 個）

### Hermes 基礎設施（5 個，必留）
- `general-workflow` / `user-collaboration-style` / `trial-and-error` / `workspace-folder-layout` / `anti-panic-protocol`
- 理由：任何代理都需要赫米斯基礎設施

### 反 slop / 反 pattern（3 個，必留）
- `anti-pattern-czar` / `anti-slop-design` / `antislop`
- 理由：避免測試報告 / bug 報告變 AI-slop

### defensive 程式（4 個，必留）
- `bash-defensive-patterns` / `python-anti-patterns` / `python-observability` / `python-resilience`

### 測試核心（4 個，必留）
- `tdd-workflow` / `test-driven-development` / `systematic-debugging` / `debug`

### 程式碼 review / coding（3 個）
- `code-reviewer` / `code` / `software-development`

### E2E / browser（4 個）
- `playwright-skill` / `agent-browser` / `browser` / `camofox`

### CI / 容器化（2 個）
- `skill-docker` / `github`

### QA 觀察（2 個）
- `site-qa-checklist` / `portal-auto-upload`

### 輸出格式（8 個）
- `minimax-docx` / `minimax-pdf` / `minimax-xlsx` / `docx` / `pdf` / `xlsx` / `pptx-generator` / `beautiful-mermaid`

### 工具輔助（3 個）
- `web_search` / `vision-analysis` / `new-conversation`

### Hermes 內部 SOP（2 個）
- `hermes-architecture` / `hermes-tier-router`

### sparc 內 agent-tester 相關（sparc-methodology 整個留）
- 理由：含 `agent-tester` / `tdd-london-swarm` / `test-long-runner` 等測試 agent patterns

## 為什麼不保留

- **anthropic-* 業務/法律/HR/行銷 skill**（60+ 個）：測試代理不需要
- **creative / design / mobile / web framework skill**：跟 E2E 測試無關
- **3d-web-experience / ant-design-skill / flutter-dev / ios-application-dev**：專注特定 stack
- **mlops / research / tradingagents / finance / data-science**：跟 QA 流程無關
- **swe-skills-bench / taste-skill-repo / strands-***：noise skill、可日後 opt-in

## 總計

- Before：195 個（clone 自 default）
- After：38 個（精瘦版）
- Reduction：80.5%
- 磁碟空間：估計 ~344 MB → ~50 MB

## User-modified 標記

所有 38 個 skill 都加了 `.user-modified` marker、SKILL.md 內容跟 default 一致、未來 hand-edit 前請看 trial-and-error/references/by-category/hermes-internal.md「Profile 補 skill 用 cp -r vs symlink」條目。


## 4 個 test-engineer 專屬 skill（2026-06-11 新增）

新增下列 4 個從零撰寫的專屬 skill（不是從 default 帶、不是 cp -r）：

1. **test-environment-bootstrap**（3.2 KB）—— 從 arch 的 docker-compose 段落起 test env、跑 smoke test、確認 healthy
2. **e2e-suite-runner**（3.0 KB）—— 從 sprint ticket 的 Given/When/Then 自動生成 Playwright E2E、跑、回報
3. **bug-report-generator**（3.1 KB）—— 從失敗 log 自動生成 .docx bug 報告（用 minimax-docx）
4. **sprint-qa-signoff**（4.5 KB）—— 從三層測試結果 + bug 清單生成 PASS/FAIL 決策

每個 skill 已加 `.user-modified` marker、未來 hand-edit 前請看 trial-and-error/references/by-category/hermes-internal.md「Profile 補 skill 用 cp -r vs symlink」條目。
