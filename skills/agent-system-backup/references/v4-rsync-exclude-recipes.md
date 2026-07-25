# v4 rsync 排除清單完整食譜

> **2026-06-10 從 4 次修補歸納**。任何 v4 設計備份腳本必讀。
> 對應 SKILL.md 第 10.5 段。

## 三層過濾原則

v4 腳本要避開「備份了不該備的東西」必須**同時**滿足三層:

| 層級 | 過濾目標 | 工具 |
|---|---|---|
| **層 1: 大小** | 任何單檔 > 50MB | `--max-size=50m` |
| **層 2: 結構** | `.curator_backups/`、`state.db*`、venv、快取 | `--exclude=...` |
| **層 3: 已知大目錄** | `sparc-methodology/v3/`、`sparc-methodology/ruflo/` | `--exclude='sparc-methodology/v3/'` 等 |

**為何需要三層?** 任何單獨一層都有漏網之魚:
- 只用 `--max-size` → 78MB 整目錄內每檔都 < 50MB、但整體 push 量爆炸
- 只用 `--exclude` → 新增的未知目錄(hermes 未來升級可能加)會漏
- 只用已知大目錄清單 → 過時、hermes 加新 skill 就失效

## 完整 rsync 命令(2026-06-10 v4.4 驗證版)

### 同步 `~/.hermes/skills/` 到 staging(預設)

```bash
rsync -au --delete --max-size=50m \
  --exclude='.git/' \
  --exclude='__pycache__/' \
  --exclude='.archive/' \
  --exclude='.curator_backups/' \
  --exclude='.bundled_manifest' \
  --exclude='.curator_state' \
  --exclude='.hub/' \
  --exclude='.usage.json' \
  --exclude='.claude-plugin/' \
  --exclude='_meta/' \
  --exclude='*.pyc' \
  --exclude='agentdb.rvf' --exclude='agentdb.rvf.lock' \
  --exclude='venv/' \
  --exclude='*.tar.gz' --exclude='*.tar' --exclude='*.zip' --exclude='*.7z' \
  --exclude='package-lock.json' --exclude='yarn.lock' --exclude='pnpm-lock.yaml' \
  --exclude='sparc-methodology/v3/' \
  --exclude='sparc-methodology/ruflo/' \
  "$HERMES_HOME/skills/" "$STAGING/skills/"
```

### 同步 `~/.hermes/profiles/*/` 到 staging(v4.2 新增)

**為何 profiles 排除清單**比 skills 多?**因 profiles 內有完整 agent runtime(state.db、sandbox、logs、curator cache 等),**漏一個 = 整個 agent 還原失敗**。

```bash
rsync -au --delete \
  --exclude='*.bak.*' --exclude='*.lock' --exclude='*.clean.*' \
  --exclude='.curator_backups/' --exclude='.archive/' --exclude='.hub/' \
  --exclude='.usage.json' --exclude='.bundled_manifest' --exclude='.curator_state' \
  --exclude='__pycache__/' --exclude='*.pyc' --exclude='venv/' \
  --exclude='state.db' --exclude='state.db-shm' --exclude='state.db-wal' \
  --exclude='*.tar.gz' --exclude='*.tar' --exclude='*.zip' --exclude='*.7z' \
  --exclude='models_dev_cache.json' --exclude='home/' --exclude='logs/' \
  "$HERMES_HOME/profiles/" "$STAGING/profiles/"
```

**注意**:**profiles rsync 沒加 `--max-size=50m`**(因為 profiles/*/skills/ 已經透過排除清單避免 .curator_backups/skills.tar.gz 進入),但**未來 v5 設計應加保險**。

## 各排除項目的「為什麼」(2026-06-10 驗證)

| 排除項 | 為何排除 | 漏掉的後果 |
|---|---|---|
| `.curator_backups/` | hermes curator 自動備份的 tar.gz,本身就是備份(125MB) | **單一 blob > 100MB、GitHub 拒絕 push** |
| `state.db*` | 對話歷史(SQLite,含敏感 metadata) | Tier 1 公開版會洩漏對話、且單檔可達 200MB+ |
| `models_dev_cache.json` | LLM provider metadata,大且會過期 | 5MB 雜訊、沒備份價值 |
| `home/`, `logs/` | 衍生 runtime 資料 | 10-50MB 雜訊、可 rebuild |
| `sparc-methodology/v3/` | 整體 78MB,內含 wasm/gif/mp4 | GitHub push 容易觸發卡頓、且屬 upstream 可 rebuild |
| `sparc-methodology/ruflo/` | 同上,屬 upstream 套件 | 同上 |
| `*.tar.gz / *.tar / *.zip / *.7z` | 任何壓縮檔都可能是「備份的備份」 | 跟 `.curator_backups/` 同問題、遞迴備份陷阱 |
| `__pycache__/`、`*.pyc` | Python 編譯產物 | 可從源碼 rebuild、純雜訊 |

## v5 設計 checklist(2026-06-10 規劃中)

**If** 設計 v5 備份
**Then** 必加:
1. `--max-size=50m` 到 **所有** rsync 段(不只是 skills)
2. `.curator_backups/` 排除到 **所有** 同步段(預設)
3. 跑備份前 `find ~/.hermes -size +50M -type f` 看有沒有新冒出的大檔
4. 跑備份後 `du -sh .git/objects` 確認 staging 大小合理(< 200MB)

**驗證**:`git verify-pack -v .git/objects/pack/*.pack | sort -k3 -rn | head -3` 看最大 pack 物件,**任何 > 50MB 必查**。
