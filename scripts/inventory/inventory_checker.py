#!/usr/bin/env python3
"""
Inventory Checker - 盤點記錄系統
掃描 QR Code / Barcode 並記錄盤點結果
"""

import sqlite3
import json
import os
import time
from datetime import datetime
from pathlib import Path

# Asset database path (share with asset_database.py)
DB_PATH = "/home/hoonsoropenclaw/.hermes/scripts/inventory/assets.db"
RECORDS_DIR = "/home/hoonsoropenclaw/.hermes/scripts/inventory/check_records"

class InventoryChecker:
    def __init__(self, db_path: str = None):
        self.db_path = db_path or DB_PATH
        os.makedirs(RECORDS_DIR, exist_ok=True)
    
    def parse_qr_data(self, qr_data: str) -> dict:
        """Parse QR code data into asset info"""
        try:
            return json.loads(qr_data)
        except json.JSONDecodeError:
            return {"id": qr_data, "raw": True}
    
    def check_asset(self, asset_id: str, location: str = None) -> dict:
        """Check a single asset during inventory"""
        conn = sqlite3.connect(self.db_path)
        conn.row_factory = sqlite3.Row
        cursor = conn.cursor()
        
        cursor.execute('SELECT * FROM assets WHERE id = ?', (asset_id,))
        row = cursor.fetchone()
        conn.close()
        
        if not row:
            return {
                "status": "not_found",
                "asset_id": asset_id,
                "message": "資產不存在於資料庫"
            }
        
        asset = dict(row)
        location_match = True
        
        if location and asset.get('location') != location:
            location_match = False
        
        return {
            "status": "ok",
            "asset_id": asset_id,
            "asset_name": asset.get('name'),
            "db_location": asset.get('location'),
            "scanned_location": location,
            "location_match": location_match,
            "category": asset.get('category'),
            "check_time": datetime.now().isoformat()
        }
    
    def batch_check(self, asset_ids: list, checker: str = "system",
                     location: str = None) -> dict:
        """Batch check multiple assets"""
        results = {
            "check_time": datetime.now().strftime('%Y-%m-%d %H:%M:%S'),
            "checker": checker,
            "location": location,
            "total": len(asset_ids),
            "found": 0,
            "not_found": 0,
            "location_mismatch": 0,
            "details": []
        }
        
        for asset_id in asset_ids:
            # Parse QR data if needed
            if isinstance(asset_id, str) and asset_id.startswith('{'):
                parsed = self.parse_qr_data(asset_id)
                asset_id = parsed.get('id', asset_id)
            
            result = self.check_asset(asset_id, location)
            
            if result['status'] == 'ok':
                results['found'] += 1
                if not result['location_match']:
                    results['location_mismatch'] += 1
            else:
                results['not_found'] += 1
            
            results['details'].append(result)
        
        # Save batch check record
        self._save_batch_record(results)
        
        return results
    
    def _save_batch_record(self, results: dict):
        """Save batch check results"""
        filename = f"check_{datetime.now().strftime('%Y%m%d_%H%M%S')}.json"
        filepath = os.path.join(RECORDS_DIR, filename)
        
        with open(filepath, 'w', encoding='utf-8') as f:
            json.dump(results, f, ensure_ascii=False, indent=2)
        
        print(f"[+] Check record saved: {filepath}")
    
    def compare_with_last_inventory(self) -> dict:
        """Compare current database with last inventory record"""
        # Find last check record
        records = sorted(Path(RECORDS_DIR).glob("check_*.json"))
        
        if not records:
            return {"error": "No previous inventory records found"}
        
        last_record_path = records[-1]
        with open(last_record_path, 'r', encoding='utf-8') as f:
            last_results = json.load(f)
        
        # Get all assets from database
        conn = sqlite3.connect(self.db_path)
        conn.row_factory = sqlite3.Row
        cursor = conn.cursor()
        cursor.execute('SELECT id FROM assets')
        db_assets = {row['id'] for row in cursor.fetchall()}
        conn.close()
        
        # Get checked assets from last record
        checked_ids = {d['asset_id'] for d in last_results.get('details', [])
                      if d.get('status') == 'ok'}
        
        # Find missing assets
        missing = db_assets - checked_ids
        
        return {
            "last_check_file": str(last_record_path),
            "last_check_time": last_results.get('check_time'),
            "total_db_assets": len(db_assets),
            "checked_assets": len(checked_ids),
            "missing_assets": list(missing),
            "missing_count": len(missing)
        }
    
    def generate_missing_report(self, output_path: str = None) -> str:
        """Generate report for missing assets"""
        comparison = self.compare_with_last_inventory()
        
        if "error" in comparison:
            return comparison["error"]
        
        missing = comparison.get('missing_assets', [])
        
        report_lines = [
            "=" * 60,
            "盤點異常報告 - 未盤到資產",
            "=" * 60,
            f"比對基準: {comparison['last_check_file']}",
            f"盤點時間: {comparison['last_check_time']}",
            f"資料庫資產總數: {comparison['total_db_assets']}",
            f"已完成盤點數: {comparison['checked_assets']}",
            f"未盤到資產數: {len(missing)}",
            "",
            "-" * 60,
            "未盤到資產清單:",
            "-" * 60
        ]
        
        if missing:
            conn = sqlite3.connect(self.db_path)
            conn.row_factory = sqlite3.Row
            cursor = conn.cursor()
            
            for i, asset_id in enumerate(missing, 1):
                cursor.execute('SELECT * FROM assets WHERE id = ?', (asset_id,))
                row = cursor.fetchone()
                if row:
                    asset = dict(row)
                    report_lines.append(
                        f"{i}. {asset_id} - {asset.get('name')} "
                        f"({asset.get('location')})"
                    )
            conn.close()
        else:
            report_lines.append("太好了！所有資產都已盤點完成。")
        
        report_lines.append("=" * 60)
        
        report_text = "\n".join(report_lines)
        
        if output_path:
            with open(output_path, 'w', encoding='utf-8') as f:
                f.write(report_text)
            print(f"[+] Missing report saved: {output_path}")
        
        return report_text

def simulate_barcode_scan(asset_ids: list) -> list:
    """Simulate barcode/QR scanner input"""
    # In real scenario, this would connect to actual scanner hardware
    print(f"[*] Simulating scan of {len(asset_ids)} items...")
    time.sleep(0.1)
    return asset_ids

def demo():
    """Demo: Simulated inventory check"""
    print("=== Inventory Checker Demo ===")
    checker = InventoryChecker()
    
    # Simulate scanning some assets
    test_scan = ["NB-2024-001", "PR-2024-001", "AC-2023-001", "NON-EXIST-001"]
    
    print("\n--- Single check ---")
    result = checker.check_asset("NB-2024-001", "圖書館2樓")
    print(f"Check result: {result}")
    
    print("\n--- Batch check ---")
    results = checker.batch_check(test_scan, checker="路可", location="圖書館2樓")
    print(f"Total: {results['total']}, Found: {results['found']}, "
          f"Not found: {results['not_found']}, "
          f"Location mismatch: {results['location_mismatch']}")
    
    print("\n--- Missing report ---")
    report = checker.generate_missing_report()
    print(report)

if __name__ == "__main__":
    demo()
