#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
travel_subsidy.py - 國民旅遊卡補助試算工具
適用於公務人員休假旅遊補助費用計算

根據公務人員強制休假補助使用注意事項設計
"""

from dataclasses import dataclass, field
from datetime import date, datetime
from typing import Literal, Optional
from enum import Enum
import json


class SubsidyLevel(Enum):
    """補助等級"""
    LEVEL_1 = (1, "住院或重大傷病")  # 最高，100%補助，但需特別條件
    LEVEL_2 = (2, "觀光旅遊")        # 觀光局審核通過之旅遊活動
    LEVEL_3 = (3, "核定自行參加旅遊")  # 自行預約政府指定國旅卡店家


@dataclass
class CardTransaction:
    """國旅卡交易記錄"""
    date: date
    amount: float
    merchant_name: str
    merchant_category: str  # 観光、交通、餐飲等
    is_subsidy_eligible: bool = True   # 是否符合補助資格
    notes: str = ""

@dataclass  
class SubsidyRecord:
    """補助記錄"""
    employee_name: str
    employee_id: str
    year: int
    base_allowance: float           # 基本補助額（強制休假補助費）
    additional_allowance: float     # 額外補助（偏遠地區）
    transactions: list[CardTransaction] = field(default_factory=list)


class TravelSubsidyCalculator:
    """
    國民旅遊卡補助試算機
    
    規則摘要（根據公務人員強制休假補助費支給要點）：
    
    ■ 基本補助：
      - 每人每年 16,000 元為上限（原為 14,000，2022年調整）
      按「實際消費」核實補助，未消費不發給
    
    ■ 消費門檻：
      - 每年須消費滿 16 小時（或結合休假達一定日數）
      - 消費地點須為國旅卡特約商店
    
    ■ 補助範疇（觀光類）：
      - 旅遊住宿（觀光飯店、遊憩區民宿）
      - 交通（國籍航空公司、臺鐵、高鐵、客運）
      - 觀光遊樂（主題樂園、國家公園門票）
      - 餐飲（須為國旅卡特約商店）
    
    ■ 不符合補助：
      - 超商、加油站、百貨公司（一般消費）
      - 網路購物（未在規定平臺）
      - 溢報或重複申請
    
    ■ 偏遠地區加成：
      - 前往交通不便地區休假，得按1/3額外加成
      - 花蓮、臺東、澎湖、金門、馬祖等地
    """
    
    BASE_ALLOWANCE = 16000.0           # 基本補助上限/年
    ADDITIONAL_BONUS_RATE = 1/3        # 偏遠地區加成率
    REMOTE_AREAS = {
        "花蓮縣", "臺東縣", "澎湖縣", "金門縣", "連江縣",
        "屏東縣恆春", "嘉義縣阿里山", "南投縣信義/水里"
    }
    
    # 行業別代碼（MCC Code）對照補助資格
    MCC_SUBSIDY_ELIGIBLE = [
        "7011",  # 飯店/汽車旅館/度假村
        "7512",  # 汽車租賃
        "4011",  # 鐵路客運
        "4121",  # 都市和大眾交通
        "4511",  # 航空公司
        "7991",  # 旅遊景點/博物館/美術館
        "7994",  # 遊樂園/主題樂園
        "5812",  # 餐廳/酒吧（需國旅卡特約）
    ]
    
    def __init__(self, year: int = None):
        self.year = year or datetime.now().year
        self.transactions: list[CardTransaction] = []
    
    def add_transaction(self, date: date, amount: float, 
                       merchant_name: str = "", merchant_category: str = "",
                       is_eligible: bool = True):
        """新增一筆國旅卡消費"""
        self.transactions.append(CardTransaction(
            date=date, amount=amount,
            merchant_name=merchant_name,
            merchant_category=merchant_category,
            is_subsidy_eligible=is_eligible
        ))
    
    def filter_subsidy_eligible(self) -> list[CardTransaction]:
        """過濾符合補助資格的消費"""
        return [t for t in self.transactions if t.is_subsidy_eligible]
    
    def calculate_total_subsidy(self, base_allowance: float = None,
                               is_remote_trip: bool = False) -> dict:
        """
        計算補助金額
        
        Args:
            base_allowance: 基本補助額（預設16,000）
            is_remote_trip: 是否前往偏遠地區（可額外加成1/3）
        
        Returns:
            補助試算結果字典
        """
        base = base_allowance or self.BASE_ALLOWANCE
        eligible_amount = sum(t.amount for t in self.filter_subsidy_eligible())
        
        # 基本補助（實支結果）
        base_subsidy = min(base, eligible_amount)
        
        # 偏遠加成（基本補助的1/3）
        bonus = 0.0
        if is_remote_trip:
            bonus = base_subsidy * self.ADDITIONAL_BONUS_RATE
            # 實際加成不得超過該趟消費
            bonus = min(bonus, eligible_amount - base_subsidy)
        
        total = base_subsidy + bonus
        
        return {
            "年份": self.year,
            "消費總金額": round(eligible_amount, 0),
            "基本補助": round(base_subsidy, 0),
            "偏遠加成": round(bonus, 0),
            "補助合計": round(total, 0),
            "補助上限": base + (base * self.ADDITIONAL_BONUS_RATE if is_remote_trip else 0),
            "符合補助筆數": len(self.filter_subsidy_eligible()),
            "總消費筆數": len(self.transactions),
        }
    
    def generate_detail_report(self) -> str:
        """產出詳細補助報告"""
        result = self.calculate_total_subsidy()
        
        lines = [
            "=" * 56,
            f"{'國民旅遊卡補助試算表':^52}",
            "=" * 56,
            f"補助年份：{result['年份']}",
            f"總消費筆數：{result['總消費筆數']} 筆",
            f"符合補助筆數：{result['符合補助筆數']} 筆",
            "-" * 56,
            f"消費總金額（新台幣）：{result['消費總金額']:>12,.0f} 元",
            f"基本補助額上限：{result['補助上限']:>12,.0f} 元",
            f"{'基本補助金額':>26}：{result['基本補助']:>12,.0f} 元",
            f"{'偏遠地區加成':>26}：{result['偏遠加成']:>12,.0f} 元",
            "-" * 56,
            f"{'補助合計':>26}：{result['補助合計']:>12,.0f} 元",
            "=" * 56,
        ]
        
        # 消費明細
        if self.transactions:
            lines.append("\n--- 消費明細 ---")
            for i, t in enumerate(self.transactions, 1):
                status = "○" if t.is_subsidy_eligible else "✗"
                lines.append(
                    f"{i}. [{status}] {t.date} "
                    f"NT${t.amount:,.0f} | {t.merchant_name or '未分類'} "
                    f"({t.merchant_category})"
                )
        
        return "\n".join(lines)
    
    def export_to_json(self, filename: str = None) -> str:
        """匯出為 JSON 格式"""
        result = self.calculate_total_subsidy()
        data = {
            "補助年度": result["年份"],
            "消費記錄": [
                {"日期": str(t.date), "金額": t.amount,
                 "商店": t.merchant_name, "類別": t.merchant_category}
                for t in self.transactions
            ],
            "試算結果": result
        }
        json_str = json.dumps(data, ensure_ascii=False, indent=2)
        
        if filename:
            with open(filename, 'w', encoding='utf-8') as f:
                f.write(json_str)
        
        return json_str


def demo():
    """示範：三日兩夜花蓮之旅"""
    calc = TravelSubsidyCalculator(year=2026)
    
    # 模擬消費資料
    transactions = [
        ("2026-07-15", 3200, "花蓮遠雄悅來大飯店", "飯店", True),
        ("2026-07-15", 180, "花蓮七星潭", "門票", True),
        ("2026-07-16", 450, "液香扁食店", "餐飲", True),
        ("2026-07-16", 800, "花蓮租車", "交通", True),
        ("2026-07-16", 200, "全家便利商店", "超商", False),  # 不符合
        ("2026-07-17", 650, "蜂巢膠囊庇護工場", "伴手禮", True),
    ]
    
    for date_str, amount, merchant, category, eligible in transactions:
        parts = date_str.split("-")
        y, m, d = int(parts[0]), int(parts[1]), int(parts[2])
        calc.add_transaction(
            date=date(y, m, d),
            amount=amount,
            merchant_name=merchant,
            merchant_category=category,
            is_eligible=eligible
        )
    
    print(calc.generate_detail_report())
    
    print("\n--- JSON 格式 ---")
    print(calc.export_to_json())


if __name__ == "__main__":
    demo()
