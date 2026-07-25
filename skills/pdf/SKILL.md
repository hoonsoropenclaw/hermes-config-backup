# SKILL.md - PDF 專業處理

## 身份
- **name**: pdf
- **description**: 當用戶想要對PDF文件做任何操作時使用此技能。這包括從PDF讀取或提取文本/表格、合併或拆分多個PDF、旋轉頁面、添加水印、創建新PDF、填寫PDF表單、加密/解密PDF、提取圖像、對掃描的PDF進行OCR使其可搜索。

## 核心工具
- **pypdf**: PDF讀取、寫入、合併、拆分、旋轉
- **pdfplumber**: 文本和表格提取
- **reportlab**: PDF創建
- **Poppler (pdftotext, pdfimages, qpdf)**: 命令行工具
- **pytesseract + pdf2image**: OCR掃描PDF

## 基本操作

### 讀取與提取
```python
from pypdf import PdfReader

reader = PdfReader("document.pdf")
print(f"頁數：{len(reader.pages)}")
text = ""
for page in reader.pages:
    text += page.extract_text()

# 提取表格
import pdfplumber
with pdfplumber.open("document.pdf") as pdf:
    for page in pdf.pages:
        tables = page.extract_tables()
        for table in tables:
            print(table)
```

### 合併與拆分
```python
from pypdf import PdfWriter, PdfReader

# 合併
writer = PdfWriter()
for pdf_file in ["doc1.pdf", "doc2.pdf"]:
    reader = PdfReader(pdf_file)
    for page in reader.pages:
        writer.add_page(page)
with open("merged.pdf", "wb") as output:
    writer.write(output)

# 拆分（每頁一個檔案）
for i, page in enumerate(reader.pages):
    writer = PdfWriter()
    writer.add_page(page)
    with open(f"page_{i+1}.pdf", "wb") as output:
        writer.write(output)
```

### 旋轉頁面
```python
reader = PdfReader("input.pdf")
writer = PdfWriter()
page = reader.pages[0]
page.rotate(90)  # 順時針旋轉90度
writer.add_page(page)
with open("rotated.pdf", "wb") as output:
    writer.write(output)
```

### 水印
```python
from pypdf import PdfReader, PdfWriter

watermark = PdfReader("watermark.pdf").pages[0]
reader = PdfReader("document.pdf")
writer = PdfWriter()

for page in reader.pages:
    page.merge_page(watermark)
    writer.add_page(page)

with open("watermarked.pdf", "wb") as output:
    writer.write(output)
```

### 加密
```python
writer.encrypt("用戶密碼", "所有者密碼")
```

## 創建 PDF

### 使用 reportlab
```python
from reportlab.lib.pagesizes import letter
from reportlab.platypus import SimpleDocTemplate, Paragraph, Spacer, PageBreak
from reportlab.lib.styles import getSampleStyleSheet

doc = SimpleDocTemplate("report.pdf", pagesize=letter)
styles = getSampleStyleSheet()
story = []

title = Paragraph("報告標題", styles['Title'])
story.append(title)
story.append(Spacer(1, 12))
body = Paragraph("這是報告的正文。 " * 20, styles['Normal'])
story.append(body)

doc.build(story)
```

### ⚠️ 重要：Unicode 下標/上標
- ❌ 絕不使用 `₀₁₂₃₄₅₆₇₈₉`、`⁰¹²³⁴⁅⁆⁇` — 內置字體不包含，會渲染為黑框
- ✅ 使用 reportlab XML 標記：`<sub>2</sub>`、`<super>2</super>`

```python
from reportlab.platypus import Paragraph
# 下標
chemical = Paragraph("H<sub>2</sub>O", styles['Normal'])
# 上標
squared = Paragraph("x<super>2</super> + y<super>2</super>", styles['Normal'])
```

## 命令行工具

### Poppler
```bash
# 提取文本
pdftotext input.pdf output.txt
pdftotext -layout input.pdf output.txt  # 帶布局

# 合併
qpdf --empty --pages file1.pdf file2.pdf -- merged.pdf

# 拆分
qpdf input.pdf --pages . 1-5 -- pages1-5.pdf

# 旋轉
qpdf input.pdf output.pdf --rotate=+90:1

# 提取圖像
pdfimages -j input.pdf output_prefix
```

### PDFtk
```bash
# 合併
pdftk file1.pdf file2.pdf cat output merged.pdf

# 拆分
pdftk input.pdf burst

# 旋轉
pdftk input.pdf rotate 1east output rotated.pdf
```

## OCR 掃描 PDF
```python
from pdf2image import convert_from_path
import pytesseract

images = convert_from_path('scanned.pdf')
text = ""
for i, image in enumerate(images):
    text += f"第{i+1}頁：\n"
    text += pytesseract.image_to_string(image)
    text += "\n\n"
```

## 工具總結
| 任務 | 最佳工具 |
|------|----------|
| 合併PDF | pypdf |
| 拆分PDF | pypdf |
| 提取文本 | pdfplumber |
| 提取表格 | pdfplumber |
| 創建PDF | reportlab |
| 命令行合併 | qpdf |
| OCR掃描PDF | pytesseract + pdf2image |
| 提取圖像 | pdfimages |
| 填寫表單 | pdf-lib 或 pypdf |

## 安裝
```bash
pip install pypdf pdfplumber reportlab pdf2image pytesseract
```