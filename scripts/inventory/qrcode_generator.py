#!/usr/bin/env python3
"""
QR Code Generator for Equipment Inventory
學校設備盤點 QR Code 產生器
"""

import qrcode
import csv
import os
from datetime import datetime
from pathlib import Path

def generate_qrcode(data: str, output_path: str, box_size: int = 10, border: int = 4):
    """Generate QR code image from data string"""
    qr = qrcode.QRCode(
        version=1,
        error_correction=qrcode.constants.ERROR_CORRECT_M,
        box_size=box_size,
        border=border,
    )
    qr.add_data(data)
    qr.make(fit=True)
    
    img = qr.make_image(fill_color="black", back_color="white")
    img.save(output_path)
    print(f"[+] QR Code saved: {output_path}")

def generate_asset_qr(asset_id: str, name: str, category: str, location: str = "") -> str:
    """Generate QR code data string for an asset"""
    # QR code contains JSON data that can be scanned and parsed
    asset_data = {
        "id": asset_id,
        "name": name,
        "category": category,
        "location": location,
        "timestamp": datetime.now().isoformat()
    }
    import json
    return json.dumps(asset_data)

def batch_generate_from_csv(csv_path: str, output_dir: str, prefix: str = "asset"):
    """Batch generate QR codes from CSV file"""
    os.makedirs(output_dir, exist_ok=True)
    count = 0
    
    with open(csv_path, 'r', encoding='utf-8') as f:
        reader = csv.DictReader(f)
        for row in reader:
            asset_id = row.get('id', f'{prefix}_{count+1:04d}')
            name = row.get('name', '')
            category = row.get('category', '')
            location = row.get('location', '')
            
            qr_data = generate_asset_qr(asset_id, name, category, location)
            output_path = os.path.join(output_dir, f'{asset_id}.png')
            
            generate_qrcode(qr_data, output_path)
            count += 1
    
    print(f"[+] Batch generated {count} QR codes to {output_dir}")

def generate_printable_sheet(assets: list, output_path: str, cols: int = 4):
    """Generate a printable QR code sheet for batch printing"""
    from PIL import Image, ImageDraw
    
    if not assets:
        print("[!] No assets to print")
        return
    
    rows = (len(assets) + cols - 1) // cols
    cell_size = 300
    padding = 20
    
    sheet_width = cols * (cell_size + padding) + padding
    sheet_height = rows * (cell_size + padding + 40) + padding  # 40 for label
    
    sheet = Image.new('RGB', (sheet_width, sheet_height), 'white')
    draw = ImageDraw.Draw(sheet)
    
    for idx, asset in enumerate(assets):
        col = idx % cols
        row = idx // cols
        
        x = padding + col * (cell_size + padding)
        y = padding + row * (cell_size + padding + 40)
        
        # Draw QR code
        qr_data = generate_asset_qr(
            asset.get('id', f'asset_{idx}'),
            asset.get('name', ''),
            asset.get('category', ''),
            asset.get('location', '')
        )
        
        qr = qrcode.QRCode(version=1, error_correction=qrcode.constants.ERROR_CORRECT_M)
        qr.add_data(qr_data)
        qr.make(fit=True)
        img = qr.make_image(fill_color="black", back_color="white")
        
        # Resize and paste
        img = img.resize((cell_size, cell_size))
        sheet.paste(img, (x, y))
        
        # Draw label
        draw.text((x, y + cell_size + 5), asset.get('id', '')[:20], fill='black')
        draw.text((x, y + cell_size + 20), asset.get('name', '')[:20], fill='black')
    
    # Save sheet
    sheet.save(output_path)
    print(f"[+] Printable sheet saved: {output_path}")

def demo():
    """Demo: Generate sample QR codes"""
    print("=== QR Code Generator Demo ===")
    
    # Demo 1: Single QR code
    demo_asset = {
        "id": "NB-2024-001",
        "name": "ASUS筆電",
        "category": "資訊設備",
        "location": "圖書館2樓"
    }
    
    import json
    qr_data = json.dumps(demo_asset)
    
    output_dir = "/home/hoonsoropenclaw/.hermes/scripts/inventory"
    os.makedirs(output_dir, exist_ok=True)
    
    output_path = os.path.join(output_dir, "demo_asset.png")
    generate_qrcode(qr_data, output_path)
    print(f"[*] Demo asset QR code: {output_path}")
    
    # Demo 2: Multiple assets in a sheet
    demo_assets = [
        {"id": "NB-001", "name": "Dell筆電", "category": "電腦", "location": "辦公室"},
        {"id": "PR-001", "name": "HP印表機", "category": "週邊", "location": "辦公室"},
        {"id": "PR-002", "name": "Epson投影機", "category": "週邊", "location": "會議室"},
        {"id": "AC-001", "name": "大同冷氣", "category": "家電", "location": "校長室"},
        {"id": "DS-001", "name": "Sony攝影機", "category": "數位設備", "location": "器材室"},
        {"id": "DS-002", "name": "Canon相機", "category": "數位設備", "location": "器材室"},
        {"id": "FB-001", "name": "木桌", "category": "傢俱", "location": "教室"},
        {"id": "FB-002", "name": "鐵椅", "category": "傢俱", "location": "教室"},
    ]
    
    sheet_path = os.path.join(output_dir, "demo_sheet.png")
    generate_printable_sheet(demo_assets, sheet_path)
    print(f"[*] Demo printable sheet: {sheet_path}")

if __name__ == "__main__":
    demo()
