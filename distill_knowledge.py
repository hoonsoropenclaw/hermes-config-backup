import os
import sys
import json
import urllib.request
import logging

logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')

API_KEY_PATH = "/home/hoonsoropenclaw/.hermes/.minimax_api_key"
API_KEY = ""
try:
    with open(API_KEY_PATH, "r") as f:
        API_KEY = f.read().strip()
except Exception:
    pass

SKILLS_DIR = "/home/hoonsoropenclaw/.hermes/data_repo/skills"
CATALOG_PATH = os.path.join(SKILLS_DIR, "SKILL_CATALOG.md")

def distill_log(log_path):
    if not os.path.exists(log_path):
        logging.error(f"Log file {log_path} not found.")
        return
        
    with open(log_path, 'r', encoding='utf-8') as f:
        log_content = f.read()[-30000:] # Last 30k chars to capture the final working code and errors
        
    domains_str = ""
    try:
        with open("/home/hoonsoropenclaw/.hermes/learning_domains.txt", "r", encoding="utf-8") as f:
            domains_str = f.read()
    except Exception:
        domains_str = "未讀取到"
        
    url = "https://api.minimax.io/v1/text/chatcompletion_v2"
    headers = {
        'Authorization': f'Bearer {API_KEY}',
        'Content-Type': 'application/json'
    }
    
    prompt = (
        "You are an AI Architect. Your goal is to analyze the following execution log of an AI agent "
        "and extract reusable 'micro-skills' (模組化微技能) that the agent learned during this task.\n"
        "A micro-skill should be a specific, modular capability. Examples: 'telegram_bot_init' (how to start a TG bot), "
        "'fastapi_sqlite_crud' (how to do CRUD with FastAPI), 'github_trending_scraper' (how to parse HTML). "
        "DO NOT create monolithic skills like 'weather_bot_complete'. Break it down into reusable technical components.\n\n"
        "For each micro-skill, provide a Markdown content block that includes:\n"
        "1. The purpose of the skill.\n"
        "2. Key code snippets or patterns.\n"
        "3. Common errors encountered and how to avoid them.\n\n"
        "NEW RULE for Anti-Patterns:\n"
        "If you see a [FATAL ERROR] indicating a TIMEOUT or OS termination, you MUST carefully analyze the last few executed commands in the log. Deduce the TRUE cause of the hang (e.g., infinite loop, waiting for user input, incorrect blocking I/O, or runaway background process). Extract an anti-pattern micro-skill (e.g., 'anti_pattern_infinite_loop' or 'anti_pattern_blocking_io') documenting EXACTLY what caused the failure and how to fix it in the future.\n\n"
        "NEW RULE for Meta-Learning Domain Expansion:\n"
        f"The agent's current authorized learning domains are:\n{domains_str}\n"
        "If you detect that the skills learned in this log fall significantly OUTSIDE the authorized domains "
        "(e.g., Blockchain, Machine Learning tuning, Hardware I/O), you MUST formulate a proposal to expand the domains.\n\n"
        "Output your response strictly as a raw JSON object (NO markdown blocks, NO backticks) matching this schema:\n"
        "{\n"
        "  \"skills\": [\n"
        "    {\n"
        "      \"skill_name\": \"telegram_bot_init\",\n"
        "      \"summary\": \"使用 python-telegram-bot 建立基礎架構的樣板\",\n"
        "      \"markdown_content\": \"# Telegram Bot Init\\n\\n## 說明...\\n...\"\n"
        "    }\n"
        "  ],\n"
        "  \"domain_expansion_proposal\": \"(Optional) 如果發現新領域，寫下給總工程師的提議，例如：發現總工程師有區塊鏈開發需求，建議將『Web3 智能合約開發』加入背景學習領域。若無則留空或 null\"\n"
        "}\n\n"
        "Here is the log:\n"
        f"{log_content}"
    )
    
    payload = {
        "model": "MiniMax-Text-01",
        "messages": [
            {"role": "user", "content": prompt}
        ],
        "temperature": 0.1
    }
    
    try:
        req = urllib.request.Request(url, headers=headers, data=json.dumps(payload).encode('utf-8'), method='POST')
        with urllib.request.urlopen(req, timeout=120) as response:
            data = json.loads(response.read().decode())
            content = data['choices'][0]['message']['content'].strip()
            
            if content.startswith("```json"):
                content = content[7:]
            if content.startswith("```"):
                content = content[3:]
            if content.endswith("```"):
                content = content[:-3]
                
            data_obj = json.loads(content.strip())
            
            # Backwards compatibility if LLM still returns a list directly
            if isinstance(data_obj, list):
                skills = data_obj
                proposal = ""
            else:
                skills = data_obj.get("skills", [])
                proposal = data_obj.get("domain_expansion_proposal", "")
                
            if proposal and isinstance(proposal, str) and len(proposal) > 5:
                rq_path = "/home/hoonsoropenclaw/.hermes/review_queue.md"
                with open(rq_path, "a", encoding="utf-8") as rq:
                    rq.write(f"\n## 🌟 領域拓展提案\n- **提案內容**: {proposal}\n- **觸發任務**: 從最新日誌中自動分析得出\n")
                logging.info(f"Domain expansion proposal generated: {proposal}")
            
            os.makedirs(SKILLS_DIR, exist_ok=True)
            
            # Read existing catalog
            catalog_content = ""
            if os.path.exists(CATALOG_PATH):
                with open(CATALOG_PATH, 'r', encoding='utf-8') as f:
                    catalog_content = f.read()
            else:
                catalog_content = "# 學習微技能目錄 (SKILL CATALOG)\n此目錄為拉斐爾已掌握的微技能模組。在進行任務前，應先檢索此目錄尋找可重用的經驗。\n\n"
            
            # Save new skills and append to catalog
            for skill in skills:
                name = skill['skill_name']
                summary = skill['summary']
                md_content = skill['markdown_content']
                
                skill_path = os.path.join(SKILLS_DIR, f"{name}.md")
                with open(skill_path, 'w', encoding='utf-8') as f:
                    f.write(md_content)
                
                # Check if it's already in the catalog
                catalog_entry = f"- **{name}**: {summary}\n"
                if name not in catalog_content:
                    catalog_content += catalog_entry
                    logging.info(f"Added new skill {name} to catalog.")
                    
            with open(CATALOG_PATH, 'w', encoding='utf-8') as f:
                f.write(catalog_content)
                
            logging.info("Knowledge distillation complete.")
            
            # 閾值觸發整併邏輯
            COUNT_FILE = os.path.join(SKILLS_DIR, "unconsolidated_count.txt")
            count = len(skills) # Number of skills just added
            if os.path.exists(COUNT_FILE):
                try:
                    with open(COUNT_FILE, 'r') as f:
                        count += int(f.read().strip())
                except:
                    pass
                    
            if count >= 5:
                logging.info(f"Unconsolidated skills reached threshold ({count}). Triggering consolidation...")
                os.system("python3 /home/hoonsoropenclaw/.hermes/consolidate_skills.py")
                with open(COUNT_FILE, 'w') as f:
                    f.write("0")
            else:
                logging.info(f"Current unconsolidated skills count: {count}. (Threshold is 5)")
                with open(COUNT_FILE, 'w') as f:
                    f.write(str(count))
            
    except Exception as e:
        logging.error(f"Failed to distill knowledge: {e}")

if __name__ == "__main__":
    if len(sys.argv) < 2:
        logging.error("Usage: python distill_knowledge.py <path_to_local_log>")
        sys.exit(1)
    
    distill_log(sys.argv[1])
