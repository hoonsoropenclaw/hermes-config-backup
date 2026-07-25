---
name: frontend-design
description: 你是一個前端設計工程師，不是佈局生成器。創建令人難忘的、生產就緒的高品質介面，避免通用的「AI UI」模式。
---

# SKILL.md - frontend-design 前端設計（生產級）

## 身份
- **name**: frontend-design
- **description**: 你是一個前端設計工程師，不是佈局生成器。創建令人難忘的、生產就緒的高品質介面，避免通用的「AI UI」模式。

## 核心原則

### 四個必須滿足的標準
1. **清晰的審美方向**: 有明確的美學立場（如 editorial brutalism、luxury minimal、retro-futurist）
2. **技術正確性**: 真實可運作的 HTML/CSS/JS 或框架代碼
3. **視覺記憶點**: 至少有一個用戶 24 小時後仍會記住的元素
4. **內聚的克制**: 裝飾必須服務美學主題

### 禁忌
- ❌ 預設佈局
- ❌ 按元件設計
- ❌ 「安全」的配色或字體
- ✅ 強烈的觀點，執行良好

## DFII 評估框架

### 維度（1-5 分）
| 維度 | 問題 |
|------|------|
| **美學影響** | 這個方向有多視覺獨特和難忘？ |
| **上下文契合** | 這個美學適合產品、受眾和目的嗎？ |
| **實作可行性** | 這可以用可用技術乾淨地建構嗎？ |
| **性能安全** | 它會保持快速和可訪問嗎？ |
| **一致性風險** | 這可以在螢幕/元件之間維護嗎？ |

### 公式
```
DFII = (Impact + Fit + Feasibility + Performance) − Consistency Risk
```

### 解讀
| DFII | 意義 | 動作 |
|------|------|------|
| **12-15** | 優秀 | 完全執行 |
| **8-11** | 強 | 有紀律地進行 |
| **4-7** | 有風險 | 減少範圍或效果 |
| **≤ 3** | 弱 | 重新思考美學方向 |

## 設計思考階段

### 1. 目的
- 這個介面應該實現什麼行動？
- 是說服性的、功能性的、探索性的還是表達性的？

### 2. 語氣（選擇一個主要方向）
- Brutalist / Raw
- Editorial / Magazine
- Luxury / Refined
- Retro-futuristic
- Industrial / Utilitarian
- Organic / Natural
- Playful / Toy-like
- Maximalist / Chaotic
- Minimalist / Severe

⚠️ 不要混合超過 **兩個** 方向。

### 3. 差異化錨點
回答：「如果這個被截圖且標誌被移除，別人如何識別它？」
這個錨點必須在最終 UI 中可見。

## 美學執行規則

### 字體
- 避免系統字體和 AI 默認值（Inter, Roboto, Arial 等）
- 選擇：
  - 1 個表現力字體用於展示
  - 1 個節制的正文字體
- 使用字體結構化（比例、節奏、對比）

### 顏色與主題
- 承諾一個 **主導顏色故事**
- 僅使用 CSS 變量
- 偏好：
  - 一個主導色調
  - 一個強調色
  - 一個中性系統
- 避免均勻平衡的調色板

### 空間構圖
- 有意地打破網格
- 使用：
  - 不對稱
  - 重疊
  - 負空間或控制密度
- 白空間是設計元素，不是缺失

### 動畫
- 動畫必須：
  - 有目的
  - 稀疏
  - 高影響
- 偏好：
  - 一個強烈的進入序列
  - 一些有意義的懸停狀態
- 避免裝飾性微動作垃圾

### 紋理與深度
- 適當使用：
  - 噪聲/顆粒覆蓋
  - 漸變網格
  - 層疊半透明
  - 自定義邊框或分隔線
  - 有敘事意圖的陰影（不是默認值）

## 實作標準

### 代碼要求
- 乾淨、可讀、模組化
- 無死樣式
- 無未使用的動畫
- 語義 HTML
- 預設可訪問（對比度、焦点、鍵盤）

### 框架指導
- **HTML/CSS**: 偏好原生特性、現代 CSS
- **React**: 功能元件、可組合樣式
- **動畫**: CSS 優先；只有正當時使用 Framer Motion

### 複雜度匹配
- 極繁主義設計 → 複雜代碼（動畫、層）
- 極簡主義設計 → 極精確的間距和類型

不匹配 = 失敗。

## 輸出結構

### 1. 設計方向摘要
- 美學名稱
- DFII 分數
- 關鍵靈感（概念性的，不是視覺抄襲）

### 2. 設計系統快照
- 字體（帶原理）
- 顏色變量
- 間距節奏
- 動畫理念

