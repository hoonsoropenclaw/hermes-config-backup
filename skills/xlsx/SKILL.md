# SKILL.md - xlsx 專業電子表格處理

## 身份
- **name**: xlsx
- **description**: 當電子表格文件是主要輸入或輸出時使用此技能。這意味著用戶想要：打開、讀取、編輯或修復現有的.xlsx、.xlsm、.csv或.tsv文件；從頭開始創建新的電子表格；或在表格文件格式之間轉換。

## 核心共識

### 字體與顏色規範（除非另有說明）
- 藍色文本 (RGB: 0,0,255): 硬編碼輸入和用戶將更改場景的數字
- 黑色文本 (RGB: 0,0,0): 所有公式和計算
- 綠色文本 (RGB: 0,128,0): 從同一工作簿內其他工作表提取的鏈接
- 紅色文本 (RGB: 255,0,0): 到其他文件的外部鏈接
- 黃色背景 (RGB: 255,255,0): 需要注意的關鍵假設

### 數字格式規範
- 年份：格式化為文本字符串（例如：「2024」）
- 貨幣：使用 `$#,##0` 格式
- 零：使用數字格式使所有零顯示為「-」
- 百分比：默認為 0.0% 格式
- 倍數：格式化為 0.0x（EV/EBITDA、P/E）
- 負數：使用括號 (123) 而不是減號 -123

### 公式原則
- ✅ **始終使用 Excel 公式，而不是在 Python 中計算值並硬編碼**
- ✅ 在公式中使用細胞引用而不是硬編碼值
- ✅ 示例：`=SUM(B2:B9)` 而非硬編碼總和
- ✅ 示例：`=(C4-C2)/C2` 而非硬編碼增長率

## 工具

### pandas（數據分析）
```python
import pandas as pd

# 讀取
df = pd.read_excel('file.xlsx')
all_sheets = pd.read_excel('file.xlsx', sheet_name=None)

# 分析
df.head()
df.info()
df.describe()

# 寫入
df.to_excel('output.xlsx', index=False)
```

### openpyxl（公式和格式化）
```python
from openpyxl import Workbook, load_workbook
from openpyxl.styles import Font, PatternFill, Alignment

# 創建
wb = Workbook()
sheet = wb.active
sheet['A1'] = 'Hello'
sheet['B2'] = '=SUM(A1:A10)'
sheet['A1'].font = Font(bold=True, color='FF0000')

# 加載現有
wb = load_workbook('existing.xlsx')
for sheet_name in wb.sheetnames:
    sheet = wb[sheet_name]

wb.save('modified.xlsx')
```

## 公式重新計算
- 由 openpyxl 創建的文件包含字符串公式但沒有計算值
- 使用 `scripts/recalc.py` 重新計算：
  ```bash
  python scripts/recalc.py output.xlsx 30
  ```
- 返回 JSON 包含錯誤位置和計數

## 驗證清單
- [ ] 零公式錯誤（#REF!、#DIV/0!、#VALUE!、#N/A、#NAME?）
- [ ] 測試 2-3 個示例引用驗證公式正確
- [ ] 檢查範圍中的差一錯誤
- [ ] 確保所有預測期間的公式一致
- [ ] 使用邊緣情況測試（零值、負數）
- [ ] 驗證沒有循環引用
- [ ] 細胞引用正確（Excel列：A=1, B=2, ..., Z=26, AA=27...）

## 工具總結
| 任務 | 最佳工具 |
|------|----------|
| 數據分析 | pandas |
| 公式/格式化 | openpyxl |
| 重新計算公式 | scripts/recalc.py |
| 驗證錯誤 | scripts/recalc.py |

## 安裝
```bash
pip install pandas openpyxl
```