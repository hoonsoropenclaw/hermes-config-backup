# Test Environment 常見問題排除手冊

## 啟動階段失敗

### port 5432 already in use

**症狀**：
```
Error: bind: address already in use
port is already allocated
```

**原因**：本機有別的 postgres 在跑（可能是別的 docker container、或本機直接裝的）。

**排查**：
```bash
sudo lsof -i :5432
# 或
sudo netstat -tlnp | grep 5432
```

**解法**：
1. 停掉佔用 process：`sudo kill <PID>`
2. 或改 docker-compose.yml 用別的 port：
   ```yaml
   postgres:
     ports:
       - "5433:5432"  # 對外 5433、容器內仍 5432
   ```
   **但**要同步改 application 的 DATABASE_URL 連 5433

### volume permission denied

**症狀**：
```
Error: EACCES: permission denied, open '/var/lib/docker/volumes/...'
```

**原因**：volume 已有別 user 的檔（可能是 root 建、但現在用 hoonsor）。

**排查**：
```bash
ls -la /var/lib/docker/volumes/<volume_name>/_data/
```

**解法**：
1. 刪 volume 重來（會丟資料）：
   ```bash
   docker compose down --volumes
   docker compose up -d
   ```
2. 或 chown 給現有 user：
   ```bash
   sudo chown -R $(id -u):$(id -g) /var/lib/docker/volumes/<volume_name>/_data/
   ```

### depends_on 沒等服務 healthy

**症狀**：
```
api_1     | sqlalchemy.exc.OperationalError: could not translate host name "postgres" to address
```

**原因**：api 容器啟動比 postgres 快、還沒 ready 就連線。

**解法**：在 docker-compose.yml 用 `condition: service_healthy`：
```yaml
services:
  postgres:
    healthcheck:
      test: ["CMD-SHELL", "pg_isready -U postgres"]
      interval: 5s
      timeout: 5s
      retries: 5
  
  api:
    depends_on:
      postgres:
        condition: service_healthy
```

## 運行階段失敗

### connection refused

**症狀**：
```
curl: (7) Failed to connect to localhost port 8000
```

**原因**：服務還在啟動中、或 service crashed。

**排查**：
```bash
docker compose ps            # 看是不是 running
docker compose logs api       # 看啟動 log、有沒有 ERROR
```

**解法**：
1. 等 10 秒重試
2. 若 service exited：看 log 修
3. 若 service restart loop：通常是 healthcheck 寫錯

### DB migration 失敗

**症狀**：
```
sqlalchemy.exc.ProgrammingError: relation "users" does not exist
```

**原因**：DB schema 沒建、migration 沒跑。

**排查**：
```bash
docker compose exec api alembic current
# 看現在在哪個 revision
```

**解法**：
1. 跑 migration：`docker compose exec api alembic upgrade head`
2. 若 migration 有 conflict、可能要 downgrade 再 upgrade：
   ```bash
   docker compose exec api alembic downgrade -1
   docker compose exec api alembic upgrade head
   ```
3. 若 migration 真的壞：rollback 找 engineering-lead

### Seed data 沒進 DB

**症狀**：API 回 200 但 response 是空陣列。

**原因**：seed script 沒跑、跑失敗、或跑的 db 跟 API 連的不同。

**排查**：
```bash
docker compose exec postgres psql -U postgres test_db -c "SELECT COUNT(*) FROM users;"
# 看 seed 進去的筆數
```

**解法**：
1. 重跑 seed：`docker compose exec api python -m scripts.seed_test_data`
2. 若 seed script 寫錯：找 engineering-lead 改

## 資源不足

### no space left on device

**排查**：
```bash
df -h /var/lib/docker
docker system df
```

**解法**：
```bash
docker system prune -a --volumes
# 警告：刪掉所有沒用容器 + volume + image、會影響其他專案
```

### out of memory

**症狀**：
```
docker compose up
ERROR: Cannot start service api: OCI runtime create failed: container_linux.go:380
```

**排查**：
```bash
free -h
docker stats
```

**解法**：
1. 停掉其他吃 RAM 的 process
2. 或降 docker-compose 內每個 service 的 memory limit：
   ```yaml
   services:
     postgres:
       mem_limit: 512m
     redis:
       mem_limit: 256m
     api:
       mem_limit: 512m
   ```

## Sprint 結束 teardown

```bash
docker compose down --volumes
```

**`--volumes` 一定要加**——否則下次 docker compose up 會 mount 舊 volume、看到舊資料。

**若忘記加**：
```bash
docker compose down
docker volume rm <project>_postgres_data
docker compose up -d
```

_Last updated: 2026-06-11（test-environment-bootstrap 附錄）_
