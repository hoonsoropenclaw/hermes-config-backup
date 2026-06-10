# 精瘦 Profile SOP（建立常駐代理時的 skill 純化程序）

> 2026-06-09 確立。**為什麼需要這個 SOP**：`hermes profile create --clone` 會從 default 帶全部 skill（本次帶 194 個），但常駐代理應該只持有「自己角色相關 + 基礎設施」共 30-60 個，避免 context 被無關技能污染、避免「身份混淆」（代理試著用跟自己角色無關的技能）。

---

## 觸發時機

使用者說「建一個常駐 X 代理」「建立長期監控代理」「幫我做 X 角色 agent」時，在 `hermes profile create --clone` **完成後立即**做這個 SOP。**不要**跳到「建好就直接交付」。

## 預期效益（驗證過）

- 磁碟空間：344 MB → 130 MB（每個 profile 省 200+ MB）
- 身份純化：代理只看到跟自己相關的 skill，不會主動嘗試無關功能
- 與 default 主代理隔離：default 仍保留 194 個 skill 完整版

---

## 階段 0：環境確認（不做會誤刪）

```bash
# 確認主代理（default）自己有完整 skill
hermes skills list 2>&1 | tail -1
# 期望：~196 enabled

# 確認新 profile 已建立
hermes profile list
# 期望：新 profile 顯示出來
```

**不要**用 `hermes --clone-all`（會把整個 default 狀態複製，含 sessions、logs、cron 紀錄，污染新 profile）。

---

## 階段 1：`opt-out --remove` 自動清 bundled skill

```bash
hermes -p <新-profile> skills opt-out --remove --yes
```

**會發生什麼**：
- 寫入 `<profile>/.no-bundled-skills` marker（以後 `hermes update` 不會再 seed 進來）
- 自動刪除 manifest 內**未被修改**的 bundled skill（本次刪了 65 個）
- **保留** user-edited、hub-installed、local skill

**驗證**：
```bash
ls ~/.hermes/profiles/<新-profile>/.no-bundled-skills  # marker 存在
hermes -p <新-profile> skills list 2>&1 | tail -1       # 數字從 ~697 掉到 ~640
```

**注意**：`persistent-subagent` 這類「在 default 端已被刪、但 clone 帶進來」的殘留 skill **可能不會被 opt-out 自動刪**（因為 opt-out 用 bundled manifest 比對，殘留的 clone 不在 manifest 內）。這要在階段 2 一併手動清。

---

## 階段 2：精準白名單刪除（身份純化核心）

### 2.1 取得磁碟真實清單（不要用 hermes CLI）

```bash
ls ~/.hermes/profiles/<新-profile>/skills/ | grep -v "^\." > /tmp/profile-skills-actual.txt
wc -l /tmp/profile-skills-actual.txt
# 比 hermes skills list 報的「enabled 數字」更準（CLI 會把子目錄也算進去）
```

### 2.2 設計白名單（依角色分）

兩個固定區塊：

**共同必留**（任何代理都需要）：
- `general-workflow` / `user-collaboration-style` / `trial-and-error` / `workspace-folder-layout`（赫米斯基礎設施）
- `bash-defensive-patterns` / `python-anti-patterns` / `python-observability` / `python-resilience`（defensive 程式設計）
- `web_search` / `agent-browser` / `browser` / `vision-analysis` / `skill-docker`（工具輔助）
- `minimax-docx` / `minimax-pdf` / `minimax-xlsx` / `docx` / `pdf` / `xlsx` / `pptx-generator` / `beautiful-mermaid`（輸出格式）
- `anti-panic-protocol` / `anti-pattern-czar` / `anti-slop-design` / `antislop` / `new-conversation`（SOP/反 slop）

**角色專屬**（依 agent 用途挑）：

| 代理類型 | 範例專屬 skill |
|----------|----------------|
| 消費者需求 / 功能盤點 | anthropic-customer-research、anthropic-account-research、anthropic-competitive-brief/intelligence、anthropic-knowledge-synthesis、anthropic-synthesize-research、scrapling、research |
| 產品規劃 | `prd-drafting`、anthropic-roadmap-update、anthropic-sprint-planning、anthropic-write-spec、github、linear-hr-workflow |
| 金融交易 | tradingagents、trader-*、anthropic-financial-statements、finance |
| 程式開發 | software-development、github、tdd-workflow、python-resilience、hermes-tier-router |
| 視覺設計 | design-taste-frontend、frontend-design、hallmark、antigravity-design-expert |

