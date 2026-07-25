#!/usr/bin/env python3
"""
Event Conflict Detector - 事件衝突檢測工具
用於檢測行事曆事件之間的時間衝突

衝突檢測原理：
Two events conflict if: A.start < B.end AND A.end > B.start
"""

import datetime
from typing import List, Dict, Optional, Tuple


class EventConflictDetector:
    """
    事件衝突檢測器
    
    使用方式：
    ```python
    from event_conflict_detector import EventConflictDetector
    
    detector = EventConflictDetector()
    
    # 添加已存在的事件
    detector.add_events(existing_events)
    
    # 檢查新事件是否衝突
    conflicts = detector.check_conflict(
        start_time=datetime.datetime(2024, 1, 15, 10, 0),
        end_time=datetime.datetime(2024, 1, 15, 11, 0)
    )
    
    if conflicts:
        print("⚠️ 發現衝突！")
        for c in conflicts:
            print(f"  衝突事件: {c['event']['summary']}")
            print(f"  重疊時間: {c['overlap_minutes']} 分鐘")
    ```
    """
    
    def __init__(self):
        self.events: List[Dict] = []
        self._time_cache: Dict[str, datetime.datetime] = {}
    
    def add_event(self, event: Dict):
        """添加單個事件到檢測队列"""
        self.events.append(event)
    
    def add_events(self, events: List[Dict]):
        """批量添加事件"""
        self.events.extend(events)
    
    def clear(self):
        """清除所有已添加的事件"""
        self.events.clear()
        self._time_cache.clear()
    
    def check_conflict(
        self,
        start_time: datetime.datetime,
        end_time: datetime.datetime,
        exclude_event_id: Optional[str] = None
    ) -> List[Dict]:
        """
        檢查新事件是否與現有事件衝突
        
        Args:
            start_time: 新事件開始時間
            end_time: 新事件結束時間
            exclude_event_id: 要排除的事件 ID（如更新時排除自身）
            
        Returns:
            List[Dict]: 衝突事件列表
            [{
                'event': event_dict,
                'overlap_minutes': int,
                'overlap_start': datetime,
                'overlap_end': datetime
            }, ...]
        """
        conflicts = []
        
        for event in self.events:
            # 排除自身（更新時）
            if exclude_event_id and event.get('id') == exclude_event_id:
                continue
            
            # 解析事件時間
            event_start = self._parse_time(event.get('start'))
            event_end = self._parse_time(event.get('end'))
            
            if event_start is None or event_end is None:
                continue
            
            # 衝突檢測：兩條線段重疊的數學條件
            if start_time < event_end and end_time > event_start:
                # 計算重疊時間
                overlap_start = max(start_time, event_start)
                overlap_end = min(end_time, event_end)
                overlap_minutes = (overlap_end - overlap_start).total_seconds() / 60
                
                conflicts.append({
                    'event': event,
                    'overlap_minutes': round(overlap_minutes, 1),
                    'overlap_start': overlap_start,
                    'overlap_end': overlap_end
                })
        
        return conflicts
    
    def find_free_slots(
        self,
        date: datetime.date,
        start_hour: int = 8,
        end_hour: int = 18,
        min_duration_minutes: int = 30
    ) -> List[Dict]:
        """
        查找指定日期的空閒時段
        
        Args:
            date: 要查找的日期
            start_hour: 工作日開始時間（小時）
            end_hour: 工作日結束時間（小時）
            min_duration_minutes: 最小持續時間（分鐘）
            
        Returns:
            List[Dict]: 空閒時段列表
            [{'start': datetime, 'end': datetime, 'duration_minutes': int}, ...]
        """
        # 解析所有事件的時間段
        busy_periods: List[Tuple[datetime.datetime, datetime.datetime]] = []
        
        for event in self.events:
            event_start = self._parse_time(event.get('start'))
            event_end = self._parse_time(event.get('end'))
            
            if event_start and event_end:
                # 確保是當天的時間
                event_start = self._ensure_date(event_start, date)
                event_end = self._ensure_date(event_end, date)
                busy_periods.append((event_start, event_end))
        
        # 按開始時間排序
        busy_periods.sort(key=lambda x: x[0])
        
        # 合併重疊的忙碌時段
        merged = self._merge_periods(busy_periods)
        
        # 計算空閒時段
        free_slots = []
        current_time = datetime.datetime.combine(date, datetime.time(start_hour))
        end_time = datetime.datetime.combine(date, datetime.time(end_hour))
        
        for busy_start, busy_end in merged:
            # 確保在工作时间范围内
            if busy_start > current_time:
                free_start = current_time
                free_end = min(busy_start, end_time)
                duration = (free_end - free_start).total_seconds() / 60
                
                if duration >= min_duration_minutes:
                    free_slots.append({
                        'start': free_start,
                        'end': free_end,
                        'duration_minutes': int(duration)
                    })
            
            current_time = max(current_time, busy_end)
        
        # 檢查最後一個時段到工作結束
        if current_time < end_time:
            duration = (end_time - current_time).total_seconds() / 60
            if duration >= min_duration_minutes:
                free_slots.append({
                    'start': current_time,
                    'end': end_time,
                    'duration_minutes': int(duration)
                })
        
        return free_slots
    
    def check_day_conflicts(
        self,
        date: datetime.date,
        service=None,
        calendar_id: str = 'primary'
    ) -> List[Dict]:
        """
        檢查特定日期的所有衝突
        
        Args:
            date: 要檢查的日期
            service: Google Calendar API service
            calendar_id: 行事曆 ID
            
        Returns:
            List[Dict]: 衝突事件對列表
        """
        if service is None:
            # 如果沒有 service，返回內存中事件的衝突
            return self._check_events_conflicts(date)
        
        # 從 Google Calendar 獲取事件
        from google_calendar_sync import GoogleCalendarSync
        
        sync = GoogleCalendarSync(service)
        start_of_day = datetime.datetime.combine(date, datetime.time.min)
        end_of_day = datetime.datetime.combine(date, datetime.time.max)
        
        day_events = sync.list_events(
            calendar_id=calendar_id,
            time_min=start_of_day,
            time_max=end_of_day
        )
        
        self.events = day_events
        return self._check_events_conflicts(date)
    
    def _check_events_conflicts(self, date: datetime.date) -> List[Dict]:
        """檢查事件列表中的所有衝突對"""
        conflicts = []
        checked = set()
        
        for i, event_a in enumerate(self.events):
            for event_b in self.events[i + 1:]:
                # 避免重複檢查同一對
                pair_key = tuple(sorted([event_a.get('id', ''), event_b.get('id', '')]))
                if not pair_key[0] or not pair_key[1]:
                    continue
                if pair_key in checked:
                    continue
                
                event_a_start = self._parse_time(event_a.get('start'))
                event_a_end = self._parse_time(event_a.get('end'))
                event_b_start = self._parse_time(event_b.get('start'))
                event_b_end = self._parse_time(event_b.get('end'))
                
                if None in [event_a_start, event_a_end, event_b_start, event_b_end]:
                    continue
                
                # 衝突檢測
                if event_a_start < event_b_end and event_a_end > event_b_start:
                    overlap_minutes = (
                        min(event_a_end, event_b_end) -
                        max(event_a_start, event_b_start)
                    ).total_seconds() / 60
                    
                    conflicts.append({
                        'event_a': event_a,
                        'event_b': event_b,
                        'overlap_minutes': round(overlap_minutes, 1),
                        'conflict_start': max(event_a_start, event_b_start),
                        'conflict_end': min(event_a_end, event_b_end)
                    })
                    
                checked.add(pair_key)
        
        return conflicts
    
    def _parse_time(self, time_str: str) -> Optional[datetime.datetime]:
        """解析時間字串為 datetime"""
        if not time_str:
            return None
        
        try:
            # 嘗試 ISO 格式 (帶時區)
            if '+' in time_str or time_str.endswith('Z'):
                return datetime.datetime.fromisoformat(
                    time_str.replace('Z', '+00:00')
                )
            # 純日期格式 YYYY-MM-DD
            elif len(time_str) == 10:
                return datetime.datetime.strptime(time_str, '%Y-%m-%d')
            # 其他 ISO 格式
            else:
                return datetime.datetime.fromisoformat(time_str)
        except Exception:
            return None
    
    def _ensure_date(
        self,
        dt: datetime.datetime,
        date: datetime.date
    ) -> datetime.datetime:
        """確保 datetime 的日期是指定的日期"""
        return dt.replace(
            year=date.year,
            month=date.month,
            day=date.day
        )
    
    def _merge_periods(
        self,
        periods: List[Tuple[datetime.datetime, datetime.datetime]]
    ) -> List[Tuple[datetime.datetime, datetime.datetime]]:
        """合併重疊的時間段"""
        if not periods:
            return []
        
        merged = [periods[0]]
        
        for current_start, current_end in periods[1:]:
            last_start, last_end = merged[-1]
            
            if current_start <= last_end:  # 重疊
                merged[-1] = (last_start, max(last_end, current_end))
            else:  # 不重疊
                merged.append((current_start, current_end))
        
        return merged
    
    def generate_report(self) -> str:
        """生成衝突檢測報告"""
        if not self.events:
            return "📅 暫無事件"
        
        lines = ["=" * 50, "📅 事件衝突檢測報告", "=" * 50]
        lines.append(f"📊 總事件數: {len(self.events)}")
        
        # 按日期分組
        by_date: Dict[str, List[Dict]] = {}
        for event in self.events:
            start = self._parse_time(event.get('start'))
            if start:
                date_key = start.strftime('%Y-%m-%d')
                if date_key not in by_date:
                    by_date[date_key] = []
                by_date[date_key].append(event)
        
        total_conflicts = 0
        
        for date_key in sorted(by_date.keys()):
            events_on_date = by_date[date_key]
            conflicts = self._check_events_conflicts(
                datetime.datetime.strptime(date_key, '%Y-%m-%d').date()
            )
            
            if conflicts:
                total_conflicts += len(conflicts)
                lines.append(f"\n📆 {date_key} ({len(conflicts)} 個衝突)")
                
                for c in conflicts:
                    lines.append(
                        f"  ⚠️ 衝突: {c['event_a'].get('summary', '(無標題)')}"
                        f" ↔ {c['event_b'].get('summary', '(無標題)')}"
                    )
                    lines.append(
                        f"     重疊: {c['overlap_minutes']} 分鐘"
                    )
        
        if total_conflicts == 0:
            lines.append("\n✅ 本週無衝突事件")
        else:
            lines.append(f"\n⚠️ 總共發現 {total_conflicts} 個衝突")
        
        return "\n".join(lines)


