# scrapling Cloudflare 實測缺口（2026-06-29 新增）

## 缺口背景

scrapling SKILL.md（mtime 2026-06-14）記錄了 nodriver 底層架構與 Cloudflare 繞過理論，但：
1. **從未對真實 Cloudflare 保護站點執行實測驗證**
2. SKILL.md 提及「理論上可繞過」但沒有 benchmark 數據支撐
3. 2026-06-29 的 API 修正（scrapling-api-usage-20260629.md）只修了 Python 語法錯誤，未補 benchmark 驗證

## 現有文件狀態

| 文件 | mtime | 內容 |
|------|-------|------|
| `skills/scrapling/SKILL.md` | 2026-06-14 | 理論、架構、已知限制 |
| `scrapling-api-usage-20260629.md` | 2026-06-29 | API 修正（configure() 錯誤） |
| **實測 benchmark** | ❌ 不存在 | 空白 |

## 理論軌：已知的已知

根據 SKILL.md：
- `nodriver` 使用 CDP 直接通訊，繞過 Selenium/Playwright 指紋
- 理論 benchmark：31 個 Cloudflare 目標零封鎖
- scrapling = nodriver + CSS selector layer
- `StealthyFetcher` 提供額外指紋混淆

## 本地知識缺口（未驗證）

1. **scrapling 的 `StealthyFetcher` 對 Cloudflare 保護站點的實際成功率是多少？**
2. **與 camofox（Firefox headless）相比，scrapling 的成功率/速度如何？**
3. **SKILL.md 提到的「31 個目標 benchmark」是否可重現？**

## If→Then

**If** 需要對 Cloudflare 保護站點執行網頁爬蟲 **Then** 先用 scrapling 的 `StealthyFetcher` 測試，不行再 fallback 到 camofox

**If** scrapling 失敗但 camofox 成功 **Then** 這代表 scrapling 的 stealth 宣稱需要實測驗證，不要假設可用

**If** 要建立 Cloudflare 爬蟲的 benchmark **Then** 使用 `https://nowsecure.nl`（已知 Cloudflare 保護站點）做基準測試

## 待驗證（Action Items）

- [ ] 對 `https://nowsecure.nl` 執行 scrapling + StealthyFetcher 實測
- [ ] 對同站點執行 camofox 對比實測
- [ ] 建立 benchmark 結果文檔

## 相關條目

- [[scrapling-api-usage-20260629.md]] — API 修正（Python 語法）
- [[browser-automation#scrapling-vs-camofox]] — 尚未填寫（預留給 benchmark 結果）
- `skills/scrapling/SKILL.md` — 理論文件
