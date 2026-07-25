# GPG 加密相關踩雷

> 觸發:任何涉及 gpg / 對稱加密 / 非對稱加密 / 簽章 / 金鑰管理的任務
> 建立時間: 2026-06-05
> 條目數: 5

---

### gpg 預設產出檔案 mode 是 0644,加密後必 chmod 0600
**發現時間**: 2026-06-05
**觸發情境**: 跑 `gpg --symmetric` 加密 token,加密檔直接落 ~/.config/hermes/alt_gh_tokens/hoonsor.gpg,被發現是 0o664
**症狀**: `ls -la hoonsor.gpg` 顯示 `-rw-rw-r--` 而不是預期的 `-rw-------`
**根因**: GPG 預設遵循 umask,加密檔會保留當前 umask 設定(通常是 022 → 644),不會自動設 600
**解法**:
```bash
gpg --symmetric ... --output enc.gpg plain.txt
chmod 600 enc.gpg   # ← 必加這步
```
或用 wrapper:
```bash
gpg --symmetric ... && chmod 600 enc.gpg
```
**預防**: SOP `alt-token-secrets-layout` 已加 chmod 600 為必要步驟;新腳本寫死 chmod 後再繼續
**相關條目**: [[secrets-and-env#替代 token 加密佈局]]

---

### gpg 第一次跑會自動建 ~/.gnupg/pubring.kbx,是正常現象
**發現時間**: 2026-06-05
**觸發情境**: 第一次在這台機器跑 gpg 對稱加密
**症狀**: stderr 出現 `gpg: keybox '/home/<user>/.gnupg/pubring.kbx' created`
**根因**: GPG 對稱加密其實不需要 key,但 GPG 預設會建一個空的 keybox 給金鑰管理用(即使只用 --symmetric 也不會用到)
**解法**: 忽略這個訊息,繼續執行。exit code 0 就是成功
**預防**: SOP 的「已知陷阱」段落已記
**相關條目**: 無

---

### GPG 2.4+ AEAD 加密格式 header 是 0x8c 0x0d,不是舊的 0x85
**發現時間**: 2026-06-05
**觸發情境**: 寫腳本驗證加密檔是否成功,一開始用 `header.startswith(b"\x85\x01")` 判斷,結果誤判為失敗
**症狀**: 驗證腳本說「加密失敗」但解密其實正常
**根因**: GPG 2.2+ 改用 AEAD (Authenticated Encryption with Associated Data) 格式,新版 header 是 0x8c 0x0d;舊版是 0x85 開頭
**解法**:
```python
with open(path, "rb") as f:
    header = f.read(2)
is_gpg = header in (b"\x8c\x0d", b"\x85\x01")  # 兩種都視為合法 GPG 格式
```
或乾脆不解 header,直接呼叫 `gpg --decrypt` 看 exit code
**預防**: 驗證 GPG 加密檔用 `gpg --decrypt` round-trip,不要用 header byte 判斷
**相關條目**: 無

---

### gpg 對稱加密別加 --user 旗標,會卡住或失敗
**發現時間**: 2026-06-05
**觸發情境**: 想用 `gpg --symmetric --user hoonsor` 限制加密給某個 user
**症狀**: gpg 卡住、報錯「no such user ID」、或要互動式輸入解鎖金鑰
**根因**: `--user` 是用來指定**非對稱加密時**用哪把公鑰,對稱加密是 passphrase-based,這個旗標沒有意義,GPG 仍會去找該 user 的金鑰,找不到就卡住
**解法**: 對稱加密用 `--passphrase-file` 或 `--passphrase-fd`,**不要加 --user**:
```bash
gpg --batch --pinentry-mode loopback \
    --passphrase-file /path/to/passphrase \
    --symmetric \
    --cipher-algo AES256 \
    --output enc.gpg plain.txt
```
**預防**: SOP 明確標註對稱加密流程
**相關條目**: 無

---

### shred 對 SSD 效果有限,對家用備份意外已足夠
**發現時間**: 2026-06-05
**觸發情境**: 寫 SOP 用 `shred -u -z -n 3` 刪除明文 token
**症狀**: (預期內)SSD 控制器可能因 wear leveling 把 overwrite 寫到不同 block
**根因**: SSD 不像 HDD 會原地寫入,firmware 會把新資料寫到新 block,舊 block 之後才被回收
**解法**:
- 對**家用備份意外、誤傳到公開地方**這類威脅:`shred` 已經足夠,因為威脅發生在檔案系統層
- 對**磁碟被偷、進階威脅**:需要全碟加密(LUKS、BitLocker)從源頭防
**預防**: 機密檔案平常就該放在加密磁碟分割上,`shred` 只是輔助
**相關條目**: 無

---

## 跨分類關聯

- Python sandbox 跑 gpg 加密時,token 寫法要注意 → [[python-sandbox#Python sandbox 把 token 遮罩成 *** 導致字串截斷]]
- 加密佈局 SOP 見 skill `alt-token-secrets-layout`


---

## 額外條目（2026-06-06 從 MEMORY.md 移入）

### gpg 對稱加密不該加 `--user` 旗標
**症狀**: `gpg --symmetric --user alice file.txt` 會卡住、報 "no public key"
**根因**: `--user` 旗標會試圖找該 user 的金鑰,對稱加密根本不需要 user
**解法**: 對稱加密用 `--passphrase-file` 或 `--passphrase-fd`,**不要加 `--user`**
**預防**: 寫 gpg 對稱加密的腳本時,參數只放 `--symmetric --cipher-algo AES256 --s2k-mode 3 --s2k-count 65011712`

### GPG 2.4+ AEAD 加密格式 header 不是 `0x85`
**症狀**: 看加密檔開頭 byte 判斷格式,以為是 `0x85` 開頭,誤判成舊格式失敗
**事實**: GPG 2.4+ 預設 AEAD 加密格式 header 開頭是 `0x8c 0x0d`
**預防**: 不要用「header byte 是 0x85」當 AEAD 判斷條件