# ============================================================
# CLI 主程序
# ============================================================

def main():
    import argparse
    
    parser = argparse.ArgumentParser(description='Event Conflict Detector')
    parser.add_argument('--date', help='檢查日期 (YYYY-MM-DD)')
    parser.add_argument('--test', action='store_true', help='運行測試案例')
    
    args = parser.parse_args()
    
    if args.test:
        print("🧪 運行測試案例...")
        
        detector = EventConflictDetector()
        
        # 測試事件
        test_events = [
            {
                'id': 'event1',
                'summary': '數學 meeting',
                'start': '2024-01-15T10:00:00+08:00',
                'end': '2024-01-15T11:00:00+08:00'
            },
            {
                'id': 'event2',
                'summary': '英文 meeting',
                'start': '2024-01-15T10:30:00+08:00',
                'end': '2024-01-15T11:30:00+08:00'
            },
            {
                'id': 'event3',
                'summary': '全校朝會',
                'start': '2024-01-15T08:00:00+08:00',
                'end': '2024-01-15T09:00:00+08:00'
            },
            {
                'id': 'event4',
                'summary': '自由時間',
                'start': '2024-01-15T14:00:00+08:00',
                'end': '2024-01-15T15:00:00+08:00'
            }
        ]
        
        detector.add_events(test_events)
        
        print("\n📋 添加的測試事件：")
        for e in test_events:
            print(f"  - {e['summary']}: {e['start'][:16]} ~ {e['end'][:16]}")
        
        # 檢查衝突
        conflicts = detector.check_conflict(
            start_time=datetime.datetime(2024, 1, 15, 14, 30),
            end_time=datetime.datetime(2024, 1, 15, 15, 30)
        )
        
        print("\n🔍 檢查 14:30-15:30 是否衝突：")
        if conflicts:
            for c in conflicts:
                print(f"  ⚠️ 與「{c['event']['summary']}」衝突 {c['overlap_minutes']} 分鐘")
        else:
            print("  ✅ 無衝突")
        
        # 生成報告
        print("\n" + detector.generate_report())
        
        # 查找空閒時段
        print("\n🔎 查找 2024-01-15 空閒時段 (8:00-18:00)：")
        free_slots = detector.find_free_slots(
            datetime.date(2024, 1, 15),
            start_hour=8,
            end_hour=18
        )
        
        for slot in free_slots:
            print(
                f"  ✅ {slot['start'].strftime('%H:%M')} - "
                f"{slot['end'].strftime('%H:%M')} "
                f"({slot['duration_minutes']} 分鐘)"
            )


if __name__ == '__main__':
    main()
