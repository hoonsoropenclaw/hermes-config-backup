import os
import sys
import json
import urllib.request
import urllib.error
import subprocess
from datetime import datetime

API_KEY_PATH = "/home/hoonsoropenclaw/.hermes/.minimax_api_key"
API_KEY = ""
try:
    with open(API_KEY_PATH, "r") as f:
        API_KEY = f.read().strip()
except Exception:
    pass
API_URL = "https://api.minimax.io/v1/text/chatcompletion_v2"
LOG_FILE = "/home/hoonsoropenclaw/.hermes/learning_output.log"
OUTPUT_FILE = "/home/hoonsoropenclaw/.hermes/data_repo/data.json"

def read_latest_logs():
    if not os.path.exists(LOG_FILE):
        return "No logs found yet."
    with open(LOG_FILE, 'r', encoding='utf-8', errors='replace') as f:
        f.seek(0, os.SEEK_END)
        size = f.tell()
        f.seek(max(size - 50000, 0)) # Read more logs to catch concurrent runs
        return f.read()

def read_ongoing_tasks():
    try:
        result = subprocess.run("ps aux | grep '[h]ermes chat'", shell=True, capture_output=True, text=True)
        return result.stdout.strip()
    except Exception as e:
        print(f"Error reading ongoing tasks: {e}")
        return ""

def read_existing_mindmap_raw():
    if not os.path.exists(OUTPUT_FILE):
        return None
    try:
        with open(OUTPUT_FILE, 'r', encoding='utf-8') as f:
            data = json.load(f)
            return data.get("mindmap", {})
    except Exception as e:
        print(f"Error reading existing mindmap: {e}")
        return None

def merge_trees(old_node, new_node):
    if not old_node or not new_node:
        return
        
    # Strip bad URLs from LLM output before merging
    if "url" in new_node:
        url = new_node["url"]
        if ".md" in url or "/artifacts/" in url:
            del new_node["url"]
            
    if "url" in old_node and "url" not in new_node:
        # Also ensure old_node doesn't have bad URLs
        url = old_node["url"]
        if not (".md" in url or "/artifacts/" in url):
            new_node["url"] = url
            
    if "status" in old_node and "status" not in new_node:
        new_node["status"] = old_node["status"]
        
    old_children_list = old_node.get("children", [])
    new_children_list = new_node.get("children", [])
    
    new_children = {child.get("name", ""): child for child in new_children_list}
    
    for old_child in old_children_list:
        name = old_child.get("name", "")
        if name in new_children:
            merge_trees(old_child, new_children[name])
        else:
            new_children_list.append(old_child)
            
    if new_children_list:
        new_node["children"] = new_children_list

