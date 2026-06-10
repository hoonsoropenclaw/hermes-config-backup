# SKILL.md - attendance-sheet 考勤表生成

## 身份
- **name**: attendance-sheet
- **description**: 根據員工工作資料生成格式化的 Excel 考勤表。接受員工姓名、日期範圍和出勤狀態代碼，輸出帶有顏色標記和摘要統計的 .xlsx 文件。

## 輸入需求

### 必要資訊
- **員工名單**: 名稱列表（陣列）
- **日期範圍**: 開始日期 ~ 結束日期
- **出勤狀態代碼**: 預定義狀態映射

### 可選資訊
- 遲到/早退容忍分鐘數
- 特殊假期設定
- 部門/團隊分組

## 狀態代碼定義

| 代碼 | 狀態 | 顏色 | 說明 |
|------|------|------|------|
| ✓ / P | 正常出勤 | 綠色 | |
| ✗ / A | 缺席 | 紅色 | |
| L | 遲到 | 橙色 | |
| E | 早退 | 橙色 | |
| S / SL | 半假 | 黃色 | |
| H | 假期 | 藍色 | 國定假日 |
| O / OFF | 排休 | 灰色 | |
| ? | 未設定 | 白色 | |

## 輸出格式

### 欄位結構
```
| 姓名 | 部門 | 01 | 02 | 03 | ... | 30 | 31 | 總計 |
|------|------|----|----|----|-----|----|----|------|
|      |      |    |    |    |     |    |    |      |
```

### 顏色規範
- 出勤：無填充
- 缺席：紅色背景 (RGB: 255, 200, 200)
- 遲到：橙色背景 (RGB: 255, 230, 200)
- 半假：黃色背景 (RGB: 255, 255, 200)
- 假期：藍色背景 (RGB: 200, 220, 255)
- 排休：灰色背景 (RGB: 230, 230, 230)

### 摘要統計
- 總出勤天數
- 缺席天數
- 遲到次數
- 早退次數
- 其他假期天數

## Python 實現

### 使用 openpyxl 創建考勤表
```python
from openpyxl import Workbook
from openpyxl.styles import Font, PatternFill, Alignment, Border, Side
from openpyxl.utils import get_column_letter
from datetime import datetime, timedelta

def create_attendance_sheet(employees, start_date, end_date, absences_dict):
    """
    employees: list of employee names
    start_date: datetime object
    end_date: datetime object
    absences_dict: {employee_name: [list of dates]} (optional absences)
    """
    wb = Workbook()
    ws = wb.active
    ws.title = "考勤表"
    
    # 定義填充色
    fill_colors = {
        'P': None,  # 正常，無填充
        'A': PatternFill(start_color='FFC8C8', end_color='FFC8C8', fill_type='solid'),  # 缺席
        'L': PatternFill(start_color='FFE6C8', end_color='FFE6C8', fill_type='solid'),  # 遲到
        'E': PatternFill(start_color='FFE6C8', end_color='FFE6C8', fill_type='solid'),  # 早退
        'S': PatternFill(start_color='FFFFC8', end_color='FFFFC8', fill_type='solid'),  # 半假
        'H': PatternFill(start_color='C8DCFF', end_color='C8DCFF', fill_type='solid'),  # 假期
        'OFF': PatternFill(start_color='E6E6E6', end_color='E6E6E6', fill_type='solid'),  # 排休
    }
    
    # 標題行
    headers = ['姓名', '部門']
    current_date = start_date
    while current_date <= end_date:
        headers.append(current_date.strftime('%d'))
        current_date += timedelta(days=1)
    headers.append('出勤天數')
    headers.append('缺席天數')
    headers.append('遲到次數')
    
    # 寫入標題
    for col, header in enumerate(headers, 1):
        cell = ws.cell(row=1, column=col)
        cell.value = header
        cell.font = Font(bold=True)
        cell.alignment = Alignment(horizontal='center')
    
    # 填充數據
    row = 2
    for emp in employees:
        ws.cell(row=row, column=1, value=emp)
        ws.cell(row=row, column=2, value='-')
        
        col = 3
        total_present = 0
        total_absent = 0
        total_late = 0
        
        current_date = start_date
        while current_date <= end_date:
            status = absences_dict.get(emp, {}).get(current_date, 'P')
            cell = ws.cell(row=row, column=col)
            cell.value = status
            cell.alignment = Alignment(horizontal='center')
            
            if status == 'P':
                total_present += 1
            elif status == 'A':
                total_absent += 1
                cell.fill = fill_colors['A']
            elif status in ['L', 'E']:
                total_late += 1
                cell.fill = fill_colors['L']
            elif status == 'S':
                cell.fill = fill_colors['S']
            elif status == 'H':
                cell.fill = fill_colors['H']
            elif status == 'OFF':
                cell.fill = fill_colors['OFF']
            
            col += 1
            current_date += timedelta(days=1)
        
        # 統計欄
        ws.cell(row=row, column=col, value=total_present)
        ws.cell(row=row, column=col+1, value=total_absent)
        ws.cell(row=row, column=col+2, value=total_late)
        
        row += 1
    
    # 調整欄寬
    ws.column_dimensions['A'].width = 12
    ws.column_dimensions['B'].width = 8
    
    wb.save('attendance.xlsx')
```

## 使用時機

### 適用場景
- 建立月度 HR 考勤報告（50 名員工）
- 將原始每日簽到日誌轉換為格式化電子表格
- 追蹤整個團隊在支付期間的遲到和缺席
- 準備績效考核的考勤文檔
- 為小團隊生成單日出勤記錄

### 常見輸入格式
```python
employees = ["張三", "李四", "王五"]
start_date = datetime(2026, 5, 1)
end_date = datetime(2026, 5, 31)

# 缺席記錄
absences = {
    "張三": {
        datetime(2026, 5, 3): "A",
        datetime(2026, 5, 15): "L",
    },
    "李四": {
        datetime(2026, 5, 10): "H",
    }
}

create_attendance_sheet(employees, start_date, end_date, absences)
```

## 整合 xlsx 技能

此技能基於 `xlsx` 技能的基礎，專注於：
1. 考勤特定的顏色編碼
2. 狀態代碼系統
3. 摘要統計計算

可與 `xlsx` 技能配合使用，處理更複雜的公式和格式化需求。