#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
expense_report_generator.py - 差旅報支報表生成器
產生符合學校行政使用的差旅費用報告

支援輸出格式：
- 螢幕終端畫面輸出
- CSV 試算表匯出
- JSON 格式交換
- Markdown 文件格式
"""

from dataclasses import dataclass, field
from datetime import date, datetime
from typing import TextIO
import csv
import json
import io

from expense_calculator import (
    TravelExpense, DailyExpense, TravelType,
    ExpenseCalculator, ExpenseCalculator
)


@dataclass
class ReportConfig:
    """報表設定"""
    report_title: str = "差旅費用報告"
    show_details: bool = True
    currency: str = "NT$"
    language: str = "zh-TW"


class ExpenseReportGenerator:
    """
    差旅報表生成器
    
    功能：
    - 單筆差旅費用報表
    - 多筆差旅費用彙總表
    - CSV/JSON/Markdown 多格式輸出
    - 結合國旅卡補助試算
    """
    
    def __init__(self, config: ReportConfig = None):
        self.config = config or ReportConfig()
        self.records: list[TravelExpense] = []
    
    def add_expense(self, expense: TravelExpense):
        """新增一筆差旅記錄"""
        self.records.append(expense)
    
    def generate_single_report(self, expense: TravelExpense,
                               calc: ExpenseCalculator = None) -> str:
        """
        產生單筆差旅費用表
        
        每位員工每次出差填寫一份
        """
        calc = calc or ExpenseCalculator()
        result = calc.calculate_total(expense)
        
        lines = [
            "=" * 60,
            f"{self.config.report_title:^56}",
            "=" * 60,
            "【基本資料】",
            f"  出差人：{expense.employee_name} ({expense.employee_id})",
            f"  單　位：{expense.department}",
            f"  出差目的：{expense.purpose}",
            "-" * 60,
            "【出差資訊】",
            f"  出差日期：{expense.travel_date} 至 {expense.return_date}",
            f"  目的地：{expense.destination}",
            f"  總天數：{result['出差天數']} 天 / {result['住宿晚數']} 晚",
            "-" * 60,
            "【費用明細】",
            f"  膳雜費：{result['膳雜費（應發）']:>12,.0f} 元",
            f"  住宿費：{result['住宿費（應發）']:>12,.0f} 元",
            f"  交通費：{result['交通費（應發）']:>12,.0f} 元",
            f"  {'合計（應發）':>26}：{result['合計（應發）']:>12,.0f} 元",
            "-" * 60,
            "【交通費檢據明細】",
        ]
        
        # 交通費詳細
        lines.append(f"  去程：{expense.transport_outward:>12,.0f} 元")
        lines.append(f"  回程：{expense.transport_return:>12,.0f} 元")
        if expense.transport_other > 0:
            lines.append(f"  其他：{expense.transport_other:>12,.0f} 元")
        
        # 每日費用細項
        if self.config.show_details and expense.daily_expenses:
            lines.extend(["", "【膳雜費用途】"])
            for daily in expense.daily_expenses:
                meal_sub = daily.breakfast + daily.lunch + daily.dinner
                lines.append(
                    f"  {daily.day_date} | "
                    f"早{daily.breakfast:>5.0f} 午{daily.lunch:>5.0f} "
                    f"晚{daily.dinner:>5.0f} | 雜支{daily.miscellaneous:>5.0f} "
                    f"| 交通{daily.local_transport:>5.0f}"
                )
        
        lines.extend([
            "-" * 60,
            f"  備註：{expense.notes or '無'}",
            "=" * 60,
            f"  核簽章：________________________",
            f"  主辦人：________________________",
        ])
        
        return "\n".join(lines)
    
    def generate_summary_table(self, all_expenses: list[TravelExpense] = None) -> str:
        """
        產生多筆差旅費用彙總表
        （適用於單位月報或統計報表）
        """
        records = all_expenses or self.records
        calc = ExpenseCalculator()
        
        # 計算總計
        total_meal = 0.0
        total_hotel = 0.0
        total_transport = 0.0
        total_all = 0.0
        
        rows = []
        for exp in records:
            r = calc.calculate_total(exp)
            total_meal += r['膳雜費（應發）']
            total_hotel += r['住宿費（應發）']
            total_transport += r['交通費（應發）']
            total_all += r['合計（應發）']
            rows.append([
                exp.employee_name,
                str(exp.travel_date),
                str(exp.return_date),
                exp.destination,
                int(r['出差天數']),
                int(r['住宿晚數']),
                int(r['膳雜費（應發）']),
                int(r['住宿費（應發）']),
                int(r['交通費（應發）']),
                int(r['合計（應發）']),
            ])
        
        lines = [
            "=" * 100,
            f"{'差旅費用彙總表':^92}",
            "=" * 100,
            f"{'姓名':^10}{'出發日':^12}{'返程日':^12}{'目的地':^14}"
            f"{'天數':^6}{'晚數':^6}"
            f"{'膳雜費':^10}{'住宿費':^10}{'交通費':^10}{'合計':^10}",
            "-" * 100,
        ]
        
        for row in rows:
            lines.append(
                f"{row[0]:^10}{row[1]:^12}{row[2]:^12}{row[3]:^14}"
                f"{row[4]:^6}{row[5]:^6}"
                f"{row[6]:>10,}{row[7]:>10,}{row[8]:>10,}{row[9]:>10,}"
            )
        
        lines.extend([
            "-" * 100,
            f"{'總　計':^10}{'':<30}"
            f"{total_meal:>10,}{total_hotel:>10,}{total_transport:>10,}{total_all:>10,}",
            "=" * 100,
        ])
        
        return "\n".join(lines)
    
    def export_to_csv(self, filepath: str, all_expenses: list[TravelExpense] = None):
        """
        匯出為 CSV 格式
        
        可匯入 Google Sheets 或 Excel
        """
        records = all_expenses or self.records
        calc = ExpenseCalculator()
        
        with open(filepath, 'w', newline='', encoding='utf-8-sig') as f:
            writer = csv.writer(f)
            
            # 標題列
            writer.writerow([
                "姓名", "員工編號", "單位", "出差日期起", "出差日期訖",
                "目的地", "出差目的", "天數", "晚數",
                "膳雜費", "住宿費", "交通費", "合計", "備註"
            ])
            
            # 資料列
            for exp in records:
                r = calc.calculate_total(exp)
                writer.writerow([
                    exp.employee_name,
                    exp.employee_id,
                    exp.department,
                    str(exp.travel_date),
                    str(exp.return_date),
                    exp.destination,
                    exp.purpose,
                    r['出差天數'],
                    r['住宿晚數'],
                    int(r['膳雜費（應發）']),
                    int(r['住宿費（應發）']),
                    int(r['交通費（應發）']),
                    int(r['合計（應發）']),
                    exp.notes or '',
                ])
    
    def export_to_json(self, filepath: str = None,
                       all_expenses: list[TravelExpense] = None) -> str:
        """匯出為 JSON 格式"""
        records = all_expenses or self.records
        calc = ExpenseCalculator()
        
        data = {
            "report_title": self.config.report_title,
            "generated_at": datetime.now().isoformat(),
            "total_records": len(records),
            "records": []
        }
        
        for exp in records:
            r = calc.calculate_total(exp)
            data["records"].append({
                "員工姓名": exp.employee_name,
                "員工編號": exp.employee_id,
                "單位": exp.department,
                "出差日期": {"起": str(exp.travel_date), "訖": str(exp.return_date)},
                "目的地": exp.destination,
                "目的": exp.purpose,
                "出差天數": r['出差天數'],
                "住宿晚數": r['住宿晚數'],
                "膳雜費": r['膳雜費（應發）'],
                "住宿費": r['住宿費（應發）'],
                "交通費": r['交通費（應發）'],
                "合計": r['合計（應發）'],
                "備註": exp.notes or '',
            })
        
        json_str = json.dumps(data, ensure_ascii=False, indent=2)
        
        if filepath:
            with open(filepath, 'w', encoding='utf-8') as f:
                f.write(json_str)
        
        return json_str
    
    def export_to_markdown(self, filepath: str = None,
                           all_expenses: list[TravelExpense] = None) -> str:
        """匯出為 Markdown 格式（可用於 Word 轉換）"""
        records = all_expenses or self.records
        calc = ExpenseCalculator()
        
        lines = [
            f"# {self.config.report_title}",
            f"",
            f"**產生時間**：{datetime.now().strftime('%Y/%m/%d %H:%M')}",
            f"",
            "## 差旅費用一覽表",
            f"",
            "| 姓名 | 單位 | 出差日 | 返程日 | 目的地 | "
            "膳雜費 | 住宿費 | 交通費 | 合計 |",
            "|------|------|--------|--------|--------|"
            "------:|------:|------:|------:|",
        ]
        
        total_meal = total_hotel = total_transport = total_all = 0
        
        for exp in records:
            r = calc.calculate_total(exp)
            total_meal += r['膳雜費（應發）']
            total_hotel += r['住宿費（應發）']
            total_transport += r['交通費（應發）']
            total_all += r['合計（應發）']
            
            lines.append(
                f"| {exp.employee_name} | {exp.department} | "
                f"{exp.travel_date} | {exp.return_date} | {exp.destination} | "
                f"{r['膳雜費（應發）']:,.0f} | {r['住宿費（應發）']:,.0f} | "
                f"{r['交通費（應發）']:,.0f} | {r['合計（應發）']:,.0f} |"
            )
        
        lines.extend([
            f"| **總計** | | | | | "
            f"**{total_meal:,.0f}** | **{total_hotel:,.0f}** | "
            f"**{total_transport:,.0f}** | **{total_all:,.0f}** |",
        ])
        
        md = "\n".join(lines)
        
        if filepath:
            with open(filepath, 'w', encoding='utf-8') as f:
                f.write(md)
        
        return md


def demo():
    """示範産出多筆差旅報表"""
    from expense_calculator import TravelType
    
    gen = ExpenseReportGenerator()
    
    # 模拟三筆差旅
    expenses = [
        TravelExpense(
            employee_name="王小明", employee_id="A123456789",
            department="人事室",
            travel_date=date(2026, 5, 10), return_date=date(2026, 5, 11),
            destination="臺北市", purpose="參加教育局會議",
            travel_type=TravelType.OVERNIGHT,
            transport_outward=350, transport_return=350,
            hotel_fee=1800, hotel_nights=1,
        ),
        TravelExpense(
            employee_name="李小美", employee_id="B987654321",
            department="教務處",
            travel_date=date(2026, 5, 15), return_date=date(2026, 5, 16),
            destination="高雄市", purpose="全國教育局長會議",
            travel_type=TravelType.OVERNIGHT,
            transport_outward=1350, transport_return=1350,
            hotel_fee=2200, hotel_nights=1,
        ),
        TravelExpense(
            employee_name="陳大雄", employee_id="C555555555",
            department="總務處",
            travel_date=date(2026, 5, 20), return_date=date(2026, 5, 20),
            destination="臺中市", purpose="領取教材",
            travel_type=TravelType.DAY_TRIP,  # 當日往返
            transport_outward=300, transport_return=300,
        ),
    ]
    
    for exp in expenses:
        gen.add_expense(exp)
    
    print("=== 彙總表 ===")
    print(gen.generate_summary_table())
    
    print("\n=== CSV 匯出 ===")
    gen.export_to_csv("/tmp/expense_report_demo.csv")
    print("已匯出至 /tmp/expense_report_demo.csv")
    
    print("\n=== JSON 格式 ===")
    json_str = gen.export_to_json()
    print(json_str[:500], "...")
    
    print("\n=== Markdown 格式 ===")
    md_str = gen.export_to_markdown()
    print(md_str)


if __name__ == "__main__":
    demo()