def extract_mindmap_json(log_text, ongoing_text, existing_raw):
    existing_json_text = json.dumps(existing_raw, ensure_ascii=False, indent=2) if existing_raw else None

    if existing_json_text:
        base_context = f"""【現有心智圖 JSON 結構】：
{existing_json_text}

【注意】：你不需要原封不動地輸出所有現有節點。你的任務是：
1. 分析日誌中是否有「新增」的實作專案、功能或節點。
2. 若有新增，請將其放在適當的層級中輸出。
3. 若某個現有節點的「狀態」或「URL」發生改變，也可以將它輸出以便更新。
4. 最終輸出的 JSON 會與現有結構進行「合併」(Merge)，因此你只需輸出包含更新或新增節點的骨架即可。若發現不符合規則的無效提案節點請「不要」輸出它。"""
    else:
        base_context = """【預設學習藍圖】（總工程師指定的高價值領域）：
1. 人工智慧代理 (AI Agents)
   - 多智能體協作 (Multi-Agent Sync)
   - MCP 工具整合 (MCP Integration)
   - 知識庫檢索 (RAG System)
2. 全端網頁開發 (Full-Stack Web)
   - React 狀態管理 (React State)
   - FastAPI 非同步處理 (FastAPI Async)
   - Serverless 部署架構 (Vercel Deploy)
3. 維運與自動化 (DevOps & Automation)
   - Linux 系統安全維護 (Linux Security)
   - 背景排程與監控 (Cron & Monitoring)
   - GitHub Actions 自動化 (CI/CD Pipeline)

【嚴格的輸出格式要求】：
你輸出的 JSON 必須嚴格遵從以下階層結構，外層必須包含 name 與 children 陣列，不能用物件的 key 來當作節點名稱：
{
  "name": "拉斐尔技能树 (Raphael Skills)",
  "children": [
    {
      "name": "人工智慧代理 (AI Agents)",
      "children": [
        { "name": "多智能體協作 (Multi-Agent Sync)", "status": "planned" }
      ]
    }
  ]
}
"""

    prompt = f"""
請閱讀以下的學習日誌，並更新心智圖狀態。
將結果轉換為嚴格的 JSON 格式。請只輸出 JSON，不要輸出 Markdown 標記（如 ```json）。

{base_context}

【更新規則 - 嚴格過濾與提取】：
1. 比對日誌，若某項預設技能已在日誌中被實作或學習，請將其保留，且不加狀態（預設即為已完成）。
2. 若某項預設技能尚未被學習，請務必保留它，並在該節點加上 `"status": "planned"`。
3. 【嚴格禁止】：日誌結尾通常會包含「🌟 領域拓展提案」、「後續優化建議」或類似的純理論討論對話。**絕對不要**將這些未實作的「提案」或「對話」加入心智圖中。心智圖只展示**實際已動手實作的專案**或**具體產出的程式碼模組**。
4. 若日誌中確實出現了不包含在現有結構中的**高價值且已實作**技能（例如真正寫出了一個爬蟲腳本），你可以將它做為新節點加入（狀態預設為已完成）。
5. 所有的 name 必須採用「中文 (English)」的雙語格式，例如 "自動化腳本 (Automation Script)"，命名必須簡潔有力，不要是一整句長長的描述。
6. 【重要】下方有「目前正在執行中的任務清單 (Ongoing Tasks)」。請仔細比對，如果某個技能正在該清單中被執行，請將該節點加上 `"status": "ongoing"`，這會優先於 planned 狀態。
7. 【提取連結 - 僅限實際成果】：若日誌中包含真實的 `[Project URL]`（例如 `https://...vercel.app` 部署網址），或是 GitHub 倉庫網址，請將其作為 `"url"` 屬性加入。**絕對不要**把單純的 Markdown 對話紀錄網址（例如 `learning_1785...md`）當成 URL 放入，我要看的是真實產出的網頁或程式碼。
8. 【結構穩定】：若有傳入現有結構，請保持層級結構不變，只做微調與新增，並清理掉原本不符合上述規則（如名字過長、其實只是理論提案、或是連到 .md 對話紀錄）的無效節點。

目前正在執行中的任務清單 (Ongoing Tasks)：
{ongoing_text}

學習日誌片段：
{log_text}
"""
    
    payload = {
        "model": "MiniMax-Text-01",
        "messages": [
            {"role": "system", "content": "You are a data extractor. Output ONLY valid JSON without markdown formatting."},
            {"role": "user", "content": prompt}
        ],
        "max_tokens": 8192
    }
    
    req = urllib.request.Request(API_URL, headers={
        'Authorization': f'Bearer {API_KEY}',
        'Content-Type': 'application/json'
    }, data=json.dumps(payload).encode('utf-8'))
    
    try:
        with urllib.request.urlopen(req, timeout=300) as response:
            result = json.loads(response.read().decode())
            content = result['choices'][0]['message']['content'].strip()
            if content.startswith("```json"):
                content = content.replace("```json\n", "")
            if content.endswith("```"):
                content = content[:-3]
            return json.loads(content)
    except Exception as e:
        print(f"Error calling LLM: {e}")
        return None

def main():
    print("Reading logs...")
    log_text = read_latest_logs()
    
    print("Reading ongoing tasks...")
    ongoing_text = read_ongoing_tasks()
    
    print("Reading existing mindmap...")
    existing_raw = read_existing_mindmap_raw()
    
    print("Extracting mindmap data...")
    mindmap_data = extract_mindmap_json(log_text, ongoing_text, existing_raw)
    
    if mindmap_data:
        if existing_raw:
            print("Merging existing properties (URLs) to prevent LLM amnesia...")
            merge_trees(existing_raw, mindmap_data)

        final_json = {
            "last_updated": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
            "mindmap": mindmap_data
        }
        with open(OUTPUT_FILE, "w", encoding='utf-8') as f:
            json.dump(final_json, f, ensure_ascii=False, indent=4)
        print(f"Successfully updated {OUTPUT_FILE}")
        
        # Git Commit and Push
        try:
            repo_dir = os.path.dirname(OUTPUT_FILE)
            subprocess.run(["git", "add", "."], cwd=repo_dir, check=True)
            subprocess.run(["git", "commit", "-m", f"Auto-update: {final_json['last_updated']}"], cwd=repo_dir, check=True)
            subprocess.run(["git", "push"], cwd=repo_dir, check=True)
            print("Successfully pushed to GitHub repository.")
        except Exception as e:
            print(f"Git push failed: {e}")
    else:
        print("Failed to extract valid JSON.")

if __name__ == "__main__":
    main()
