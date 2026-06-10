# hermes-config-backup (v4)

> **本 repo 是 Hermes Agent 設定/技能/記憶的版本化備份**
>
> v4 設計：雙雲端分層（GitHub Tier 1 + Google Drive Tier 2）

## 📦 這個 repo 備了什麼

| 路徑 | 內容 | 大小 | 重要 |
|------|------|------|------|
| `config.yaml` | Hermes 主設定 | ~5 KB | ✅ |
| `auth.json.template` | secrets 範本 | ~1 KB | ✅ |
| `agents/` | 5 個 agent profile | ~2 KB | ✅ |
| `memories/` | 7 個 markdown（MEMORY/USER/SOUL...）| ~10 KB | ✅ |
| `scripts/` | 備份/監控/管理腳本 | ~500 KB | ✅ |
| `docs/` | 還原 SOP 文件 | ~20 KB | ✅ |
| `skills/` | 185 個 skill | ~110 MB | ✅ |
| `skills/sparc-methodology/` | ruvnet/claude-flow snapshot | ~78 MB | ✅ |
| `EXCLUDE.md` | 為什麼這些東西**不**備 | - | 必看 |

## 🚫 不備的東西（看 EXCLUDE.md）

簡短版：
- ❌ `hermes-agent/` 本體（1.1 GB、可 `pip install`）
- ❌ `state.db` 資料庫（rebuild 即可）
- ❌ `.env`、tokens（會另外加密上 Drive Tier 2）
- ❌ `browser_screenshots/`、`image_cache/`、`audio_cache/`（cache）

## 🔄 異機還原（5 分鐘拿到可運行的 hermes）

```bash
git clone https://github.com/hoonsoropenclaw/hermes-config-backup.git ~/.hermes
cd ~/.hermes

# 1. 還原核心設定（已有）
cp config.yaml ~/.hermes/config.yaml
cp -r agents/ memories/ scripts/ docs/ ~/.hermes/

# 2. 還原 skills（sparc 在內）
cp -r skills/* ~/.hermes/skills/

# 3. 安裝 hermes-agent 本體（不算備份、隨時可裝）
pip install hermes-agent

# 4. 還原 secrets（從 Drive Tier 2，需要時才做）
# 見 hermes-restore-v4.sh 的 tier2 步驟
```

## 🏗️ 自動同步

由 `~/.hermes/scripts/hermes-backup-v4.sh` 自動處理：
- 每天檢查 `~/.hermes/` 變動 → 增量 commit → push 到本 repo
- 每周日 03:00 額外建加密 tar.gz → 上 Drive Tier 2

## 📊 Repo 統計

- 最後更新：見 [commits](../../commits/main)
- sparc-methodology 來源：[ruvnet/claude-flow](https://github.com/ruvnet/claude-flow)（落後 upstream 2 個 commit）
- 總大小：~150 MB（其中 sparc 佔 78 MB）