### 2.3 批次刪除（用 Python，不要用 shell glob）

```python
import os, shutil

with open("/tmp/profile-skills-actual.txt") as f:
    actual = set(l.strip() for l in f if l.strip() and not l.startswith("."))

# 過濾非 skill 項目
NON_SKILL = {"portal-auto-upload.md", "skill_stats.json", "_meta"}
actual -= NON_SKILL

# 白名單 = 共同必留 + 角色專屬
KEEP = {"general-workflow", "user-collaboration-style", ...}  # 填實際清單
to_remove = sorted(actual - KEEP)

# 刪
PROFILE_DIR = os.path.expanduser("~/.hermes/profiles/<新-profile>/skills")
for name in to_remove:
    path = os.path.join(PROFILE_DIR, name)
    if os.path.isdir(path): shutil.rmtree(path)
    elif os.path.isfile(path): os.remove(path)
```

### 2.4 必保留保險

無論白名單怎麼寫，**這 5 個一定要有**：
1. 自己的專屬 skill
2. `general-workflow`
3. `trial-and-error`
4. `user-collaboration-style`
5. `workspace-folder-layout`

---

## 階段 3：驗證（4 項必須全過）

```bash
# 1. 專屬 skill 還在
test -f ~/.hermes/profiles/<新-profile>/skills/<自己-skill>/SKILL.md && echo "✓ 專屬 skill 還在"

# 2. 4 個通用必留還在
for s in general-workflow trial-and-error user-collaboration-style workspace-folder-layout; do
  test -d ~/.hermes/profiles/<新-profile>/skills/$s && echo "✓ $s" || echo "✗ $s MISSING"
done

# 3. 主代理（default）依然完整（最重要的不可逆防護）
ls ~/.hermes/skills/ | wc -l  # 應該還是 ~194
test -d ~/.hermes/skills/persistent-subagent && echo "⚠ default 端不該刪的東西被動了" || echo "✓"

# 4. opt-out marker 存在
test -f ~/.hermes/profiles/<新-profile>/.no-bundled-skills && echo "✓ marker 存在"
```

---

## 階段 4：寫進長期記憶（L3 教訓）

這次的判斷要進 MEMORY.md 的「抽象決策原則」段，讓未來的我自動知道：

```markdown
### 精瘦 profile 原則（2026-06-09 確立）
- 任何「常駐子代理」（用 `hermes profile + tmux` 建立的）= 30-60 個 skill（自己專屬 + 赫米斯基礎設施）
- 磁碟節省 200+ MB、避免身份混淆、context 純淨
- **If** 建立新常駐代理 **Then** 一定要跑 `opt-out --remove` + 白名單刪除兩個階段（完整 SOP 見 trial-and-error/references/sops/profile-slimming-sop.md）
```

---

## 已知坑

1. **`hermes skills list` 數字跟磁碟 `ls` 數字不一致** — CLI 把 skill 子目錄的 `references/` `scripts/` 等也算成 enabled；看磁碟為準
2. **opt-out 不會刪 user-edited / hub / local skill** — 階段 2 必須手動刪
3. **`persistent-subagent` 等已被 default 移除的殘留** — opt-out 跳過，階段 2 一併清
4. **刪了 hub 來源的 skill 後，`hermes update` 不會自動裝回來** — 真要回來得用 `hermes skills install` 顯式安裝
5. **不要刪 `_meta` 目錄或 `skill_stats.json`** — 這些不是 skill，是 hermes 自己的 metadata

---

## 怎麼 undo（後悔的話）

```bash
# 1. 刪 opt-out marker（恢復未來會 seed 進來）
rm ~/.hermes/profiles/<profile>/.no-bundled-skills

# 2. 跑一次 hermes update 觸發 seeding
hermes -p <profile> update

# 但已經刪掉的 skill 不會自動回來（除非原本是 bundled），要手動：
hermes -p <profile> skills install <skill-name>
```

**注意**：刪的 skill 主代理（default）都還有，可以參考 default 那邊的 SKILL.md 把內容複製回來，或整個 `cp -r ~/.hermes/skills/<skill> ~/.hermes/profiles/<profile>/skills/`
