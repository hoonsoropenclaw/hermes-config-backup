#!/usr/bin/env python3
"""
Google Calendar Sync System - 學校行事曆同步解決方案
Google Calendar API v3 Python Client Integration

功能：
- OAuth 2.0 驗證流程
- 行事曆事件 CRUD 操作
- 學校行事曆同步
- 事件衝突檢測
"""

import os
import json
import pickle
import datetime
import webbrowser
from pathlib import Path
from typing import Optional

# Google API Libraries
from googleapiclient.discovery import build
from google_auth_oauthlib.flow import InstalledAppFlow
from google.auth.transport.requests import Request

# ============================================================
# OAuth Handler - 驗證流程管理
# ============================================================

class GoogleCalendarOAuth:
    """
    Google Calendar API OAuth 2.0 驗證處理模組
    
    流程圖解：
    ┌─────────────────────────────────────────────────────────────┐
    │                    OAuth 2.0 驗證流程                        │
    ├─────────────────────────────────────────────────────────────┤
    │                                                             │
    │   ┌──────────┐    1. 首次驗證     ┌──────────────────┐       │
    │   │  使用者  │ ──────────────────▶│  產生授權 URL   │       │
    │   └──────────┘                    └──────────────────┘       │
    │        │                                   │                   │
    │        │ 2. 用戶點擊 URL                        │                   │
    │        ▼                                   ▼                   │
    │   ┌──────────┐                    ┌──────────────────┐       │
    │   │ 瀏覽器   │ ◀───────────────────│  開啟授權頁面    │       │
    │   └──────────┘                    │  (Google 登入)   │       │
    │        │                           └──────────────────┘       │
    │        │ 3. 授權成功                                    │
    │        ▼                                                │
    │   ┌──────────┐    4. 領取代碼    ┌──────────────────┐       │
    │   │ callback │ ◀───────────────▶│  換取 AccessToken │       │
    │   └──────────┘                    └──────────────────┘       │
    │                                        │                    │
    │                                        ▼                    │
    │   ┌──────────┐                    ┌──────────────────┐       │
    │   │ Token    │ ◀─────────────────│  儲存 credentials │       │
    │   │ 文件     │                    │  (token.pickle)  │       │
    │   └──────────┘                    └──────────────────┘       │
    │                                                             │
    └─────────────────────────────────────────────────────────────┘
    
    API 權限範圍：
    - https://www.googleapis.com/auth/calendar       (完整读写)
    - https://www.googleapis.com/auth/calendar.readonly (只读)
    """
    
    SCOPES = [
        'https://www.googleapis.com/auth/calendar',
        'https://www.googleapis.com/auth/calendar.readonly'
    ]
    
    def __init__(self, credentials_path: str = None, token_path: str = None):
        """
        初始化 OAuth 處理器
        
        Args:
            credentials_path: Google API Console 下載的 credentials.json 路徑
            token_path: 存儲 access token 的 pickle 文件路徑
        """
        self.workspace = Path.home() / '.openclaw' / 'workspace'
        self.credentials_path = credentials_path or str(
            self.workspace / 'scripts' / 'calendar' / 'credentials.json'
        )
        self.token_path = token_path or str(
            self.workspace / 'scripts' / 'calendar' / 'token.pickle'
        )
        self.service = None
    
    def get_credentials(self) -> Optional[object]:
        """
        獲取或刷新 Google API 認證憑證
        
        Returns:
            google.auth.credentials: 驗證通過的憑證對象
        """
        creds = None
        
        # 檢查是否有已存在的 token
        if os.path.exists(self.token_path):
            with open(self.token_path, 'rb') as token:
                creds = pickle.load(token)
        
        # 驗證憑證是否有效，必要时刷新
        if not creds or not creds.valid:
            if creds and creds.expired and creds.refresh_token:
                print("🔄 憑證已過期，正在刷新...")
                creds.refresh(Request())
            else:
                print("📝 需要進行 OAuth 驗證...")
                return None  # 需要用戶授權
        
        return creds
    
    def authenticate(self) -> bool:
        """
        執行完整的 OAuth 2.0 驗證流程
        
        Returns:
            bool: 驗證是否成功
        """
        creds = self.get_credentials()
        
        if creds is None:
            # 需要進行首次驗證
            if not os.path.exists(self.credentials_path):
                print(f"❌ 找不到 credentials.json: {self.credentials_path}")
                print("📝 請到 Google Cloud Console 下載並放置於此路徑")
                return False
            
            flow = InstalledAppFlow.from_client_secrets_file(
                self.credentials_path,
                self.SCOPES
            )
            creds = flow.run_local_server(
                port=0,
                open_browser=True,
                prompt='consent'
            )
        
        # 保存憑證
        with open(self.token_path, 'wb') as token:
            pickle.dump(creds, token)
        
        print("✅ OAuth 驗證成功！")
        return True
    
    def build_service(self):
        """
        建立 Google Calendar API 服務對象
        
        Returns:
            googleapiclient.discovery.Resource: Calendar API 服務對象
        """
        creds = self.get_credentials()
        
        if not creds or not creds.valid:
            if not self.authenticate():
                raise Exception("OAuth 驗證失敗")
        
        self.service = build('calendar', 'v3', credentials=creds)
        return self.service


