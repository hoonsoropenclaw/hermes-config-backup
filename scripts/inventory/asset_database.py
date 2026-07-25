#!/usr/bin/env python3
"""
Asset Database Manager
學校資產資料庫管理系統
"""

import sqlite3
import csv
import json
import os
from datetime import datetime
from pathlib import Path

DB_PATH = "/home/hoonsoropenclaw/.hermes/scripts/inventory/assets.db"

class AssetDatabase:
    def __init__(self, db_path: str = None):
        self.db_path = db_path or DB_PATH
        self.init_db()
    
    def init_db(self):
        """Initialize database schema"""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS assets (
                id TEXT PRIMARY KEY,
                name TEXT NOT NULL,
                category TEXT,
                brand TEXT,
                model TEXT,
                serial_number TEXT,
                purchase_date TEXT,
                purchase_price REAL,
                location TEXT,
                custodian TEXT,
                status TEXT DEFAULT '正常',
                remark TEXT,
                created_at TEXT DEFAULT CURRENT_TIMESTAMP,
                updated_at TEXT DEFAULT CURRENT_TIMESTAMP
            )
        ''')
        
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS inventory_records (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                asset_id TEXT,
                check_date TEXT,
                checker TEXT,
                status TEXT,
                remark TEXT,
                location TEXT,
                FOREIGN KEY (asset_id) REFERENCES assets(id)
            )
        ''')
        
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS categories (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                name TEXT UNIQUE,
                parent_id INTEGER,
                remark TEXT
            )
        ''')
        
        conn.commit()
        conn.close()
        print(f"[+] Database initialized: {self.db_path}")
    
    def add_asset(self, asset: dict) -> bool:
        """Add a new asset"""
        try:
            conn = sqlite3.connect(self.db_path)
            cursor = conn.cursor()
            cursor.execute('''
                INSERT INTO assets (id, name, category, brand, model, serial_number,
                                   purchase_date, purchase_price, location, custodian,
                                   status, remark)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            ''', (
                asset.get('id'),
                asset.get('name'),
                asset.get('category'),
                asset.get('brand'),
                asset.get('model'),
                asset.get('serial_number'),
                asset.get('purchase_date'),
                asset.get('purchase_price'),
                asset.get('location'),
                asset.get('custodian'),
                asset.get('status', '正常'),
                asset.get('remark')
            ))
            conn.commit()
            conn.close()
            print(f"[+] Asset added: {asset.get('id')} - {asset.get('name')}")
            return True
        except sqlite3.IntegrityError:
            print(f"[!] Asset already exists: {asset.get('id')}")
            return False
    
    def get_asset(self, asset_id: str) -> dict:
        """Get asset by ID"""
        conn = sqlite3.connect(self.db_path)
        conn.row_factory = sqlite3.Row
        cursor = conn.cursor()
        cursor.execute('SELECT * FROM assets WHERE id = ?', (asset_id,))
        row = cursor.fetchone()
        conn.close()
        return dict(row) if row else None
    
    def update_asset(self, asset_id: str, updates: dict) -> bool:
        """Update asset information"""
        updates['updated_at'] = datetime.now().isoformat()
        set_clause = ', '.join([f"{k} = ?" for k in updates.keys()])
        values = list(updates.values()) + [asset_id]
        
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        cursor.execute(f'UPDATE assets SET {set_clause} WHERE id = ?', values)
        conn.commit()
        affected = cursor.rowcount
        conn.close()
        print(f"[+] Asset updated: {asset_id}")
        return affected > 0
    
    def delete_asset(self, asset_id: str) -> bool:
        """Delete an asset"""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        cursor.execute('DELETE FROM assets WHERE id = ?', (asset_id,))
        conn.commit()
        affected = cursor.rowcount
        conn.close()
        print(f"[+] Asset deleted: {asset_id}")
        return affected > 0
    
    def search_assets(self, keyword: str = None, category: str = None,
                       location: str = None, status: str = None) -> list:
        """Search assets with filters"""
        conn = sqlite3.connect(self.db_path)
        conn.row_factory = sqlite3.Row
        cursor = conn.cursor()
        
        query = 'SELECT * FROM assets WHERE 1=1'
        params = []
        
        if keyword:
            query += ' AND (name LIKE ? OR id LIKE ? OR serial_number LIKE ?)'
            kw = f'%{keyword}%'
            params.extend([kw, kw, kw])
        
        if category:
            query += ' AND category = ?'
            params.append(category)
        
        if location:
            query += ' AND location = ?'
            params.append(location)
        
        if status:
            query += ' AND status = ?'
            params.append(status)
        
        cursor.execute(query, params)
        rows = cursor.fetchall()
        conn.close()
        return [dict(row) for row in rows]
    
    def record_inventory(self, asset_id: str, checker: str, status: str,
                         remark: str = '', location: str = None) -> bool:
        """Record an inventory check"""
        check_date = datetime.now().strftime('%Y-%m-%d %H:%M:%S')
        
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        cursor.execute('''
            INSERT INTO inventory_records (asset_id, check_date, checker, status, remark, location)
            VALUES (?, ?, ?, ?, ?, ?)
        ''', (asset_id, check_date, checker, status, remark, location))
        conn.commit()
        conn.close()
        print(f"[+] Inventory recorded: {asset_id} - {status}")
        return True
    
    def get_inventory_history(self, asset_id: str = None) -> list:
        """Get inventory record history"""
        conn = sqlite3.connect(self.db_path)
        conn.row_factory = sqlite3.Row
        cursor = conn.cursor()
        
        if asset_id:
            cursor.execute('''
                SELECT * FROM inventory_records WHERE asset_id = ? ORDER BY check_date DESC
            ''', (asset_id,))
        else:
            cursor.execute('SELECT * FROM inventory_records ORDER BY check_date DESC')
        
        rows = cursor.fetchall()
        conn.close()
        return [dict(row) for row in rows]
    
    def export_to_csv(self, output_path: str) -> int:
        """Export all assets to CSV"""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        cursor.execute('SELECT * FROM assets ORDER BY id')
        rows = cursor.fetchall()
        conn.close()
        
        if not rows:
            print("[!] No assets to export")
            return 0
        
        headers = [desc[0] for desc in cursor.description] if rows else []
        with open(output_path, 'w', encoding='utf-8', newline='') as f:
            writer = csv.DictWriter(f, fieldnames=headers)
            writer.writeheader()
            for row in rows:
                writer.writerow(dict(zip(headers, row)))
        
        print(f"[+] Exported {len(rows)} assets to {output_path}")
        return len(rows)
    
    def import_from_csv(self, csv_path: str, update_existing: bool = False) -> int:
        """Import assets from CSV"""
        count = 0
        with open(csv_path, 'r', encoding='utf-8') as f:
            reader = csv.DictReader(f)
            for row in reader:
                row = {k: v for k, v in row.items() if v}  # Remove empty values
                if update_existing:
                    existing = self.get_asset(row.get('id'))
                    if existing:
                        self.update_asset(row['id'], row)
                        count += 1
                    else:
                        if self.add_asset(row):
                            count += 1
                else:
                    if self.add_asset(row):
                        count += 1
        
        print(f"[+] Imported {count} assets from {csv_path}")
        return count
    
    def get_statistics(self) -> dict:
        """Get inventory statistics"""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        cursor.execute('SELECT COUNT(*) as total FROM assets')
        total = cursor.fetchone()[0]
        
        cursor.execute("SELECT COUNT(*) as count FROM assets WHERE status != '正常'")
        abnormal = cursor.fetchone()[0]
        
        cursor.execute('''
            SELECT category, COUNT(*) as count FROM assets GROUP BY category
        ''')
        by_category = {row[0]: row[1] for row in cursor.fetchall()}
        
        cursor.execute('''
            SELECT location, COUNT(*) as count FROM assets GROUP BY location
        ''')
        by_location = {row[0]: row[1] for row in cursor.fetchall()}
        
        cursor.execute('''
            SELECT SUM(purchase_price) as total FROM assets WHERE purchase_price IS NOT NULL
        ''')
        total_value = cursor.fetchone()[0] or 0
        
        conn.close()
        
        return {
            'total_assets': total,
            'abnormal_count': abnormal,
            'by_category': by_category,
            'by_location': by_location,
            'total_value': total_value
        }

def demo():
    """Demo: Test asset database operations"""
    print("=== Asset Database Demo ===")
    db = AssetDatabase()
    
    # Add demo assets
    demo_assets = [
        {
            "id": "NB-2024-001",
            "name": "Dell Inspiron 15",
            "category": "資訊設備",
            "brand": "Dell",
            "model": "Inspiron 15",
            "serial_number": "DL20240001",
            "purchase_date": "2024-01-15",
            "purchase_price": 28000,
            "location": "圖書館2樓",
            "custodian": "王小明",
            "status": "正常"
        },
        {
            "id": "PR-2024-001",
            "name": "HP LaserJet Pro",
            "category": "週邊設備",
            "brand": "HP",
            "model": "LaserJet Pro",
            "serial_number": "HP20240001",
            "purchase_date": "2024-02-20",
            "purchase_price": 12000,
            "location": "辦公室1",
            "custodian": "陳大同",
            "status": "正常"
        },
        {
            "id": "AC-2023-001",
            "name": "大同窗型冷氣",
            "category": "家電",
            "brand": "大同",
            "model": "KC-252",
            "serial_number": "TATUNG2023001",
            "purchase_date": "2023-06-10",
            "purchase_price": 15000,
            "location": "校長室",
            "custodian": "李主任",
            "status": "正常"
        }
    ]
    
    print("\n--- Adding demo assets ---")
    for asset in demo_assets:
        db.add_asset(asset)
    
    print("\n--- Search results ---")
    results = db.search_assets(category="資訊設備")
    print(f"Found {len(results)} info equipment assets")
    for r in results:
        print(f"  {r['id']}: {r['name']} @ {r['location']}")
    
    print("\n--- Statistics ---")
    stats = db.get_statistics()
    print(f"Total assets: {stats['total_assets']}")
    print(f"By category: {stats['by_category']}")
    print(f"Total value: {stats['total_value']} NTD")

if __name__ == "__main__":
    demo()
