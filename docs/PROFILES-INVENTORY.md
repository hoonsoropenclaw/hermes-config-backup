# PROFILES-INVENTORY.md - 7 個常駐 Profile 結構清單

> 2026-06-11 初次建立。作為「profile 結構有任何變動」的 single source of truth。
> 改任何 profile（建/刪/精瘦/加 skill）都必同步改本檔。
> 跟 `INVENTORY.md`（備份用）並列，但用途不同。

## 7 個 Profile 一覽

| Profile | Skill 數 | Opt-out bundled | Persona | SOUL | 大小 | .user-modified | 角色 |
|---------|---------|-----------------|---------|------|------|----------------|------|
| `consumer-researcher` | 56 | ✓ | 見 profile | 見 profile | 135.9 MB | 0 | handoff chain 第 1 棒 / 消費者研究 |
| `product-planner` | 63 | ✓ | 見 profile | 見 profile | 141.7 MB | 0 | handoff chain 第 2 棒 / PRD 撰寫 |
| `system-architect` | 101 | ✓ | 見 profile | 見 profile | 297.4 MB | 0 | handoff chain 第 3 棒 / 技術架構 |
| `engineering-lead` | 84 | ✓ | 見 profile | 見 profile | 139.3 MB | 4 | handoff chain 第 4 棒 / 程式實作 |
| `test-engineer` | 42 | ✓ | 9.8 KB | 6.8 KB | 216.9 MB | 42 | handoff chain 第 5 棒 / 品質驗收（鏈尾） |
| `default` | 0 | ✗（source）| - | - | - | - | 主代理、telegram gateway |

> **Skill 數計算規則**：頂層目錄 + 頂層 `.md` 單檔 skill（不含 `.archive` / `.curator_backups` / `.hub` / `.bundled_manifest` / `.usage.json` 等 opt-out 殘留）。

## Handoff Chain 完整圖

```
consumer-researcher  →  product-planner  →  system-architect  →  engineering-lead  →  test-engineer
   (56 skills)            (63 skills)         (101 skills)         (84 skills)          (38 skills)
   消費者研究             PRD 撰寫             技術架構             程式實作             品質驗收
```

## 各 Profile 角色定位

### `default`（**0 skills**、**預設主代理**）
- 跑 hermes-gateway、telegram 連線、general-purpose
- 195 個 skill 由 default 帶、clone 給其他常駐 profile
- Persona：無（用 system prompt）

### `consumer-researcher`（56 skills）
- handoff chain 第 1 棒
- 從網路/Reddit/PTT/HN 抓消費者聲音
- 產出 `consumer-needs-research-<slug>.md`

### `product-planner`（63 skills）
- handoff chain 第 2 棒
- 接 consumer-needs-research 寫 PRD
- 產出 `prd-<slug>.md` + 釐清 [待釐清] / [待驗證]

### `system-architect`（101 skills）
- handoff chain 第 3 棒
- 接 PRD 寫技術架構
- 產出 3-5 份 `arch-<slug>.md`（架構文件 + API 規格 + 資料模型）

### `engineering-lead`（**84 skills**，2026-06-11 從 81 補 4 個）
- handoff chain 第 4 棒
- 接 arch 拆 sprint ticket + 寫 code + TDD
- 4 個新 opt-in skill：`debug` / `systematic-debugging` / `writing-plans` / `tech-debt`
- 產出 `sprint-<N>-report.md` + 多個 PR

### `test-engineer`（**42 skills**，2026-06-11 初次建立）
- handoff chain 第 5 棒（**鏈尾**）
- 接 sprint 報告跑 unit + integration + E2E + 性能測試
- 產出 `bug-report-<N>.docx` + `sprint-<N>-qa-signoff.md`
- 精瘦於 195 → 38（reduction 80.5%）+ 後加 4 個專屬 skill = 42

## Handoff 觸發機制

- **不是 cron 自動**——目前所有 chain 階段都**靠主 session 手動串接**（透過 ~/.hermes/handoff/<project-slug>/ 目錄 + 終端機呼叫）
- **未來可以改成 cron**——但目前觀望、手動串接的可控性高
- 詳見 `~/.hermes/skills/autonomous-ai-agents/hermes-architecture/SKILL.md` 跟 MEMORY.md「跨 profile handoff pipeline」

## 各 Profile 的 .user-modified 狀態

