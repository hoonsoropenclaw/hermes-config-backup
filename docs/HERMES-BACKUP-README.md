# 赫米斯備份（Google Drive 版本）

> 這是 hoonsoropenclaw 的赫米斯全狀態加密備份所在。
> 異機還原用，**完整**還原需要 hermes-agent 源碼、state.db、.env 等敏感/大型資料。
> 公開版（不含敏感）在 https://github.com/hoonsoropenclaw/hermes-config-backup

## 📁 資料夾結構

每個備份時間戳一個資料夾，命名格式 `hermes_backup_<YYYYMMDD_HHMMSS>_full/`：

```
hermes-backup/                              ← 你在這層
├── HERMES-BACKUP-README.md                 ← 這份說明（異機還原 SOP 入口）
├── hermes-restore.sh                       ← 一鍵還原腳本
└── hermes_backup_20260606_153736_full/     ← 單次備份的時間戳資料夾
    ├── hermes_backup_20260606_153736_full.tar.gz  ← 主備份（rclone crypt 加密）
    ├── RESTORE.md                          ← 解 tar 後的詳細 SOP
    └── restore_hermes.sh/                  ← 解 tar 後的還原腳本
```

## 🚀 快速還原（推薦）

**最快的方式**（假設你已有 rclone config 跟 gh CLI）：

```bash
# 1. 從 Drive 下載最新版 hermes-restore.sh
#    在瀏覽器打開這個資料夾，下載 hermes-restore.sh
chmod +x hermes-restore.sh

# 2. 編輯頂部設定
nano hermes-restore.sh
# 改這 3 個：
#   HERMES_HOME="/path/to/your/.hermes"   # 新主機的 hermes home
#   RCLONE_CONFIG="/path/to/your/rclone.conf"
#   GITHUB_USERNAME="hoonsoropenclaw"

# 3. 跑
./hermes-restore.sh
```

腳本會自動：
1. 找到 Drive 上**最新**的 `_full` 備份
2. 用 rclone crypt 自動解密
3. 解 tar.gz
4. 跑**互動式選擇**：要還原 .env / state.db / 源碼 / 哪些技能
5. 顯示驗證清單

## 📋 完整異機還原 SOP

詳見每個備份資料夾內的 `RESTORE.md`（解 tar 後可看到），或 https://github.com/hoonsoropenclaw/hermes-config-backup/blob/main/docs/RESTORE.md

## 🔐 安全注意事項

- **這層 Drive 資料夾是加密的**（rclone crypt 透明加密），直接看檔名是亂碼
- 但本檔（`HERMES-BACKUP-README.md`）跟 `hermes-restore.sh` 是**明文**的（讓沒 rclone config 的人也能看到說明）
- 真正的敏感資料（.env、state.db、源碼、token）都在加密 tar.gz 內
- **請勿把本資料夾設為公開分享** —— 雖然內容是加密的，但避免不必要風險

## 📞 還原有問題時

1. 看 `hermes-restore.sh` 印出的錯誤訊息
2. 看每個備份資料夾內的 `RESTORE.md` 詳細步驟
3. 看 trial-and-error skill（隨備份還原）：`/references/by-category/hermes-config-tuning.md`

---

最後更新：2026-06-06
備份頻率：每天 03:00（自動 cron）
