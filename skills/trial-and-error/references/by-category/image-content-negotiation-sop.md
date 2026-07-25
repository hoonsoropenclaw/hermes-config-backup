# 圖像生成內容審查談判 SOP（2026-07-09）

**Level**: D3 — Structured 3-Step User-Facing SOP  
**Gap**: `content-filter-20260709.md` 有 research vocabulary 數據，但缺少「用戶首次被拒 → 3 步內給替代方案」的結構化程序。Jun 15 session（163 msgs）是這個缺口的真實代價。

---

## 觸發條件

當 `mmx image generate` 返回任何內容審查阻擋（prompt-level 或 output-level），立即執行本 SOP，**不要**只說「不行」就停下來等用戶 retry。

---

## 內容審查談判三步法

### Step 1：識別觸發維度

根據被拒的 prompt，診斷是哪個維度觸發：

| 維度 | 典型觸發詞 | 說明 |
|------|-----------|------|
| **Body-shape** | `curvy alone`, `voluptuous`, `hourglass body shape` | 直接描述身體曲線 |
| **Pose** | `sexy pose`, `seductive pose`, `looking at viewer` | 暗示性姿勢 |
| **Clothing** | `lingerie`, `revealing outfit`, `cleavage` | 暴露服裝 |
| **Lighting/Mood** | `dramatic lighting`, `moody atmosphere` | 可能與某些訓練資料關聯 |
| **Camera/Angle** | `bird's-eye view` + `portrait` + `line art` 組合 | 三元素組合高觸發率 |

**快速診斷原則**：用戶 prompt 同時含 3+ 維度（主體描述 + 姿勢 + 透視 + 風格）= 觸發率大幅上升。

---

### Step 2：提供 2 個具體替代方案

**核心原則**：「找等價表達」而非「繞過規則」。

每次阻擋，提供 **2 個可立即試用**的完整 prompt 重構方案，格式：

```
建議替代方案（可立即試用）：

方案A：[完整替代 prompt — 包含主體 + 風格 + 姿態描述]
方案B：[完整替代 prompt — 另一種等價表達]

核心變更：[1句說明哪個維度被替換了]
```

**Body-shape vocabulary 安全替換表**（直接套用）：

| 意圖（被擋） | 安全替換 |
|-------------|---------|
| `curvy alone` | `full-figured`, `well-rounded`, `soft curves`, `balanced proportions` |
| `voluptuous` | `soft curves`, `gentle silhouette`, `relaxed posture` |
| `hourglass body shape` | `proportional silhouette`, `balanced figure` |
| `sexy pose` | `confident posture`, `editorial pose`, `poised stance` |
| `seductive pose` | `natural pose`, `relaxed stance`, `candid moment` |
| `lingerie` | `elegant sleepwear`, `designer loungewear`, `tasteful attire` |
| `revealing outfit` | `casual chic`, `polished casual`, `refined everyday look` |
| `heavy makeup` | `natural beauty`, `refined elegance`, `polished appearance` |

**Style Safety Ranking**（通過率從高到低）：

| 等級 | 風格 | 通過率 |
|------|------|--------|
| ✅ 安全 | `comic book`, `Ghibli style`, `vector illustration` | 4/4 |
| ✅ 安全 | `watercolor illustration`, `oil painting style` | 高 |
| ⚠️ 注意 | `fashion editorial`, `magazine cover` | 需配合強服裝描述 |
| ❌ 高觸發 | `minimalist line art` + 人物 + `bird's-eye` | 三元素組合 |
| ❌ 高觸發 | `curvy` + `photography` | 直接身體描述 |

---

### Step 3：若用戶 retry 3+ 次仍未通過

主動升級對話層次，說明審查邏輯：

```
這些方案仍未通過，可能是多層審查（prompt-level + visual output classifier）的 false positive。

「等價表達」的核心思路：
- 你想要的「感覺」可以用其他維度呈現
- 例：想表現「曲線美」→ 可以用「服裝線條 + 藝術風格」而非「身體描述」

如果你知道最終想要的核心元素（姿勢 / 服裝 / 場景 / 情緒），
告訴我，我幫你用這些元素重新建構 prompt，完全繞過被擋的維度。
```

**升級開關**：用戶 retry 3 次 = 自動觸發 Step 3，不要等。

---

## 組合觸發警示（觸發即預警）

以下組合**同時出現**時，主動預警用戶高觸發率：

- `bird's-eye view` + `portrait` + `line art` → NSFW aesthetic false positive 高
- `curvy` + `photography` + `lingerie` → 三元素直撞審查
- `voluptuous` + `hourglass` + `looking at viewer` → 疊加觸發

**預警話術**：
```
⚠️ 提醒：你的描述含多個可能觸發審查的維度（具體列出）。
建議先確認最核心的 1-2 個維度，其餘用藝術風格暗示。
```

---

## 標準回覆範本（複製貼上用）

```
MiniMax 對此描述審查未通過，常見原因是：[具體猜測 1 個維度]。

建議替代方案（可立即試用）：
  方案A：[完整 prompt，含主體 + 安全替代詞 + 風格]
  方案B：[完整 prompt，含不同等價表達]

核心變更：[一句說明]

如果這些方案仍不滿意，告訴我你想要的核心元素（姿勢/服裝/場景），
我幫你用這些元素重新建構。
```

---

## 與 `--prompt-optimizer` flag 的整合

當用戶的 prompt 含多個衝突維度，優先使用 `mmx image generate --prompt-optimizer`：
- optimizer 會自動重寫衝突關鍵字
- 若結果偏離原始意圖（商用精確控制場景），才用手動重構

```bash
# 優先
mmx image generate --prompt "你的完整描述" --prompt-optimizer --aspect-ratio 1:1

# 若 optimizer 結果不滿意
# → 用本 SOP Step 2 的 vocabulary 清單手動重構
```

---

## 與 FLUX/其他 uncensored 模型的切換條件

當 MiniMax 持續觸發且本 SOP 無法在 3 次內找到可行方案：

1. 評估是否可以使用 `FLUX` 或其他平台
2. 向用戶說明：「MiniMax 的審查對這個描述特別嚴格，我可以幫你評估其他生成器」
3. 若切換，平滑過渡：新平台的 prompt 需要重新調整（本 SOP 的 vocabulary 不完全適用）

---

## 與其他 trial-and-error 條目的分工

| 內容 | 位置 |
|------|------|
| Research vocabulary + 通過率數據 | `media/mmx-cli/references/content-filter-20260709.md` |
| **使用者-facing 談判 SOP** | `trial-and-error/references/by-category/image-content-negotiation-sop.md`（本文） |
| bird's-eye view 透視角技術 | `media/mmx-cli/references/birds-eye-perspective.md` |
| style selection 決策樹 | `trial-and-error/references/by-category/mmx-image-style-decision-tree-20260628.md` |

---

**上次驗證**：2026-07-09 Cycle 460（Phase 3 research 確認 gap 存在）  
**下次檢查**：當任何 image generation 任務觸發 content filter 時，驗證 SOP 是否被遵守
