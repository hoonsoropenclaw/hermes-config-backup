# SKILL.md - web-artifacts-builder 網頁制品構建器

## 身份
- **name**: web-artifacts-builder
- **description**: 建構強大的前端 claude.ai artifacts，遵循以下步驟：初始化前端 repo → 開發 artifact → 打包成單一 HTML 文件 → 展示給用戶。

**技術棧**: React 18 + TypeScript + Vite + Parcel (bundling) + Tailwind CSS + shadcn/ui

## 設計與風格指南

⚠️ **重要**: 避免被稱為「AI slop」的設計模式：
- 過度居中的佈局
- 紫色漸變
- 統一圓角
- Inter 字體

## 快速開始

### Step 1: 初始化專案

```bash
bash scripts/init-artifact.sh <project-name>
cd <project-name>
```

這會創建一個完整配置的專案，包含：
- ✅ React + TypeScript (via Vite)
- ✅ Tailwind CSS 3.4.1 + shadcn/ui theming system
- ✅ 路徑別名 (`@/`) 配置
- ✅ 40+ shadcn/ui 元件預裝
- ✅ 所有 Radix UI 依賴
- ✅ Parcel 配置用於打包（via .parcelrc）
- ✅ Node 18+ 兼容性

### Step 2: 開發 Artifact

通過編輯生成的檔案來建構 artifact。

### Step 3: 打包為單一 HTML 文件

```bash
bash scripts/bundle-artifact.sh
```

這會創建 `bundle.html` - 一個自包含的 artifact，所有 JavaScript、CSS 和依賴都內聯。此文件可直接在 Claude 對話中作為 artifact 分享。

**要求**: 專案必須在根目錄有 `index.html`。

**腳本功能**:
- 安裝打包依賴（parcel, @parcel/config-default, parcel-resolver-tspaths, html-inline）
- 創建帶路徑別名支援的 `.parcelrc` 配置
- 使用 Parcel 建構（無 source maps）
- 使用 html-inline 將所有資源內聯到單一 HTML

### Step 4: 與用戶分享 Artifact

將打包的 HTML 文件在對話中分享給用戶，這樣他們可以直接查看 artifact。

### Step 5: 測試/視覺化 Artifact（可選）

注意：這是完全可選的步驟。只有在必要或被要求時才執行。

使用可用工具（包括其他 Skills 或內建工具如 Playwright 或 Puppeteer）來測試/視覺化 artifact。通常避免提前測試，因為會增加請求和完成 artifact 可見之間的延遲。在呈現 artifact 之後，如果被要求或出現問題，再進行測試。

## 常用開發任務

### 添加元件
```bash
npx shadcn@latest add [component-name]
```

### 自定義主題
編輯 `tailwind.config.js` 和 `src/styles/globals.css`。

### 添加依賴
```bash
npm install [package-name]
```

## 參考資源

- **shadcn/ui 元件**: https://ui.shadcn.com/docs/components

## 使用時機

- 建構複雜的前端 UI（儀表板、表單、資料視覺化等）
- 需要 React 組件架構的項目
- 希望將結果作為可分享的 HTML artifact

## 限制

- 此技能僅在任務明確匹配上述範圍時使用
- 不要將輸出作為環境特定驗證、測試或專家審查的替代品
- 如需 clarification，請停止並詢問