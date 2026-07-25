# scrapling Cloudflare Benchmark 驗證缺口（2026-06-29）

## 現況

`scrapling` SKILL.md 記錄了 StealthyFetcher 可繞過 Cloudflare Turnstile，但：
1. **從未對真實 Cloudflare 保護站點執行實測**
2. SKILL.md 宣稱「31 個目標零封鎖」但無 benchmark 數據
3. API 修正在 `scrapling-api-usage-20260629.md`，但 benchmark 仍空白

## 待驗證 Action Items

```bash
# 1. 基本驗證（nowsecure.nl 是已知 Cloudflare 保護站點）
uv venv /tmp/se --python 3.12 && uv pip install --python /tmp/se/bin/python scrapling
/tmp/se/bin/python -c "
from scrapling.fetchers import StealthyFetcher
s = StealthyFetcher()
r = s.get('https://nowsecure.nl')
print('status:', r.status)
print('html[:200]:', r.html[:200])
"

# 2. Camofox 對比（Firefox headless）
curl -s http://localhost:9377/health
# 若 camofox 可用，用相同 URL 測試成功率
```

## 抉擇樹更新準則

| 測試結果 | 更新方向 |
|---------|---------|
| StealthyFetcher 成功率 > 70% | 在 SKILL.md 提升 StealthyFetcher 優先級 |
| StealthyFetcher 成功率 < 30% | Fallback 到 camofox/nodriver，文件更新抉擇樹 |
| 兩者皆失敗 | nodriver（若可用）+ 記錄失敗 target |

## If→Then

- **If** 需對 Cloudflare 站點抓取 **Then** 先用 `nowsecure.nl` 測試 StealthyFetcher，不行再 fallback
- **If** benchmark 完成 **Then** 更新 SKILL.md 抉擇樹並移除本文件的「未驗證」標記