| Profile | .user-modified 已加 skill | 紀錄位置 |
|---------|---------------------------|---------|
| `engineering-lead` | debug / systematic-debugging / writing-plans / tech-debt（4 個 2026-06-11 加） | `skills/_meta/user-modified-skills.md` |
| `test-engineer` | 38 個全標記（clone 自 default 後精瘦） | `skills/_meta/slim-history.md` + 各 skill 內 `.user-modified` 檔 |
| 其他 4 profile | 未標記（opt-in 走 bundled 機制、不需 marker） | - |

**為什麼需要 .user-modified**：opt-in 用 `cp -r`（不是 symlink）、未來 hermes update 重新 seed 不會自動同步、需 marker 提醒「這個 skill 是手動加的、可能跟 default 不一致」。詳見 trial-and-error/references/by-category/hermes-internal.md「Profile 補 skill 用 cp -r vs symlink」條目。

## 修改影響對照表（給未來 AI 必看）

### 新增 profile 時
**必同步修改**：
1. 本檔（PROFILES-INVENTORY.md）—— 加新 profile 段落
2. MEMORY.md「常駐子代理」段—— 記錄新 profile 的角色跟 SOUL 摘要
3. trial-and-error/references/by-category/hermes-internal.md—— 加新 profile 建立的踩坑紀錄

### 精瘦某 profile 的 skill 時
**必同步修改**：
1. 該 profile `skills/_meta/slim-history.md`—— 記錄精瘦決策
2. 該 profile 移除的 skill 內的 `.user-modified` marker 也要清掉
3. 該 profile `persona.md` 內的「技能庫概覽」段—— 更新 skill 數

### 改某 profile 的 persona / SOUL 時
**必同步修改**：
1. 該 profile `persona.md` 跟 `SOUL.md`
2. 該 profile 的 `memories/MEMORY.md`（如果有關鍵轉變）
3. INVENTORY.md 改檔對照表（如果改了 hermes 架構）

### 加 skill 進某 profile 時
**必同步修改**：
1. 該 skill 目錄下的 `.user-modified` marker
2. 該 profile `skills/_meta/user-modified-skills.md`（如果存在）或新建
3. 該 profile `persona.md` 內的「技能庫概覽」段—— 加新 skill

## Wrapper Scripts

所有 profile 都有 `~/.local/bin/<name>` wrapper（hermes 自動建）：
- `~/.local/bin/consumer-researcher`
- `~/.local/bin/product-planner`
- `~/.local/bin/system-architect`
- `~/.local/bin/engineering-lead`
- `~/.local/bin/test-engineer`
- （default 無 wrapper）

每個 wrapper 是 44 bytes、指向 `~/.hermes/hermes-agent/venv/bin/hermes` 加 profile 參數。

## 驗證命令

```bash
# 1. 列出所有 profile
hermes profile list

# 2. 確認某 profile skill 數（頂層目錄 + 單檔 .md）
python3 -c "
from pathlib import Path
sd = Path.home() / '.hermes/profiles/<name>/skills'
n = sum(1 for d in sd.iterdir() if not d.name.startswith('.') and (d.is_dir() or (d.is_file() and d.suffix == '.md' and d.name != 'README.md')))
print(f'{n} skills')
"

# 3. 確認 wrapper 存在
ls -la ~/.local/bin/<name>

# 4. 確認 .user-modified marker 數
find ~/.hermes/profiles/<name>/skills/ -name ".user-modified" | wc -l

# 5. 確認某 profile 跑得起來
~/.local/bin/<name> chat -q "ping" --cli
```

## 各 Profile 完整檔案路徑

```
~/.hermes/profiles/
├── default/                # 主代理 source
├── consumer-researcher/    # chain 第 1 棒
│   ├── persona.md
│   ├── SOUL.md
│   ├── config.yaml
│   ├── .env
│   ├── .no-bundled-skills
│   ├── memories/MEMORY.md
│   ├── skills/             # 56 個
│   └── cron/, logs/, sessions/, state.db, ...
├── product-planner/         # chain 第 2 棒 (63 個 skills)
├── system-architect/        # chain 第 3 棒 (101 個 skills)
├── engineering-lead/         # chain 第 4 棒 (84 個 skills)
│   ├── persona.md
│   ├── SOUL.md
│   ├── skills/_meta/user-modified-skills.md  ← opt-in 紀錄
│   └── skills/{debug,systematic-debugging,writing-plans,tech-debt}/.user-modified
└── test-engineer/           # chain 第 5 棒 (38 個 skills)
    ├── persona.md           (9.8 KB)
    ├── SOUL.md              (6.8 KB)
    ├── skills/_meta/slim-history.md  ← 精瘦決策
    └── skills/<38 個>/.user-modified
```

_Last updated: 2026-06-11_