# ============================================================
# Calendar Sync - 行事曆同步核心
# ============================================================

class GoogleCalendarSync:
    """
    Google Calendar 同步核心類
    
    功能：
    - 列出所有行事曆
    - 創建/讀取/更新/刪除 事件
    - 同步學校行事曆
    - 衝突檢測
    """
    
    def __init__(self, service=None):
        self.service = service
        self.initialized = False
    
    def initialize(self, service=None):
        """初始化或注入 service"""
        if service:
            self.service = service
            self.initialized = True
        elif not self.initialized:
            oauth = GoogleCalendarOAuth()
            self.service = oauth.build_service()
            self.initialized = True
    
    def list_calendars(self) -> list:
        """
        列出所有已訂閱的行事曆
        
        Returns:
            list: 行事曆列表 [{id, summary, description, ...}, ...]
        """
        self._check_service()
        
        calendars = []
        page_token = None
        
        while True:
            calendar_list = self.service.calendarList().list(
                pageToken=page_token,
                showDeleted=False
            ).execute()
            
            for cal in calendar_list.get('items', []):
                calendars.append({
                    'id': cal.get('id'),
                    'summary': cal.get('summary'),
                    'description': cal.get('description', ''),
                    'primary': cal.get('primary', False),
                    'accessRole': cal.get('accessRole'),
                    'backgroundColor': cal.get('backgroundColor'),
                })
            
            page_token = calendar_list.get('nextPageToken')
            if not page_token:
                break
        
        return calendars
    
    def get_calendar_id(self, calendar_name: str) -> Optional[str]:
        """
        按名稱查找行事曆 ID
        
        Args:
            calendar_name: 行事曆名稱（部分匹配）
            
        Returns:
            str: 行事曆 ID，未找到返回 None
        """
        calendars = self.list_calendars()
        
        for cal in calendars:
            if calendar_name.lower() in cal['summary'].lower():
                return cal['id']
        
        return None
    
    def list_events(
        self,
        calendar_id: str = 'primary',
        time_min: datetime.datetime = None,
        time_max: datetime.datetime = None,
        max_results: int = 100,
        single_events: bool = True,
        order_by_mapping: bool = True
    ) -> list:
        """
        列出行事曆中的事件
        
        Args:
            calendar_id: 行事曆 ID，'primary' 為主行事曆
            time_min: 起始時間
            time_max: 結束時間
            max_results: 最大返回數量
            single_events: 是否展開重複事件
            order_by_mapping: 按開始時間排序
            
        Returns:
            list: 事件列表
        """
        self._check_service()
        
        # 預設時間範圍：未來 30 天
        if not time_min:
            time_min = datetime.datetime.now(datetime.timezone.utc)
        if not time_max:
            time_max = time_min + datetime.timedelta(days=30)
        
        events_params = {
            'calendarId': calendar_id,
            'timeMin': time_min.isoformat(),
            'timeMax': time_max.isoformat(),
            'maxResults': max_results,
            'singleEvents': single_events,
            'orderBy': 'startTime' if order_by_mapping else 'updated'
        }
        
        events = []
        page_token = None
        
        while True:
            events_params['pageToken'] = page_token
            result = self.service.events().list(**events_params).execute()
            
            for event in result.get('items', []):
                events.append(self._parse_event(event))
            
            page_token = result.get('nextPageToken')
            if not page_token:
                break
        
        return events
    
    def _parse_event(self, event: dict) -> dict:
        """解析事件數據為統一格式"""
        start = event.get('start', {})
        end = event.get('end', {})
        
        # 處理全天事件 vs 時間事件
        if 'date' in start:  # 全天事件
            start_time = start['date']
            end_time = end.get('date', start['date'])
        else:  # 時間事件
            start_time = start.get('dateTime', '')
            end_time = end.get('dateTime', '')
        
        return {
            'id': event.get('id'),
            'summary': event.get('summary', '(無標題)'),
            'description': event.get('description', ''),
            'location': event.get('location', ''),
            'start': start_time,
            'end': end_time,
            'all_day': 'date' in start,
            'creator': event.get('creator', {}).get('email', ''),
            'status': event.get('status'),
            'html_link': event.get('htmlLink', ''),
            'recurring': bool(event.get('recurringEventId')),
        }
    
    def create_event(
        self,
        summary: str,
        start_time: datetime.datetime,
        end_time: datetime.datetime = None,
        calendar_id: str = 'primary',
        description: str = '',
        location: str = '',
        all_day: bool = False,
        reminder_minutes: int = 30,
        color_id: int = None
    ) -> dict:
        """
        創建新事件
        
        Args:
            summary: 事件標題
            start_time: 開始時間（datetime 或 date）
            end_time: 結束時間（若為 None，则 start_time + 1 小時）
            calendar_id: 行事曆 ID
            description: 事件描述
            location: 地點
            all_day: 是否為全天事件
            reminder_minutes: 提醒分鐘數
            color_id: 顏色 ID (1-11)
            
        Returns:
            dict: 創建的事件對象
        """
        self._check_service()
        
        if end_time is None:
            end_time = start_time + datetime.timedelta(hours=1)
        
        event = {
            'summary': summary,
            'description': description,
            'location': location,
        }
        
        if all_day:
            # 全天事件
            if isinstance(start_time, datetime.datetime):
                start_time = start_time.date()
            if isinstance(end_time, datetime.datetime):
                end_time = end_time.date()
            
            event['start'] = {'date': str(start_time)}
            event['end'] = {'date': str(end_time)}
        else:
            # 時間事件
            event['start'] = {'dateTime': start_time.isoformat()}
            event['end'] = {'dateTime': end_time.isoformat()}
        
        # 添加提醒
        if reminder_minutes > 0:
            event['reminders'] = {
                'useDefault': False,
                'overrides': [
                    {
                        'method': 'popup',
                        'minutes': reminder_minutes
                    }
                ]
            }
        
        # 設置顏色
        if color_id:
            event['colorId'] = str(color_id)
        
        created_event = self.service.events().insert(
            calendarId=calendar_id,
            body=event
        ).execute()
        
        print(f"✅ 事件已創建: {created_event.get('id')}")
        return self._parse_event(created_event)
    
    def update_event(
        self,
        event_id: str,
        calendar_id: str = 'primary',
        **kwargs
    ) -> dict:
        """
        更新事件
        
        Args:
            event_id: 事件 ID
            calendar_id: 行事曆 ID
            **kwargs: 要更新的欄位 (summary, description, start, end, ...)
            
        Returns:
            dict: 更新後的事件對象
        """
        self._check_service()
        
        # 獲取現有事件
        event = self.service.events().get(
            calendarId=calendar_id,
            eventId=event_id
        ).execute()
        
        # 更新欄位
        for key, value in kwargs.items():
            if value is not None:
                event[key] = value
        
        updated_event = self.service.events().update(
            calendarId=calendar_id,
            eventId=event_id,
            body=event
        ).execute()
        
        print(f"✅ 事件已更新: {event_id}")
        return self._parse_event(updated_event)
    
    def delete_event(
        self,
        event_id: str,
        calendar_id: str = 'primary'
    ) -> bool:
        """
        刪除事件
        
        Args:
            event_id: 事件 ID
            calendar_id: 行事曆 ID
            
        Returns:
            bool: 刪除是否成功
        """
        self._check_service()
        
        try:
            self.service.events().delete(
                calendarId=calendar_id,
                eventId=event_id
            ).execute()
            print(f"✅ 事件已刪除: {event_id}")
            return True
        except Exception as e:
            print(f"❌ 刪除失敗: {e}")
            return False
    
    def quick_add_event(
        self,
        text: str,
        calendar_id: str = 'primary'
    ) -> dict:
        """
        快速新增事件（Google 自動解析文字）
        
        Args:
            text: 事件描述文字，如 "Meeting tomorrow at 3pm"
            calendar_id: 行事曆 ID
            
        Returns:
            dict: 創建的事件對象
        """
        self._check_service()
        
        created_event = self.service.events().quickAdd(
            calendarId=calendar_id,
            text=text
        ).execute()
        
        print(f"✅ 快速新增成功: {created_event.get('id')}")
        return self._parse_event(created_event)
    
    def _check_service(self):
        """檢查 service 是否已初始化"""
        if not self.service:
            raise Exception("Calendar service 未初始化，請先調用 initialize()")


