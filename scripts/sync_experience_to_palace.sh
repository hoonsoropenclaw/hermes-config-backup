#!/bin/bash
# ==============================================
# sync_experience_to_palace.sh - 將 EXPERIENCE.md 同步到 MemPalace
# 功能：將 If→Then 格式的經驗同步到 MemPalace 向量知識庫
#       每個模式作為一個 drawer 存入
# 使用：./sync_experience_to_palace.sh
# 建立：2026-05-25
# ==============================================

set -euo pipefail

EXPERIENCE_FILE="/home/hoonsoropenclaw/.hermes/evolution/EXPERIENCE.md"
PALACE_PATH="/home/hoonsoropenclaw/.mempalace/palace"

# 顏色輸出
RED='\033[0;31m'
GREEN='\033[0;32m'
NC='\033[0m'

log_info() { echo -e "${GREEN}[INFO]${NC} $1"; }
log_error() { echo -e "${RED}[ERROR]${NC} $1"; }

# 主程式（使用 Python 執行所有操作）
main() {
    log_info "開始同步 EXPERIENCE.md 到 MemPalace..."
    
    PYTHONWARNINGS=ignore python3 << 'PYTHON_EOF'
import re
from mempalace.backends.chroma import ChromaBackend

EXPERIENCE_FILE = "/home/hoonsoropenclaw/.hermes/evolution/EXPERIENCE.md"
PALACE_PATH = "/home/hoonsoropenclaw/.mempalace/palace"

with open(EXPERIENCE_FILE, "r") as f:
    content = f.read()

patterns = []
lines = content.split('\n')
current_pattern_name = ""
current_pattern_content = []
in_pattern = False
pattern_id = 1

# 正確的正規表示式：### 模式 N：內容（無空格）
for i, line in enumerate(lines):
    pattern_match = re.match(r'^### 模式 (\d+)：(.*)', line)
    if pattern_match:
        if current_pattern_name:
            patterns.append({
                "id": f"exp_pattern_{pattern_id:03d}",
                "name": current_pattern_name,
                "content": '\n'.join(current_pattern_content).strip()
            })
            pattern_id += 1
        current_pattern_name = pattern_match.group(2)
        current_pattern_content = [line]
        in_pattern = True
    elif in_pattern and line.startswith('## '):
        if current_pattern_name:
            patterns.append({
                "id": f"exp_pattern_{pattern_id:03d}",
                "name": current_pattern_name,
                "content": '\n'.join(current_pattern_content).strip()
            })
            pattern_id += 1
        current_pattern_name = ""
        current_pattern_content = []
        in_pattern = False
    elif in_pattern:
        current_pattern_content.append(line)

if current_pattern_name:
    patterns.append({
        "id": f"exp_pattern_{pattern_id:03d}",
        "name": current_pattern_name,
        "content": '\n'.join(current_pattern_content).strip()
    })

print(f"Found {len(patterns)} patterns to sync")

backend = ChromaBackend()
coll = backend.get_or_create_collection(PALACE_PATH, "drawers")

success_count = 0
error_count = 0

for p in patterns:
    try:
        result = coll.add(
            documents=p["content"],
            ids=p["id"],
            metadatas={
                "wing": "evolution",
                "room": "experience_patterns",
                "source": EXPERIENCE_FILE,
                "added_by": "sync_experience_to_palace.sh",
                "pattern_name": p["name"]
            }
        )
        print(f"  OK: {p['id']} - {p['name'][:50]}")
        success_count += 1
    except Exception as e:
        print(f"  ERROR: {p['id']} - {e}")
        error_count += 1

print(f"\nSync complete! Success: {success_count}, Errors: {error_count}")
PYTHON_EOF
}

main "$@"