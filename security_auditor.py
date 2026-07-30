import os
import glob
import re
import urllib.request
import json
import logging

logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')

HERMES_DIR = "/home/hoonsoropenclaw/.hermes"
BACKUP_SCRIPT = os.path.join(HERMES_DIR, "scripts", "hermes-backup-v4.sh")
API_KEY_PATH = os.path.join(HERMES_DIR, ".minimax_api_key")
REVIEW_QUEUE = os.path.join(HERMES_DIR, "review_queue.md")

def get_api_key():
    try:
        with open(API_KEY_PATH, "r") as f:
            return f.read().strip()
    except Exception:
        return None

def check_for_secrets(file_content, api_key):
    url = "https://api.minimax.io/v1/text/chatcompletion_v2"
    headers = {
        'Authorization': f'Bearer {api_key}',
        'Content-Type': 'application/json'
    }
    
    prompt = (
        "You are a DevSecOps Security Auditor. Analyze the following python/bash code.\n"
        "Check if there are any hardcoded API keys, passwords, or secrets (e.g. 'sk-...', 'AIzaSy...').\n"
        "Reply EXACTLY with 'LEAK_DETECTED' if you find any hardcoded secrets.\n"
        "Reply EXACTLY with 'CLEAN' if the code is safe and does not contain hardcoded secrets.\n\n"
        "Code:\n"
        f"{file_content}"
    )
    
    payload = {
        "model": "MiniMax-Text-01",
        "messages": [{"role": "user", "content": prompt}],
        "temperature": 0.1
    }
    
    try:
        req = urllib.request.Request(url, headers=headers, data=json.dumps(payload).encode('utf-8'), method='POST')
        with urllib.request.urlopen(req, timeout=30) as response:
            data = json.loads(response.read().decode())
            content = data['choices'][0]['message']['content'].strip()
            return "LEAK_DETECTED" in content
    except Exception as e:
        logging.error(f"API Error: {e}")
        # If API fails, default to conservative (safe, block it just in case)
        return True

def main():
    api_key = get_api_key()
    if not api_key:
        logging.error("No API key found for security auditor.")
        return

    # 1. Parse current ROOT_SINGLE_FILES
    if not os.path.exists(BACKUP_SCRIPT):
        logging.error(f"Backup script not found: {BACKUP_SCRIPT}")
        return

    with open(BACKUP_SCRIPT, "r", encoding="utf-8") as f:
        backup_content = f.read()

    # Regex to find the block
    match = re.search(r'declare -a ROOT_SINGLE_FILES=\(\s*(.*?)\s*\)', backup_content, re.DOTALL)
    if not match:
        logging.error("Could not find ROOT_SINGLE_FILES array in backup script.")
        return

    array_content = match.group(1)
    # Extract filenames
    current_files = re.findall(r'"([^"]+)"', array_content)
    
    # 2. Scan for .py and .sh files in HERMES_DIR
    py_files = glob.glob(os.path.join(HERMES_DIR, "*.py"))
    sh_files = glob.glob(os.path.join(HERMES_DIR, "*.sh"))
    all_files = py_files + sh_files
    
    new_files_added = []
    
    for filepath in all_files:
        filename = os.path.basename(filepath)
        # Skip if already in backup list or is a hidden file
        if filename in current_files or filename.startswith('.'):
            continue
            
        logging.info(f"New unbacked-up file detected: {filename}")
        
        # Read content
        with open(filepath, "r", encoding="utf-8") as f:
            file_content = f.read()
            
        # 3. Security Scan
        is_leaking = check_for_secrets(file_content, api_key)
        
        if is_leaking:
            logging.warning(f"🚨 [SECURITY ALERT] Secrets found in {filename}!")
            with open(REVIEW_QUEUE, "a", encoding="utf-8") as rq:
                rq.write(f"\n## 🚨 [SECURITY ALERT] 機密外洩風險！\n"
                         f"- **檔案**: `{filename}`\n"
                         f"- **攔截原因**: 自動資安掃描發現此檔案內含有硬編碼的金鑰或密碼。\n"
                         f"- **防護動作**: 已阻擋該檔案進入備份白名單。請總工程師或架構師修改程式碼，將金鑰改為讀取隱藏檔後，系統才會放行備份。\n")
        else:
            logging.info(f"✅ {filename} is clean. Adding to backup whitelist.")
            new_files_added.append(filename)
            
    # 4. Auto-update Backup Script
    if new_files_added:
        # We need to inject these new files into the array block
        new_lines = "\n".join([f'    "{f}"' for f in new_files_added])
        
        # Replace the original array_content with the appended one
        replacement = array_content
        if not replacement.endswith("\n"):
            replacement += "\n"
        replacement += new_lines + "\n"
        
        new_backup_content = backup_content.replace(array_content, replacement)
        with open(BACKUP_SCRIPT, "w", encoding="utf-8") as f:
            f.write(new_backup_content)
        logging.info(f"Successfully added {len(new_files_added)} files to hermes-backup-v4.sh.")

if __name__ == "__main__":
    main()