# ============================================================
# Event Conflict Detector - 事件衝突檢測
# ============================================================

class EventConflictDetector:
    """
    事件衝突檢測器
    
    衝突檢測演算法：
    ┌──────────────────────────────────────────────────────────┐
    │                   衝突檢測原理                            │
    ├──────────────────────────────────────────────────────────┤
    │                                                          │
    │  事件 A:    |████████████|                               │
    │  事件 B:              |████████████|     → 不衝突        │
    │                                                          │
    │  事件 A:    |████████████|                               │
    │  事件 B:            |████████████|       → 衝突（重疊）   │
    │                                                          │
    │  事件 A:    |████████████|                               │
    │  事件 B:  |████████████|           → 衝突（包含）         │
    │                                                          │
    │  衝突條件:  A.start < B.end AND A.end > B.start          │
    │                                                          │
    └──────────────────────────────────────────────────────────┘
    """
    
    def __init__(self):
        self.events = []
    
    def add_event(self, event: dict):
        """添加事件到檢測队列"""
        self.events.append(event)
    
    def add_events(self, events: list):
        """批量添加事件"""
        self.events.extend(events)
    
    def check_conflict(
        self,
        start_time: datetime.datetime,
        end_time: datetime.datetime,
        exclude_event_id: str = None
    ) -> list:
        """
        檢查新事件是否與現有事件衝突
        
        Args:
            start_time: 新事件開始時間
            end_time: 新事件結束時間
            exclude_event_id: 要排除的事件 ID（如更新時排除自身）
            
        Returns:
            list: 衝突事件列表 [{event, overlap_minutes}, ...]
        """
        conflicts = []
        
        for event in self.events:
            # 排除自身
            if exclude_event_id and event['id'] == exclude_event_id:
                continue
            
            # 解析事件時間
            event_start = self._parse_time(event['start'])
            event_end = self._parse_time(event['end'])
            
            if event_start is None or event_end is None:
                continue
            
            # 衝突檢測
            if start_time < event_end and end_time > event_start:
                # 計算重疊時間
                overlap_start = max(start_time, event_start)
                overlap_end = min(end_time, event_end)
                overlap_minutes = (overlap_end - overlap_start).total_seconds() / 60
                
                conflicts.append({
                    'event': event,
                    'overlap_minutes': overlap_minutes,
                    'overlap_start': overlap_start,
                    'overlap_end': overlap_end
                })
        
        return conflicts
    
    def check_day_conflicts(
        self,
        date: datetime.date,
        calendar_id: str = 'primary',
        service = None
    ) -> list:
        """
        檢查特定日期的所有衝突
        
        Args:
            date: 要檢查的日期
            calendar_id: 行事曆 ID
            service: Calendar API service
            
        Returns:
            list: 衝突事件 ID 列表
        """
        if not service:
            raise ValueError("需要提供 Calendar API service")
        
        # 獲取當日事件
        start_of_day = datetime.datetime.combine(date, datetime.time.min)
        end_of_day = datetime.datetime.combine(
            date, 
            datetime.time.max,
            tzinfo=datetime.timezone.utc
        )
        
        sync = GoogleCalendarSync(service)
        day_events = sync.list_events(
            calendar_id=calendar_id,
            time_min=start_of_day,
            time_max=end_of_day
        )
        
        # 轉換為時間序列
        self.events = day_events
        
        # 檢查所有衝突組合
        conflicts = []
        checked = set()
        
        for i, event_a in enumerate(day_events):
            for event_b in day_events[i+1:]:
                pair_key = tuple(sorted([event_a['id'], event_b['id']]))
                if pair_key in checked:
                    continue
                
                event_a_start = self._parse_time(event_a['start'])
                event_a_end = self._parse_time(event_a['end'])
                event_b_start = self._parse_time(event_b['start'])
                event_b_end = self._parse_time(event_b['end'])
                
                if (event_a_start < event_b_end and 
                    event_a_end > event_b_start):
                    conflicts.append({
                        'event_a': event_a,
                        'event_b': event_b,
                        'overlap_minutes': (
                            min(event_a_end, event_b_end) - 
                            max(event_a_start, event_b_start)
                        ).total_seconds() / 60
                    })
                    checked.add(pair_key)
        
        return conflicts
    
    def _parse_time(self, time_str: str) -> Optional[datetime.datetime]:
        """解析時間字串為 datetime"""
        if not time_str:
            return None
        
        try:
            # 嘗試 ISO 格式
            if '+' in time_str or 'Z' in time_str:
                return datetime.datetime.fromisoformat(
                    time_str.replace('Z', '+00:00')
                )
            elif len(time_str) == 10:  # 日期格式 YYYY-MM-DD
                return datetime.datetime.strptime(time_str, '%Y-%m-%d')
            else:
                return datetime.datetime.fromisoformat(time_str)
        except:
            return None


