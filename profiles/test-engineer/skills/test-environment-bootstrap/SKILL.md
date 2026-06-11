---
name: test-environment-bootstrap
description: "從 arch-<slug>.md 的 docker-compose 段落建立 test environment、跑 smoke test、確認所有服務 healthy。test-engineer 跑任何測試前必走。"
version: 1.0.0
author: hoonsor
tags: [test, environment, docker, smoke-test, prerequisites]
---

# Test Environment Bootstrap Skill

從 `arch-<slug>.md` 讀取 docker-compose 段落、自動建立 test environment、跑 smoke test、確認所有服務 healthy。**test-engineer 跑任何測試前必走 SOP**——沒建好 test env、跑再多測試也是假安全感。

## 觸發情境

- 收到 `sprint-<N>-report.md` 從 engineering-lead
- 準備跑 integration / E2E / performance test 前
- test-env 掛了要重起
- 使用者明確說「建 test env」「起服務」「test env 還在嗎」

## 為什麼這個 skill 必走

沒建 test env 跑測試的後果：
- 跑 unit test 過 ≠ 跑整合測試也過（缺 DB）
- 跑 E2E 連不上 backend（容器沒起）
- performance baseline 是錯的（環境資源被其他 process 佔用）
- bug 報告「在我環境能跑」無法重現（其他環境差太多）

## 標準流程（6 步）

### Step 1 — 讀 arch 找 docker-compose 段落

- 讀 `~/.hermes/handoff/<project-slug>/arch-<slug>.md` §「部署拓樸」段
- 找 `docker-compose.yml` 路徑（通常在 `arch/<project>/docker-compose.yml`）
- 列出需要的服務（postgres / redis / api / frontend / nginx / ...）
- 確認 docker-compose 版本（v2 vs v3，影響 CLI 指令）
- 確認有沒有 custom network / volume / depends_on

**產出**：`test-env-design.md`（每個服務清單 + port + depends_on）

### Step 2 — 確認本機環境

- `docker --version`：確認 Docker Engine 有裝
- `docker compose version`：確認 v2 CLI（不是 v1 `docker-compose`）
- `docker ps`：確認 daemon 在跑
- `df -h /var/lib/docker`：確認有 5GB+ 空間
- `free -h`：確認有 2GB+ RAM（test env 要起 4-5 個容器）

**如果任一失敗**：寫進 `test-env-blockers.md`、**不要**繼續建（建了也跑不起來）

### Step 3 — 起 test env

```bash
cd <path-to-docker-compose>
docker compose up -d
```

**驗證**：
- `docker compose ps`：所有 service 應該 `running` (不是 `starting` / `exited`)
- `docker compose logs --tail=50 <service>`：看啟動 log、找 ERROR / panic

**常見失敗**：
- port 被佔（`bind: address already in use`）
- volume permission 錯誤（`permission denied`）
- depends_on 沒等服務 healthy 就起下一個（用 `condition: service_healthy` 修）

### Step 4 — 跑 smoke test

每個 service 都跑、不能只看 container status：

```bash
# Postgres
docker compose exec postgres psql -U postgres -c "SELECT version()"
# Redis
docker compose exec redis redis-cli ping  # 預期: PONG
# API
curl -f http://localhost:8000/health       # 預期: {"status": "ok"}
# Frontend
curl -f http://localhost:3000/             # 預期: HTML 200
# DB migration
docker compose exec api alembic upgrade head
```

**如果任一失敗**：檢查 log、修補、**不要跳過**。

### Step 5 — 跑 test seed data init

- 讀 `arch-<slug>.md` §「測試資料」段
- 跑 seed script（從 arch 抓路徑）
- 驗證 seed 進 DB

```bash
docker compose exec api python -m scripts.seed_test_data
# 或
psql -h localhost -U postgres test_db < seed.sql
```

**產出**：`test-env-status.md`（每個 service 狀態、smoke test 結果、seed 成功筆數）

### Step 6 — 寫 test-env-status.md

```markdown
# Test Environment Status (Sprint <N>)

**起環境時間**：YYYY-MM-DD HH:MM
**預期壽命**：8 小時（sprint 結束後 teardown）

## Service Status
| Service | Port | Status | Smoke Test | Log Errors |
|---------|------|--------|-----------|-----------|
| postgres | 5432 | ✅ healthy | SELECT version() OK | 0 |
| redis | 6379 | ✅ healthy | PONG | 0 |
| api | 8000 | ✅ healthy | /health 200 | 0 |
| frontend | 3000 | ✅ healthy | GET / 200 | 0 |

## Seed Data
- Users: 10 個
- Posts: 50 篇
- Tags: 15 個

## Known Limitations
- 沒啟 nginx（sprint 不測 production routing）
- 沒啟 CDN（sprint 不測 image optimization）
- 記憶體限制 4GB
```

## 常見問題排除

| 問題 | 原因 | 解法 |
|------|------|------|
| `port 5432 already in use` | 本機有別的 postgres | `lsof -i :5432` 找誰佔、停掉 |
| `no space left on device` | Docker 磁碟滿 | `docker system prune -a` 清掉沒用容器 |
| `connection refused` | 服務還在啟動中 | `sleep 10 && docker compose ps` 等 |
| `permission denied on volume` | volume 已有別 user 的檔 | `docker volume rm <name>` 重來 |

## Sprint 結束時 teardown

```bash
docker compose down --volumes
```

**注意**：用 `--volumes` 會**刪掉所有 test 資料**——下次 sprint 要重新 seed。

## If→Then 規則

- **If** 收到 `sprint-<N>-report.md` **Then** 立刻跑 test-environment-bootstrap、不能在沒 test env 狀態下跑測試
- **If** test-env-status.md 顯示任一 service 不 healthy **Then** 立刻 teardown 重來、不要硬跑測試
- **If** 收到「在我環境能跑」的 bug 報告 **Then** 要求重跑 test-environment-bootstrap、看實際 test env 是不是跟聲稱的一致

_Last updated: 2026-06-11（test-engineer SOP）_
