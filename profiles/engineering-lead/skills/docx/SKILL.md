# SKILL.md - docx 專業文件處理

## 身份
- **name**: docx
- **description**: 當用戶想要創建、讀取、編輯或操作Word文檔（.docx文件）時使用此技能。觸發條件包括：任何提及「Word文檔」、「word document」、「.docx」，或請求生成具有格式化（如目錄、標題、頁碼或信頭）的專業文檔。也用於從.docx文件中提取或重新組織內容，在文檔中插入或替換圖像，在Word文件中執行查找和替換，處理修訂或批註，或將內容轉換為精美的Word文檔。

## 核心共識

### .docx 結構
- .docx文件是一個包含XML文件的ZIP存檔
- 讀取/分析：使用pandoc或解包獲取原始XML
- 創建新文檔：使用 docx-js（Node.js）
- 編輯現有文檔：解包 → 編輯XML → 重新打包

### 工具链
- **pandoc**: 文本提取、格式轉換
- **docx npm套件**: 創建新文檔
- **LibreOffice**: PDF轉換（透過scripts/office/soffice.py）
- **Poppler (pdftoppm)**: PDF轉圖像

## 創建新文檔

### docx-js 基本範例
```javascript
const { Document, Packer, Paragraph, TextRun, Header, Footer, 
        PageNumber, HeadingLevel, AlignmentType } = require('docx');
const fs = require('fs');

const doc = new Document({
  styles: {
    default: { document: { run: { font: "Arial", size: 24 } } },
    paragraphStyles: [
      { id: "Heading1", name: "Heading 1", basedOn: "Normal", next: "Normal", quickFormat: true,
        run: { size: 32, bold: true, font: "Arial" },
        paragraph: { spacing: { before: 240, after: 240 }, outlineLevel: 0 } },
      { id: "Heading2", name: "Heading 2", basedOn: "Normal", next: "Normal", quickFormat: true,
        run: { size: 28, bold: true, font: "Arial" },
        paragraph: { spacing: { before: 180, after: 180 }, outlineLevel: 1 } },
    ]
  },
  sections: [{
    properties: {
      page: {
        size: { width: 12240, height: 15840 }, // US Letter
        margin: { top: 1440, right: 1440, bottom: 1440, left: 1440 } // 1" margin
      }
    },
    headers: { default: new Header({ children: [new Paragraph("頁眉")] }) },
    footers: {
      default: new Footer({ children: [new Paragraph({ 
        children: [new TextRun("頁碼 "), new TextRun({ children: [PageNumber.CURRENT] })] 
      })] })
    },
    children: [
      new Paragraph({ heading: HeadingLevel.HEADING_1, children: [new TextRun("標題")] }),
    ]
  }]
});

Packer.toBuffer(doc).then(buffer => fs.writeFileSync("doc.docx", buffer));
```

### 重要規則
- ❌ 絕不使用 `\n` — 使用單獨的 Paragraph 元素
- ❌ 絕不手動插入項目符號字符 — 使用 `LevelFormat.BULLET` 編號配置
- ❌ 絕不使用 `WidthType.PERCENTAGE` — 永遠使用 `WidthType.DXA`
- ✅ PageBreak 必須在 Paragraph 內部
- ✅ ImageRun 需要 `type` 參數（png/jpg等）
- ✅ 表格需要雙重寬度設置：`columnWidths` 和 細胞 `width`
- ✅ 使用 `ShadingType.CLEAR`（不是 SOLID）用於表格著色

### 紙張尺寸（DXA单位，1440 DXA = 1英寸）
| 紙張 | 寬度 | 高度 | 內容寬度（1"邊距） |
|------|------|------|------|
| US Letter | 12,240 | 15,840 | 9,360 |
| A4（默認） | 11,906 | 16,838 | 9,026 |

## 編輯現有文檔

### 步驟
1. **解包**: `python scripts/office/unpack.py document.docx unpacked/`
2. **編輯**: 在 `unpacked/word/` 中編輯XML文件
3. **重新打包**: `python scripts/office/pack.py unpacked/ output.docx --original document.docx`

### XML 修訂標記
```xml
<!-- 插入 -->
<w:ins w:id="1" w:author="Claude" w:date="2025-01-01T00:00:00Z">
  <w:r><w:t>插入的文本</w:t></w:r>
</w:ins>

<!-- 刪除 -->
<w:del w:id="2" w:author="Claude" w:date="2025-01-01T00:00:00Z">
  <w:r><w:delText>刪除的文本</w:delText></w:r>
</w:del>
```

### 智能引號 XML 實體
| 實體 | 字元 |
|------|------|
| &apos; | '（左單引號） |
| &rsquo; | '（右單引號/撇號） |
| &ldquo; | "（左雙引號） |
| &rdquo; | "（右雙引號） |

### 批註標記
```xml
<w:commentRangeStart w:id="0"/>
<w:commentRangeEnd w:id="0"/>
<w:r><w:rPr><w:rStyle w:val="CommentReference"/></w:rPr>
  <w:commentReference w:id="0"/>
</w:r>
```

## 圖像嵌入
1. 添加圖像文件到 `word/media/`
2. 添加關係到 `word/_rels/document.xml.rels`:
   ```xml
   <Relationship Id="rId5" Type=".../image" Target="media/image1.png"/>
   ```
3. 添加內容類型到 `[Content_Types].xml`:
   ```xml
   <Default Extension="png" ContentType="image/png"/>
   ```
4. 在 document.xml 中引用：
   ```xml
   <w:drawing>
     <wp:inline>
       <wp:extent cx="914400" cy="914400"/> <!-- EMU：914400 = 1英寸 -->
       <a:graphic>
         <a:graphicData uri=".../picture">
           <pic:pic>
             <pic:blipFill><a:blip r:embed="rId5"/></pic:blipFill>
           </pic:pic>
         </a:graphicData>
       </a:graphic>
     </wp:inline>
   </w:drawing>
   ```

## 工具總結
| 任務 | 最佳工具 |
|------|----------|
| 文本提取 | pandoc |
| 新文檔創建 | docx (Node.js) |
| PDF轉換 | LibreOffice (scripts/office/soffice.py) |
| 圖像提取 | pdftoppm (Poppler) |
| 驗證 | python scripts/office/validate.py |

## 安裝
```bash
npm install -g docx
```