### 3. 實作
- 完整可運作的代碼
- 只有在意圖不明顯的地方添加註釋

### 4. 差異化 callout
明確說明：
> 「這通過做 X 而不是 Y 來避免通用 UI。」

## Taste-Skill 整合（首選框架）

**重要**：對於 landing page、portfolio、editorial 類型的 Web 開發任務，優先使用 `design-taste-frontend`（taste-skill）而非本技能的直接代碼輸出。

### 三轉盤框架（taste-skill）
每次載入 skill_view(name='design-taste-frontend') 後，針對任務設定三個維度：
- **VARIANCE**（1-10）：佈局變化程度。1=完美對稱，10=藝術化混沌
- **MOTION**（1-10）：動畫強度。1=靜態，10=電影感/物理引擎
- **DENSITY**（1-10）：視覺密度。1=畫廊級留白，10=儀表板級密集

**基線值**：`8 / 6 / 4`（landing page 預設）

### 觸發 taste-skill 的條件
- 使用者要求製作「網頁」、「landing page」、「作品集」
- 提到「不要模板感」、「要有品味」、「避免 AI 感」
- 任務屬於 landing / portfolio / editorial / redesign 類型

### 搭配方式
- `design-taste-frontend`：主要實作框架
- `soft-design`：當使用者要求「高端精緻」、「安靜奢華」時
- `minimalist-ui`：當要求「極簡」、「Notion/Linear 風格」時
- `redesign-skill`：當任務是「改造現有網站」時

## 整合其他技能
- **page-cro**: 佈局層次和轉換流
- **copywriting**: 字體和消息節奏
- **marketing-psychology**: 視覺說服和偏差對齊
- **branding**: 視覺身份一致性
- **ab-test-setup**: 變體安全設計系統

## 操作員檢查清單

在最終確定輸出之前：
- [ ] 清晰的審美方向已說明
- [ ] DFII ≥ 8
- [ ] 一個令人難忘的設計錨點
- [ ] 無通用字體/顏色/佈局
- [ ] 代碼匹配設計雄心
- [ ] 可訪問和高性能
- [ ] 若為 landing/portfolio/editorial 類型，已考慮採用 taste-skill 三轉盤框架

## 禁忌模式（立即失敗）
❌ Inter/Roboto/系統字體
❌ 紫白 SaaS 漸變
❌ 默認 Tailwind/ShadCN 佈局
❌ 對稱的、可預測的部分
❌ 過度使用的 AI 設計比喻
❌ 無意圖的裝飾

如果設計可以被誤認為是模板 → 重啟。

## 交付前的常見交互 bug（不是設計問題，是程式 bug，會直接讓使用者說「點了沒反應」）

### 0. Topnav anchor 連結到不存在的 `id`（最隱蔽、最高頻 — 寫完先全文 grep 一次）

症狀：使用者點 topnav 的「怎麼用」「關於」「API」等按鈕**完全沒反應**,URL hash 有更新但頁面沒捲動。**最容易先檢查**的 bug。

根因：寫 topnav 時加了 `<a href="#how-it-works">怎麼用</a>`,但**從來沒寫對應的 `<section id="how-it-works">` 在 HTML 裡**。瀏覽器找不到 target 就靜默放棄,沒有 console error 提示。

為什麼這個 bug 特別容易出現:
- 寫 topnav 時心智在「導覽結構」,很容易只先列好連結
- 寫 section 內容時如果順序顛倒（先寫 nav、後寫內容）、或中途插入新章節忘了對應 nav,bug 就誕生
- 瀏覽器**完全不會報錯** — 不像 JS 語法錯會在 console 紅字,這是「靜默失敗」,只能靠使用者點擊回報

**預防 — 寫完 topnav 後立刻跑這個 grep 一次**:

```bash
# 抓出所有 anchor 的目標
grep -oE 'href="#[^"]+"' index.html | sort -u

# 抓出所有 id
grep -oE 'id="[^"]+"' index.html | sort -u

# 比對 — 任何 href="#xxx" 沒有對應 id="xxx" 都是 bug
```

或者寫一個最簡單的 5 行 self-check script 在 build/dev server 啟動時跑:

```js
// 在 index.html 最底下 <script> 加
document.querySelectorAll('a[href^="#"]').forEach(a => {
  const id = a.getAttribute('href').slice(1);
  if (id && !document.getElementById(id)) {
    console.warn(`Broken anchor: <a href="#${id}"> 但找不到對應元素`);
  }
});
```

驗證方式:寫完網站後,**用 headless browser 對每個 topnav 按鈕跑一次 click**,看 URL hash 有更新 + 目標元素在 viewport 內:

