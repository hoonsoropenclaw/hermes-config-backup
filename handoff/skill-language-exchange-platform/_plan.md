# Architect Worker 派遣計劃 — v3_4_workers 模式

> **模式宣告**:`[MODE=speed]` — 4 子代理完全平行
> **任務**:技能/語言交換平台 Step 3-6
> **時間預估**:15-25 分鐘
> **Token 預估**:200-320K(4 子代理 + 主 session 整合)

## 5 個架構盲點的預設建議(worker 拿這個當技術選型基準)

| # | 盲點 | 預設建議 |
|---|------|---------|
| 1 | 政府證件儲存 | 30 分鐘硬刪 + 遮罩證件號 |
| 2 | 跨國匯率 | 固定 USD 錨點(MVP) |
| 3 | 活體檢測 | 簡單眨眼 + 人工 review |
| 4 | 影片儲存 | Supabase Storage + Cloudflare(MVP) |
| 5 | 12 歲學員 | MVP 不開放 |

> Worker **必須**用這 5 個預設建議(若要改要明確標 [架構決策待釐清] + 為何改)

## Worker 派遣清單(4 個完全平行)

### Worker A: 容器圖 + 技術選型(Step 3)
- **寫到**:`_raw/architect/worker-A-container.md`
- **產出**:C4 Level 2 容器圖(Mermaid graph TB) + 技術選型表(每個容器:為何選 + 替代 + 何時改)
- **必含**:前端 / 後端 / DB / Cache / Storage / Worker Queue / 14 個外部整合

### Worker B: 元件圖(Step 4)
- **寫到**:`_raw/architect/worker-B-components.md`
- **產出**:C4 Level 3 元件圖(Mermaid graph TB) + 元件職責表
- **聚焦**:Auth / User / SkillTag / Matching / Order / PointEscrow / Review / Notification + 各個 Service
- **限制**:元件 5-8 個、對應 Must-have User Story

### Worker C: 資料庫 schema(Step 5)
- **寫到**:`_raw/architect/worker-C-database.md`
- **產出**:Mermaid erDiagram + 8 張表規格(users / skill_tags / matchings / orders / point_ledger / reviews / media_metadata / audit_log) + 索引策略 + 1 年資料量估算
- **必含**:點數帳本的雙向凍結/撥款、跨國匯率表、媒體 metadata(原始檔 30 分鐘硬刪)

### Worker D: API 規格(Step 6)
- **寫到**:`_raw/architect/worker-D-api.md`
- **產出**:RESTful 端點清單(/auth/* /users/* /matchings/* /orders/* /reviews/* /media/* /points/*) + 認證(JWT + refresh) + 分頁(cursor) + 限流 + 錯誤碼 + 1 個 WebSocket(/ws/chat)
- **限制**:每個端點含 Method/Path/認證/請求/回應/錯誤碼

## 對齊契約(3 個 worker 之間要對得起來)

| 契約 | 來源 | 必須對齊 |
|------|------|---------|
| 容器命名 | Worker A | Worker B 的元件必須住在 A 定義的容器內 |
| 服務命名 | Worker B | Worker D 的 API 路徑必須對得起 B 定義的 Service |
| 資料表命名 | Worker C | Worker D 的 API 回應欄位必須對得起 C 的 schema |

## 整合順序(主 session 跑)

1. 等 4 個 worker 全部完成(用 `process(action='wait')` 監聽)
2. **先讀 Worker A 的容器圖 + Worker C 的 schema + Worker D 的端點**—— 找命名不一致的地方
3. **再讀 Worker B 的元件圖**—— 確認元件住在對的容器
4. **寫整合的 3 份文件**:
   - `architecture.md`(容器 + 元件 + 部署)
   - `database-schema.md`(整合 C 的內容)
   - `api-spec.md`(整合 D 的內容)
5. **每份文件最後一節**「1 小時上手 checklist」

## 失敗處理

- Worker 失敗 → 重試 1 次 → 還是失敗就主 session 自己補
- Worker 寫到 sandbox 隔離目錄 → `find ~/.hermes -name "worker-*.md"` 撈
- Worker 寫空檔 → 視為失敗
- Worker 產出格式亂 → 主 session 自己整理

## 重要限制(給所有 worker)

- ✅ 用**絕對路徑** `/home/hoonsoropenclaw/.hermes/handoff/...` 寫檔
- ✅ 用 `web_search` / `web_extract` 抓資料(若有需要)
- ✅ 必讀 `~/.hermes/handoff/skill-language-exchange-platform/architecture-step1-2.md` 的 §1.5 盲點清單
- ✅ 完成後**只輸出 "DONE"**,不要貼詳細結果
- ❌ 不要做架構決策(用 5 個預設建議就好,若要改要明確標)
- ❌ 不要新增 Persona / User Story(那是上游的工作)
- ❌ 失敗時輸出 `FAILED: <原因>`