# ============================================================
# School Calendar Sync - 學校行事曆整合
# ============================================================

class SchoolCalendarSync:
    """
    學校行事曆同步整合器
    
    功能：
    - 學校行事曆事件批量導入
    - 學期行事曆自動生成
    - 行事曆分類標籤
    """
    
    # 學校行事曆顏色配置
    EVENT_COLORS = {
        'exam': 11,        # 紅色 - 考試
        'holiday': 10,     # 綠色 - 放假
        'meeting': 5,      # 藍色 - 會議
        'event': 6,        # 紫色 - 活動
        'class': 9,        # 橙色 - 課程
        'other': 1         # 灰色 - 其他
    }
    
    def __init__(self, calendar_sync: GoogleCalendarSync):
        self.sync = calendar_sync
    
    def batch_import_events(
        self,
        events: list,
        calendar_id: str = 'primary',
        dry_run: bool = False
    ) -> dict:
        """
        批量導入事件
        
        Args:
            events: 事件列表
                [{
                    'summary': '標題',
                    'start': '2024-01-15',
                    'end': '2024-01-15',
                    'type': 'exam' | 'holiday' | 'meeting' | 'event',
                    'description': '描述'
                }, ...]
            calendar_id: 目標行事曆
            dry_run: 是否為測試模式（不實際創建）
            
        Returns:
            dict: {success: int, failed: int, created: list, errors: list}
        """
        results = {
            'success': 0,
            'failed': 0,
            'created': [],
            'errors': []
        }
        
        for event_data in events:
            try:
                # 解析時間
                start = event_data.get('start')
                end = event_data.get('end', start)
                
                if isinstance(start, str):
                    start = datetime.datetime.fromisoformat(start)
                if isinstance(end, str):
                    end = datetime.datetime.fromisoformat(end)
                
                # 獲取顏色
                event_type = event_data.get('type', 'other')
                color_id = self.EVENT_COLORS.get(event_type)
                
                # 準備創建
                event_params = {
                    'summary': event_data.get('summary', ''),
                    'start_time': start,
                    'end_time': end,
                    'description': event_data.get('description', ''),
                    'all_day': event_data.get('all_day', True),
                }
                
                if color_id:
                    event_params['color_id'] = color_id
                
                if dry_run:
                    print(f"🔍 [dry_run] 將創建: {event_params['summary']}")
                    results['success'] += 1
                else:
                    created = self.sync.create_event(
                        calendar_id=calendar_id,
                        **event_params
                    )
                    results['created'].append(created['id'])
                    results['success'] += 1
                    
            except Exception as e:
                results['failed'] += 1
                results['errors'].append({
                    'event': event_data.get('summary', ''),
                    'error': str(e)
                })
        
        return results
    
    def generate_semester_calendar(
        self,
        year: int,
        semester: int,
        calendar_id: str = 'primary'
    ) -> list:
        """
        生成學期行事曆（示範：按教育局校曆）
        
        Args:
            year: 學年度
            semester: 學期 (1 or 2)
            calendar_id: 目標行事曆
            
        Returns:
            list: 生成的行事曆事件列表
        """
        events = []
        
        # 根據台灣教育局行事曆（範例格式）
        if semester == 1:
            # 第一學期：8/1 開學 - 1/31 寒假
            start_date = f"{year}-08-01"
            end_date = f"{year+1}-01-31"
            
            # 重要日期
            special_dates = [
                {'date': f"{year}-09-10", 'summary': '中秋連假', 'type': 'holiday'},
                {'date': f"{year}-10-10", 'summary': '國慶日', 'type': 'holiday'},
                {'date': f"{year}-12-20", 'summary': '期末考試週', 'type': 'exam'},
                {'date': f"{year+1}-01-01", 'summary': '元旦', 'type': 'holiday'},
            ]
        else:
            # 第二學期：2/1 開學 - 6/30 暑假
            start_date = f"{year}-02-01"
            end_date = f"{year}-06-30"
            
            special_dates = [
                {'date': f"{year}-02-28", 'summary': '和平連假', 'type': 'holiday'},
                {'date': f"{year}-04-04", 'summary': '兒童節', 'type': 'holiday'},
                {'date': f"{year}-06-20", 'summary': '期末考試週', 'type': 'exam'},
            ]
        
        return events