```js
// 點完後 console 查驗
JSON.stringify({
  url: location.href,
  hash: location.hash,
  scroll_y: window.scrollY,
  target_in_view: (() => {
    const id = location.hash.slice(1);
    if (!id) return null;
    const r = document.getElementById(id).getBoundingClientRect();
    return r.top >= 0 && r.top < window.innerHeight;
  })()
})
```

**If→Then**:
- **If** 寫完 topnav 想驗證所有連結 **Then** `grep -oE 'href="#[^"]+"' index.html` 跟 `grep -oE 'id="[^"]+"' index.html` 對一次
- **If** 使用者回報「點 XXX 沒反應」**Then** 先查 `href="#xxx"` 跟 `id="xxx"` 配對（這比 sticky-nav / dynamic-render 更常見,且最簡單修）
- **If** 發現某個 anchor 沒對應 id **Then** 不要只刪 anchor — anchor 是設計意圖,缺的是 section 內容;補上 section 才能保留「使用者點下去有東西看」的期待

### 1. Sticky nav + anchor link + 動態渲染的組合炸彈

症狀：使用者點 topnav 的 `#session`、`#info` 等錨點「沒反應」或「感覺沒換位置」。最常見場景：頁面是動態渲染（filter / search / lazy load），且 header 是 `position: sticky`。

三個獨立 bug 疊在一起：

1. **sticky nav 擋住 section 頂端**：預設 `scroll-margin-top: 0` 會讓 section 標題被 60-80px 高的 sticky bar 蓋住，使用者感覺「沒捲到」。修法：在每個 anchor target 上加 `scroll-margin-top: <nav-height>`（或在 `html { scroll-padding-top: ... }` 全域設）。
2. **動態渲染時目標 section 不在 DOM**：篩選器把頁面縮成單一分類時，其他分類的 `<section id="...">` 不存在，瀏覽器 `a[href^="#"]` 點下去找不到元素就直接放棄。修法：攔截 topnav 的 `click`，先 reset filter / 搜尋詞再 re-render，最後才 `scrollIntoView`。
3. **網址列 hash 沒更新**：純 `scrollIntoView` 不會更新 `location.hash`，使用者 reload 後定位會丟失。修法：`history.replaceState(null, '', '#' + id)`。

最小可工作樣板（純 JS，沒有 framework）：

```js
document.addEventListener('click', e => {
  const a = e.target.closest('a[href^="#"]');
  if (!a) return;
  const id = a.getAttribute('href').slice(1);
  if (!id) return;
  // 視需要先 force-render 讓 target 存在
  // e.g. activeCategory = 'all'; $q.value = ''; render();
  const target = document.getElementById(id);
  if (target) {
    e.preventDefault();
    target.scrollIntoView({ behavior: 'smooth', block: 'start' });
    history.replaceState(null, '', '#' + id);
  }
});
```

CSS 端配套：
```css
html { scroll-behavior: smooth; scroll-padding-top: 80px; }  /* = sticky nav 高度 */
section[id] { scroll-margin-top: 80px; }                       /* 雙保險 */
```

驗證方式：開 DevTools，切到某個 filter 後用 `document.getElementById('target-id')` 檢查目標是否存在；用 `getBoundingClientRect().top` 確認捲動後頂端落在 `scroll-margin-top` 的位置（不是負值也不是 0）。

### 2. `navigator.clipboard.writeText` 在 file:// 或非安全 context 會被靜默擋掉

症狀：點「複製」按鈕什麼反應都沒有。headless 工具（例如 camofox、Browserbase 沒開 proxy）也會 401。

修法：每次寫剪貼簿的 handler 都要有 fallback：

```js
async function copy(text, btn) {
  try {
    await navigator.clipboard.writeText(text);
  } catch {
    // 非安全 context（file://、http://）或被擋。降級方案：
    const ta = document.createElement('textarea');
    ta.value = text;
    ta.style.position = 'fixed';
    ta.style.opacity = '0';
    document.body.appendChild(ta);
    ta.select();
    try { document.execCommand('copy'); } catch {}
    document.body.removeChild(ta);
  }
  // 視覺回饋（避免使用者以為沒點到）
  if (btn) { btn.classList.add('copied'); /* setTimeout 還原 */ }
}
```

### 3. 任何有搜尋框的頁面：鍵盤 `/` 跳搜尋、Esc 清空是基本款

```js
document.addEventListener('keydown', e => {
  if (e.key === '/' && document.activeElement !== searchInput) {
    e.preventDefault(); searchInput.focus();
  } else if (e.key === 'Escape' && document.activeElement === searchInput) {
    searchInput.value = ''; searchInput.blur(); render();
  }
});
```

這三條是「設計上 OK 但被使用者一句話打槍」的高頻來源。寫完一頁面後務必手動點過一輪。