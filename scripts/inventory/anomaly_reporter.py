#!/usr/bin/env python3
"""
Anomaly Reporter - 異常通報工具
自動檢測並通報盤點異常
"""

import sqlite3
import json
import os
from datetime import datetime, timedelta
from pathlib import Path
from typing import List, Dict

# Config
DB_PATH = "/home/hoonsoropenclaw/.hermes/scripts/inventory/assets.db"
REPORTS_DIR = "/home/hoonsoropenclaw/.hermes/scripts/inventory/reports"
TEMPLATE_DIR = "/home/hoonsoropenclaw/.hermes/scripts/inventory/templates"

class AnomalyReporter:
    """盤點異常偵測與通報系統"""
    
    def __init__(self, db_path: str = None):
        self.db_path = db_path or DB_PATH
        os.makedirs(REPORTS_DIR, exist_ok=True)
        os.makedirs(TEMPLATE_DIR, exist_ok=True)
    
    def detect_missing_assets(self, expected_ids: List[str] = None) -> Dict:
        """偵測未盤點到的資產"""
        conn = sqlite3.connect(self.db_path)
        conn.row_factory = sqlite3.Row
        cursor = conn.cursor()
        
        if expected_ids is None:
            cursor.execute('SELECT id FROM assets')
            expected_ids = [row['id'] for row in cursor.fetchall()]
        
        conn.close()
        
        # 讀取最近盤點記錄
        records_dir = "/home/hoonsoropenclaw/.hermes/scripts/inventory/check_records"
        records = sorted(Path(records_dir).glob("check_*.json")) if os.path.exists(records_dir) else []
        
        if not records:
            return {"error": "No inventory records found"}
        
        last_record_path = records[-1]
        with open(last_record_path, 'r', encoding='utf-8') as f:
            last_data = json.load(f)
        
        checked_ids = {d['asset_id'] for d in last_data.get('details', []) 
                      if d.get('status') == 'ok'}
        
        missing = [aid for aid in expected_ids if aid not in checked_ids]
        
        return {
            "check_time": last_data.get('check_time'),
            "total_expected": len(expected_ids),
            "checked": len(checked_ids),
            "missing_count": len(missing),
            "missing_ids": missing
        }
    
    def detect_location_changes(self, threshold_days: int = 1) -> List[Dict]:
        """偵測位置變動的資產"""
        conn = sqlite3.connect(self.db_path)
        conn.row_factory = sqlite3.Row
        cursor = conn.cursor()
        
        # 取得所有有歷程記錄的資產
        cursor.execute('''
            SELECT i.asset_id, a.name, a.location as current_location,
                   i.check_date, i.location as recorded_location
            FROM inventory_records i
            JOIN assets a ON i.asset_id = a.id
            WHERE i.location IS NOT NULL AND i.location != ''
            ORDER BY i.check_date DESC
        ''')
        
        all_records = cursor.fetchall()
        conn.close()
        
        # Group by asset, keep latest
        latest_records = {}
        for row in all_records:
            asset_id = row['asset_id']
            if asset_id not in latest_records:
                latest_records[asset_id] = dict(row)
        
        # Filter for location changes
        changes = []
        for asset_id, record in latest_records.items():
            if record['recorded_location'] != record['current_location']:
                changes.append({
                    "asset_id": asset_id,
                    "asset_name": record['name'],
                    "system_location": record['current_location'],
                    "checked_location": record['recorded_location'],
                    "check_date": record['check_date']
                })
        
        return changes
    
    def detect_status_anomalies(self) -> List[Dict]:
        """偵測狀態異常的資產"""
        conn = sqlite3.connect(self.db_path)
        conn.row_factory = sqlite3.Row
        cursor = conn.cursor()
        
        # 取得非正常狀態的資產
        cursor.execute('''
            SELECT * FROM assets WHERE status != '正常' ORDER BY status
        ''')
        
        anomalies = []
        for row in cursor.fetchall():
            asset = dict(row)
            anomalies.append({
                "asset_id": asset['id'],
                "asset_name": asset['name'],
                "current_status": asset['status'],
                "location": asset['location'],
                "remark": asset.get('remark', '')
            })
        
        conn.close()
        return anomalies
    
    def detect_maintenance_due(self, days_threshold: int = 30) -> List[Dict]:
        """偵測需要保養維護的資產"""
        conn = sqlite3.connect(self.db_path)
        conn.row_factory = sqlite3.Row
        cursor = conn.cursor()
        
        # 假設有 purchase_date 計算保養期限
        # 這裡用 purchase_date 超過一定時間當作需要保養
        threshold_date = (datetime.now() - timedelta(days=365)).strftime('%Y-%m-%d')
        
        cursor.execute('''
            SELECT * FROM assets 
            WHERE purchase_date < ? AND category IN ('資訊設備', '週邊設備')
            ORDER BY purchase_date
        ''', (threshold_date,))
        
        due_maintenance = []
        for row in cursor.fetchall():
            asset = dict(row)
            purchase_date = datetime.strptime(asset['purchase_date'], '%Y-%m-%d')
            days_old = (datetime.now() - purchase_date).days
            
            due_maintenance.append({
                "asset_id": asset['id'],
                "asset_name": asset['name'],
                "purchase_date": asset['purchase_date'],
                "days_in_use": days_old,
                "location": asset['location']
            })
        
        conn.close()
        return due_maintenance
    
    def generate_anomaly_report(self, output_format: str = "text") -> str:
        """Generate comprehensive anomaly report"""
        report_id = datetime.now().strftime('%Y%m%d_%H%M%S')
        
        report = {
            "report_id": report_id,
            "generated_at": datetime.now().isoformat(),
            "section_missing": self.detect_missing_assets(),
            "section_location_changes": self.detect_location_changes(),
            "section_status_anomalies": self.detect_status_anomalies(),
            "section_maintenance_due": self.detect_maintenance_due(),
        }
        
        # Save JSON report
        json_path = os.path.join(REPORTS_DIR, f"anomaly_report_{report_id}.json")
        with open(json_path, 'w', encoding='utf-8') as f:
            json.dump(report, f, ensure_ascii=False, indent=2)
        
        print(f"[+] JSON report saved: {json_path}")
        
        # Generate text report
        text_lines = self._format_text_report(report, output_format)
        
        if output_format == "text":
            return text_lines
        
        return report  # Return dict for further processing
    
    def _format_text_report(self, report: Dict, output_format: str = "text") -> str:
        """Format report as readable text"""
        lines = [
            "=" * 70,
            "設備盤點異常通報報告",
            f"報告編號: {report['report_id']}",
            f"產生時間: {report['generated_at']}",
            "=" * 70,
            ""
        ]
        
        # Missing section
        missing = report.get('section_missing', {})
        if 'error' not in missing:
            lines.extend([
                "【一資產未盤點統計】",
                "-" * 50,
                f"盤點時間: {missing.get('check_time', 'N/A')}",
                f"資料庫總數: {missing.get('total_expected', 0)}",
                f"已完成盤點: {missing.get('checked', 0)}",
                f"未盤到資產: {missing.get('missing_count', 0)}",
                ""
            ])
            
            if missing.get('missing_ids'):
                lines.append("未盤到資產清單:")
                for i, aid in enumerate(missing['missing_ids'], 1):
                    lines.append(f"  {i}. {aid}")
                lines.append("")
        
        # Location changes
        changes = report.get('section_location_changes', [])
        if changes:
            lines.extend([
                "【二、位置異動偵測】",
                "-" * 50,
                f"偵測到 {len(changes)} 項位置異動:"
                ""
            ])
            for change in changes[:10]:  # Show top 10
                lines.append(
                    f"  • {change['asset_id']} - {change['asset_name']}\n"
                    f"    系統位置: {change['system_location']} → "
                    f"實際位置: {change['checked_location']}"
                )
            lines.append("")
        
        # Status anomalies
        anomalies = report.get('section_status_anomalies', [])
        if anomalies:
            lines.extend([
                "【三、狀態異常資產】",
                "-" * 50,
                f"共 {len(anomalies)} 項狀態異常:"
                ""
            ])
            for a in anomalies:
                lines.append(f"  • {a['asset_id']} - {a['asset_name']}: {a['current_status']}")
            lines.append("")
        
        # Maintenance due
        maintenance = report.get('section_maintenance_due', [])
        if maintenance:
            lines.extend([
                "【四、保養到期提醒】",
                "-" * 50,
                f"共 {len(maintenance)} 項設備可能需要保養:"
                ""
            ])
            for m in maintenance[:10]:
                lines.append(
                    f"  • {m['asset_id']} - {m['asset_name']}\n"
                    f"    購置日期: {m['purchase_date']} (已使用 {m['days_in_use']} 天)"
                )
            lines.append("")
        
        # Summary
        lines.extend([
            "=" * 70,
            f"報告結束 - 共 {report['report_id']}",
            "=" * 70
        ])
        
        report_text = "\n".join(lines)
        
        # Save text report
        text_path = os.path.join(REPORTS_DIR, f"anomaly_report_{report['report_id']}.txt")
        with open(text_path, 'w', encoding='utf-8') as f:
            f.write(report_text)
        
        print(f"[+] Text report saved: {text_path}")
        
        return report_text
    
    def send_email_notification(self, recipients: List[str], report: Dict = None) -> bool:
        """Send email notification for anomalies (placeholder)"""
        # 這裡整合 email 發送功能
        # 可使用 smtplib 或第三方服務如 SendGrid, Mailgun
        print(f"[*] Would send email to: {recipients}")
        return True

def demo():
    """Demo: Generate anomaly report"""
    print("=== Anomaly Reporter Demo ===")
    reporter = AnomalyReporter()
    
    report_text = reporter.generate_anomaly_report(output_format="text")
    print("\n" + report_text)

if __name__ == "__main__":
    demo()
