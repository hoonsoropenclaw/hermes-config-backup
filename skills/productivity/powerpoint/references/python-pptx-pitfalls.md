# python-pptx 投影片生成：常見版面坑與 LibreOffice 渲染陷阱

> 本檔專門針對**用 python-pptx 從零生成簡報**的情境，補 `SKILL.md` 與 `editing.md` 沒涵蓋的版面座標與中文化陷阱。pptxgenjs 的使用者請看 `pptxgenjs.md`。

## 0. 安裝與基本環境

```bash
pip install python-pptx
# 視覺自檢需要（Linux）
which soffice libreoffice pdftoppm
# 都沒裝 → apt install libreoffice poppler-utils
```

中文字型在 Linux server 常不存在；選字型時要用**使用者電腦上有的字**（如「微軟正黑體」「Noto Sans TC」），LibreOffice 找不到會自動 fallback，但渲染結果會跟 PowerPoint 不一樣。

## 1. 16:9 標準尺寸（一定要先設）

```python
from pptx import Presentation
from pptx.util import Inches

prs = Presentation()
prs.slide_width = Inches(13.333)   # 16:9
prs.slide_height = Inches(7.5)
```

預設是 4:3（10 × 7.5 inch）。**忘了設寬度 → 所有「置中」算式都會偏**。

## 2. ⭐ 中文 run 必加 East-Asian typeface hint

只用 `run.font.name = "微軟正黑體"` 在 PowerPoint 顯示正常，但 LibreOffice 渲染 PDF 時常常變方框或 fallback 到醜字。**必須額外設定 a:ea typeface**：

```python
from pptx.oxml.ns import qn
from lxml import etree

def style_run(run, *, font="微軟正黑體", size=18, color=RGBColor(0,0,0), bold=False):
    run.font.name = font
    run.font.size = Pt(size)
    run.font.bold = bold
    run.font.color.rgb = color
    # East-Asian 字型 hint）
    rPr = run._r.get_or_add_rPr()
    ea = rPr.find(qn('a:ea'))
    if ea is None:
        ea = etree.SubElement(rPr, qn('a:ea'))
    ea.set('typeface', font)
```

少了這一段的徵兆：PowerPoint 看正常，但 `soffice --convert-to pdf` 出來的圖片中文變方框或豆腐字。

## 3. ⭐⭐⭐ LibreOffice 渲染時 `vertical_anchor` 不一定生效

**症狀**：`text_frame.vertical_anchor = MSO_ANCHOR.MIDDLE` 在 PowerPoint 預覽正常，但 `soffice --convert-to pdf` 出來的 PDF 裡文字仍是 top-anchored。

**根因**：LibreOffice 對 vertical_anchor 的實作跟 PowerPoint 不一致；尤其是 textbox 高度比內容大很多時，LibreOffice 直接 top-align。

**解法**：不要依賴 vertical_anchor，自己算座標：

```python
# 投影片 7.5" 高，內容區 2.0"–7.0"，中間 ≈ 4.5"
# 4 條 22pt + 12pt space_after 的 bullet ≈ 高度 2.0"
# 因此起始 y = 4.5 - 2.0/2 = 3.5"
tb = slide.shapes.add_textbox(Inches(0.7), Inches(3.5), SLIDE_W - Inches(1.4), Inches(2.0))
```

或乾脆 top-anchor + 讓 textbox 從緊鄰標題底開始往下排：

```python
tb = slide.shapes.add_textbox(Inches(0.7), Inches(2.0), SLIDE_W - Inches(1.4), Inches(5.0))
tf.vertical_anchor = MSO_ANCHOR.TOP
```

**自檢訊號**：如果你做一頁只有 3 條 bullet 的 slide，渲染出來 bullet 集中在上半部但 bottom 50% 是空白，這就是 top-anchor 行為。

## 4. ⭐⭐ 文字方塊的 `top` 參數 bug

**症狀**：呼叫 `add_bullets(slide, items, top=Inches(4.0))` 結果 bullet 還是出現在 `Inches(2.0)` 的位置。

**根因**：寫了 `tb = slide.shapes.add_textbox(Inches(0.7), Inches(2.0), ...)` 寫死 y 座標，忽略了傳入的 `top` 參數。

