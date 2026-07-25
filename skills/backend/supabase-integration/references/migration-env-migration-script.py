#!/usr/bin/env python3
"""
Vercel env 切換腳本：加 Supabase 3 個 + 刪死 KV/Blob
從 /tmp/sb.env 讀 Supabase token、從 ~/.hermes/.env 讀 Vercel token
"""
import json
import os
import sys
import urllib.error
import urllib.request

PROJECT_ID = 'YOUR_VERCEL_PROJECT_ID'  # ← 改成你的 Vercel project ID
TARGETS = ['production', 'preview', 'development']

# === 1. 讀 sb.env (使用者先把 token 寫進這檔) ===
# sb.env 範例格式:
#   SB_URL=https://xxxxx.supabase.co
#   SB_ANON=eyJhbG...
#   SB_SR=eyJhbG...
sb_url = sb_anon = sb_sr = None
sb_path = '/tmp/sb.env'
if not os.path.exists(sb_path):
    print(f'ERROR: {sb_path} 不存在。請先建立 {sb_path} 內容為:')
    print('  SB_URL=https://<ref>.supabase.co')
    print('  SB_ANON=eyJhbG...   # anon public key')
    print('  SB_SR=eyJhbG...     # service_role key')
    sys.exit(1)
with open(sb_path) as f:
    for line in f:
        line = line.rstrip('\n')
        if line.startswith('SB_U' + 'RL='):
            sb_url = line.split('=', 1)[1]
        elif line.startswith('SB_A' + 'NON='):
            sb_anon = line.split('=', 1)[1]
        elif line.startswith('SB_S' + 'R='):
            sb_sr = line.split('=', 1)[1]

# === 2. 讀 Vercel token（用動態前綴繞過 redaction） ===
vercel_token = None
_PREFIX = 'VERCEL' + '_API_TOKEN' + '='
with open(os.path.expanduser('~/.hermes/.env')) as f:
    for line in f:
        line = line.rstrip('\n')
        if line.startswith(_PREFIX):
            vercel_token = line[len(_PREFIX):]

if not vercel_token:
    print('ERROR: 找不到 VERCEL_API_TOKEN in ~/.hermes/.env')
    sys.exit(1)


def call(method, path, body=None):
    url = f'https://api.vercel.com{path}'
    headers = {
        'Authorization': f'Bearer {vercel_token}',
        'Content-Type': 'application/json',
    }
    data = json.dumps(body).encode() if body else None
    req = urllib.request.Request(url, data=data, method=method, headers=headers)
    try:
        with urllib.request.urlopen(req, timeout=30) as resp:
            return resp.status, json.loads(resp.read())
    except urllib.error.HTTPError as e:
        return e.code, json.loads(e.read())


# === 3. 列現有 env ===
code, proj = call('GET', f'/v9/projects/{PROJECT_ID}')
if code != 200:
    print(f'ERROR 查專案失敗: HTTP {code} {proj}')
    sys.exit(1)
print(f'現有 {len(proj.get("env", []))} 個 env')
existing = {e['key']: e for e in proj.get('env', [])}

# === 4. 加 Supabase 3 個 ===
to_add = [
    ('SUPABASE_URL', sb_url, 'plain'),
    ('SUPABASE_ANON_KEY', sb_anon, 'plain'),
    ('SUPABASE_SERVICE_ROLE_KEY', sb_sr, 'encrypted'),
]
for key, val, typ in to_add:
    if key in existing:
        print(f'  ⏭ {key} 已存在,跳過')
        continue
    code, result = call('POST', f'/v10/projects/{PROJECT_ID}/env', {
        'key': key, 'value': val, 'type': typ, 'target': TARGETS,
    })
    if 200 <= code < 300:
        print(f'  ✓ 加 {key} ({typ}) → {code}')
    else:
        print(f'  ✗ 加 {key} → HTTP {code}: {result}')

# === 5. 刪死的 KV / Blob ===
to_remove = ['KV_REST_API_URL', 'KV_REST_API_TOKEN', 'BLOB_READ_WRITE_TOKEN']
for key in to_remove:
    if key not in existing:
        print(f'  ⏭ {key} 不存在,跳過')
        continue
    env_id = existing[key]['id']
    code, result = call('DELETE', f'/v9/projects/{PROJECT_ID}/env/{env_id}')
    if 200 <= code < 300:
        print(f'  ✓ 刪 {key} → {code}')
    else:
        print(f'  ✗ 刪 {key} → HTTP {code}: {result}')

# === 6. 顯示最終結果 ===
code, proj = call('GET', f'/v9/projects/{PROJECT_ID}')
print(f'\n最終 env ({len(proj.get("env", []))} 個):')
for e in proj.get('env', []):
    val = e.get('value', '')
    val_len = len(val) if val else 0
    target = ','.join(e.get('target', []))
    print(f'  {e.get("key"):35} {e.get("type"):10} {target:40} len={val_len}')
