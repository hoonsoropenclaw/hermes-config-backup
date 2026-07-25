#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
expense_calculator.py - 差旅費用計算模組
適用於台灣公務人員國內出差費用處理

根據「國內出差旅費報支要點」設計
"""

from dataclasses import dataclass, field
from datetime import date, datetime, timedelta
from typing import Literal, Optional
from enum import Enum


class TravelType(Enum):
    """出差類型"""
    DAY_TRIP = "當日往返"          # 不過夜
    OVERNIGHT = "過夜出差"        # 過夜
    HOSTEL_ONLY = "簡宿"          # 借用學校或公家宿舍


@dataclass
class DailyExpense:
    """每日費用記錄"""
    day_date: date
    breakfast: float = 0.0
    lunch: float = 0.0
    dinner: float = 0.0
    miscellaneous: float = 0.0   # 雜支
    local_transport: float = 0.0  # 當地交通
    
    @property
    def total(self) -> float:
        return self.breakfast + self.lunch + self.dinner + self.miscellaneous + self.local_transport


@dataclass
class TravelExpense:
    """完整差旅費用"""
    employee_name: str
    employee_id: str
    department: str
    travel_date: date
    return_date: date
    destination: str
    purpose: str
    travel_type: TravelType = TravelType.OVERNIGHT
    
    # 交通費（飛機/火車/客運/高鐵）
    transport_outward: float = 0.0
    transport_return: float = 0.0
    transport_other: float = 0.0  # 其他交通費（租車、保險等）
    
    # 住宿費
    hotel_fee: float = 0.0
    hotel_nights: int = 0
    
    # 日用雜費（膳雜費）
    daily_expenses: list[DailyExpense] = field(default_factory=list)
    
    notes: str = ""


class ExpenseCalculator:
    """
    台灣公務人員差旅費用計算機
    
    根據「國內出差旅費報支要點」：
    - 膳雜費：每人每日 650 元（含午/晚/雜支）
    - 住宿費上限：每人每日 2,000 元（一般地區）/ 2,500 元（偏遠地區）
    - 交通費：檢據核銷（高鐵/火車/客運/飛機）
    - 過夜出差可有1日膳雜費（650元），當日往返則無
    """
    
    # 2024年最新的報支標準
    MEAL_ALLOWANCE_PER_DAY = 650.0        # 膳雜費上限/日（小於12小時不發給）
    HOTEL_CAP_GENERAL = 2000.0            # 一般地區住宿上限/日
    HOTEL_CAP_REMOTE = 2500.0             # 偏遠地區住宿上限/日
    HALF_DAY_THRESHOLD_HOURS = 12          # 超過12小時才發膳雜費
    
    def __init__(self, remote_area: bool = False):
        self.remote_area = remote_area
        self.hotel_cap = self.HOTEL_CAP_REMOTE if remote_area else self.HOTEL_CAP_GENERAL
    
    @staticmethod
    def calculate_nights(start_date: date, end_date: date) -> int:
        """計算住宿晚數"""
        delta = end_date - start_date
        if delta.days == 0:
            return 0
        return max(1, delta.days)
    
    @staticmethod
    def calculate_trip_days(start_date: date, end_date: date) -> int:
        """計算總出差天數"""
        delta = end_date - start_date
        return delta.days + 1  # 含首日
    
    def calculate_meal_allowance(self, travel: TravelExpense) -> float:
        """
        計算膳雜費
        
        規則（根據國內出差旅費報支要點）：
        - 當日往返：不分給膳雜費
        - 過夜出差：每日 650 元（含午餐、晚餐、雜支）
        - 出差時間未達12小時：不發給膳雜費
        """
        if travel.travel_type == TravelType.DAY_TRIP:
            return 0.0
        
        nights = self.calculate_nights(travel.travel_date, travel.return_date)
        # 住宿N晚有N+1天，但過夜第一天有膳雜費
        total_days = self.calculate_trip_days(travel.travel_date, travel.return_date)
        trip_hours = total_days * 24
        
        if trip_hours < self.HALF_DAY_THRESHOLD_HOURS:
            return 0.0
        
        # 每天 650 元，乘以出差天數
        return self.MEAL_ALLOWANCE_PER_DAY * total_days
    
    def calculate_hotel_allowance(self, travel: TravelExpense) -> float:
        """
        計算住宿費補助
        
        規則：
        - 按日核給，最高不超過上限
        - 實際費用低於上限者，核實報支
        - 住宿日數nour住宿晚數，2天來回會有1晚
        """
        if not travel.hotel_nights or travel.hotel_nights <= 0:
            return 0.0
        
        actual = min(travel.hotel_fee, self.hotel_cap * travel.hotel_nights)
        return actual
    
    def calculate_transport_allowance(self, travel: TravelExpense) -> float:
        """
        計算交通費補助
        交通費應檢據核銷，機票/高鐵/火車/客運實支
        """
        return (travel.transport_outward + 
                travel.transport_return + 
                travel.transport_other)
    
    def calculate_total(self, travel: TravelExpense) -> dict:
        """
        計算差旅總費用
        
        返回一個包含費用明細的字典
        """
        meal = self.calculate_meal_allowance(travel)
        hotel = self.calculate_hotel_allowance(travel)
        transport = self.calculate_transport_allowance(travel)
        
        # 統計實際花費
        actual_daily_total = sum(d.total for d in travel.daily_expenses)
        
        total = meal + hotel + transport
        funded = min(total, meal + hotel + transport)  # 交通費實支
        
        return {
            "出差人": travel.employee_name,
            "出差日期": f"{travel.travel_date} ~ {travel.return_date}",
            "出差天數": self.calculate_trip_days(travel.travel_date, travel.return_date),
            "住宿晚數": travel.hotel_nights,
            "目的地": travel.destination,
            "膳雜費（應發）": round(meal, 0),
            "住宿費（應發）": round(hotel, 0),
            "交通費（應發）": round(transport, 0),
            "合計（應發）": round(total, 0),
            "交通費檢據金額": round(actual_daily_total, 0),
            "實際總發金額": round(funded, 0),
            "膳雜費單日": self.MEAL_ALLOWANCE_PER_DAY,
            "住宿費單日上限": self.hotel_cap,
        }
    
    def breakdown_report(self, travel: TravelExpense) -> str:
        """產出費用明細表"""
        result = self.calculate_total(travel)
        lines = [
            "=" * 50,
            f"{'差旅費用明細表':^46}",
            "=" * 50,
            f"出差人：{result['出差人']}",
            f"出差日期：{result['出差日期']}",
            f"出差天數：{result['出差天數']} 天",
            f"住宿晚數：{result['住宿晚數']} 晚",
            f"目的地：{result['目的地']}",
            "-" * 50,
            f"【膳雜費】{result['膳雜費（應發）']:>10,.0f} 元",
            f"  └─ 單日標準：{result['膳雜費單日']} 元 x {result['出差天數']} 天",
            f"【住宿費】{result['住宿費（應發）']:>10,.0f} 元",
            f"  └─ 單日上限：{result['住宿費單日上限']} 元 x {result['住宿晚數']} 晚",
            f"【交通費】{result['交通費（應發）']:>10,.0f} 元",
            "-" * 50,
            f"{'合計（應發）':>26}：{result['合計（應發）']:>10,.0f} 元",
            "=" * 50,
        ]
        return "\n".join(lines)


def demo():
    """
    示範：南部學校出差二日遊
    """
    travel = TravelExpense(
        employee_name="王小明",
        employee_id="A123456789",
        department="人事室",
        travel_date=date(2026, 5, 15),
        return_date=date(2026, 5, 16),
        destination="高雄市",
        purpose="參加教育局研習會議",
        travel_type=TravelType.OVERNIGHT,
        transport_outward=1350.0,   # 火車票
        transport_return=1350.0,   # 火車票
        hotel_fee=1500.0,            # 實際住宿費
        hotel_nights=1,
        daily_expenses=[
            DailyExpense(day_date=date(2026, 5, 15), breakfast=0, lunch=150, dinner=200, miscellaneous=0, local_transport=200),
            DailyExpense(day_date=date(2026, 5, 16), breakfast=0, lunch=150, dinner=0, miscellaneous=0, local_transport=100),
        ],
    )
    
    calc = ExpenseCalculator(remote_area=False)
    print(calc.breakdown_report(travel))
    
    print("\n--- JSON 格式輸出 ---")
    import json
    result = calc.calculate_total(travel)
    print(json.dumps(result, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    demo()