**解法**：永遠用參數傳入的 top：

```python
def add_bullets(slide, items, top=Inches(2.0)):  # 預設值只是 fallback
    tb = slide.shapes.add_textbox(Inches(0.7), top, SLIDE_W - Inches(1.4), Inches(5.0))
```

**自檢訊號**：CTA 頁有「橘色方塊」與「bullet 條列」時，兩者重疊——通常就是某個函式忽略了 `top`。

## 5. ⭐ CTA 區塊與 bullet 一定要分區

**症狀**：請示頁放了 1.5" 高的橘色 CTA 矩形 + 4 條 bullet，結果 bullet 跟矩形互相覆蓋。

**解法**：CTA 區塊固定高度（如 1.0"），bullet 從 CTA 底 + 0.4" 間距開始：

```python
if is_request:
    # CTA box: y 1.9–2.9（h=1.0）
    box = slide.shapes.add_shape(MSO_SHAPE.ROUNDED_RECTANGLE,
                                 Inches(0.8), Inches(1.9), SLIDE_W - Inches(1.6), Inches(1.0))
    box.text_frame.text = "📌 請示事項：核撥 114 年經費 55,000 元"
    # bullet 從 y 3.3 起
    add_bullets(slide, items, top=Inches(3.3))
```

## 6. ⭐ 16:9 slide 不要把物件塞到 y > 7.0"

預留 0.5" 給 footer（頁碼 / 浮水印）。如果加 footer：

```python
def add_footer(slide, page_num, total):
    txt = slide.shapes.add_textbox(Inches(0.5), SLIDE_H - Inches(0.45), Inches(6), Inches(0.3))
    # ...
```

底部內容 `y + height > 7.0"` 會撞到 footer。

## 7. 完整最小可運行範例

```python
from pptx import Presentation
from pptx.util import Inches, Pt
from pptx.dml.color import RGBColor
from pptx.enum.shapes import MSO_SHAPE
from pptx.enum.text import PP_ALIGN, MSO_ANCHOR
from pptx.oxml.ns import qn
from lxml import etree

def style_run(run, *, font="微軟正黑體", size=18, color=RGBColor(0,0,0), bold=False):
    run.font.name = font
    run.font.size = Pt(size)
    run.font.bold = bold
    run.font.color.rgb = color
    rPr = run._r.get_or_add_rPr()
    ea = rPr.find(qn('a:ea'))
    if ea is None:
        ea = etree.SubElement(rPr, qn('a:ea'))
    ea.set('typeface', font)

prs = Presentation()
prs.slide_width = Inches(13.333)
prs.slide_height = Inches(7.5)

slide = prs.slides.add_slide(prs.slide_layouts[6])
tb = slide.shapes.add_textbox(Inches(0.6), Inches(0.5), Inches(12), Inches(1.0))
p = tb.text_frame.paragraphs[0]
r = p.add_run()
r.text = "標題"
style_run(r, size=28, bold=True, color=RGBColor(0x2E, 0x5A, 0x4F))

prs.save("out.pptx")
```

## 8. 視覺自檢的固定 SOP（不可省略）

```bash
# 1. pptx → pdf
soffice --headless --convert-to pdf out.pptx

# 2. pdf → png（每頁一張，r=80 夠用）
pdftoppm -png -r 80 out.pdf page

# 3. 用 vision 模型或瀏覽器逐頁看
#    必查：溢出、重疊、空白超過 40%、字型 fallback
```

LibreOffice headless 第一次跑會建 user profile，慢 5–10 秒；之後會 cache。

## 9. 已知會被自評抓出的缺陷（給行政簡報特別提醒）

行政簡報使用者會特別在意：
- **底部留白 > 40%** — 主管覺得「這份沒做完吧？」
- **標題塞太多東西** — 一個標題塞 3 個方案名稱就違反「一頁一訊息」
- **數字沒對齊 / 沒單位** — 經費百分比要算到小數 1 位且加總 = 100%
- **CTA 模糊** — 沒寫「請核撥 OO 元」就只是報告，不是請示

來源：本場域（2026-10-05）art-20261005-022139-efc1-slides 自評。