# ============================================================
# CLI 主程序
# ============================================================

def main():
    """
    命令行介面範例
    """
    import argparse
    
    parser = argparse.ArgumentParser(description='Google Calendar Sync System')
    subparsers = parser.add_subparsers(dest='command', help='子命令')
    
    # 驗證命令
    auth_parser = subparsers.add_parser('auth', help='執行 OAuth 驗證')
    
    # 列表命令
    list_parser = subparsers.add_parser('list', help='列出所有行事曆')
    list_parser.add_argument('--events', action='store_true', help='列出事件')
    list_parser.add_argument('--calendar', default='primary', help='行事曆 ID')
    
    # 創建事件命令
    create_parser = subparsers.add_parser('create', help='創建事件')
    create_parser.add_argument('--title', required=True, help='事件標題')
    create_parser.add_argument('--start', required=True, help='開始時間 (YYYY-MM-DD)')
    create_parser.add_argument('--end', help='結束時間 (YYYY-MM-DD)')
    create_parser.add_argument('--calendar', default='primary', help='行事曆 ID')
    create_parser.add_argument('--desc', default='', help='描述')
    create_parser.add_argument('--location', default='', help='地點')
    
    args = parser.parse_args()
    
    if not args.command:
        parser.print_help()
        return
    
    # 初始化 OAuth 和 Sync
    oauth = GoogleCalendarOAuth()
    oauth.authenticate()
    sync = GoogleCalendarSync()
    sync.initialize(oauth.service)
    
    if args.command == 'auth':
        print("✅ 驗證完成！")
        
    elif args.command == 'list':
        if args.events:
            events = sync.list_events(calendar_id=args.calendar)
            print(f"\n📅 事件列表（共 {len(events)} 個）：")
            for e in events:
                print(f"  • {e['start'][:10]} | {e['summary']}")
        else:
            calendars = sync.list_calendars()
            print(f"\n📅 行事曆列表（共 {len(calendars)} 個）：")
            for cal in calendars:
                marker = "⭐" if cal.get('primary') else "  "
                print(f"  {marker} {cal['summary']} ({cal['id']})")
    
    elif args.command == 'create':
        start = datetime.datetime.strptime(args.start, '%Y-%m-%d')
        end = datetime.datetime.strptime(args.end, '%Y-%m-%d') if args.end else start
        
        sync.create_event(
            summary=args.title,
            start_time=start,
            end_time=end,
            calendar_id=args.calendar,
            description=args.desc,
            location=args.location,
            all_day=True
        )


if __name__ == '__main__':
    main()
