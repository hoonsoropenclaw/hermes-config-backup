# 設備盤點管理系統 - 安裝說明

## 依賴套件

```bash
# 使用 pipx 安裝隔離環境
pipx install qrcode pillow

# 或使用虛擬環境
python3 -m venv venv
source venv/bin/activate
pip install qrcode pillow
```

## 腳本清單

| 腳本 | 說明 |
|------|------|
| `qrcode_generator.py` | QR Code 產生器 |
| `asset_database.py` | 資產資料庫管理 |
| `inventory_checker.py` | 盤點記錄系統 |
| `anomaly_reporter.py` | 異常通報工具 |

## 使用方式

```bash
# 產生 QR Code
python3 qrcode_generator.py

# 測試資料庫
python3 asset_database.py

# 盤點檢查
python3 inventory_checker.py

# 異常報告
python3 anomaly_reporter.py
```
