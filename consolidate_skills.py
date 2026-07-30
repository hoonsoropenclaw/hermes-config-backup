import os
import sys
import json
import urllib.request
import logging
import glob

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

def consolidate_skills():
    if not os.path.exists(CATALOG_PATH):
        logging.info("SKILL_CATALOG.md not found. Nothing to consolidate.")
        return
        
    with open(CATALOG_PATH, 'r', encoding='utf-8') as f:
        catalog_content = f.read()
        
    url = "https://api.minimax.io/v1/text/chatcompletion_v2"
    headers = {
        'Authorization': f'Bearer {API_KEY}',
        'Content-Type': 'application/json'
    }
    
    prompt = (
        "You are an AI Architect analyzing a catalog of micro-skills for an AI agent.\n"
        "Your goal is to identify skills that are highly overlapping, duplicated, or just differently named versions of the same concept.\n\n"
        "Here is the catalog:\n"
        f"{catalog_content}\n\n"
        "Output ONLY a raw JSON array of merge actions (NO markdown formatting, NO backticks). "
        "Each action must specify the source skills to merge, the new merged name, and a new summary.\n"
        "If NO merges are needed, output an empty array `[]`.\n"
        "[\n"
        "  {\n"
        "    \"source_skills\": [\"fastapi_sqlite_crud\", \"fastapi_db_setup\"],\n"
        "    \"merged_name\": \"fastapi_database_architecture\",\n"
        "    \"merged_summary\": \"FastAPI 資料庫整合樣板與 CRUD 操作 (包含 SQLite)\"\n"
        "  }\n"
        "]\n"
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
                
            merge_actions = json.loads(content.strip())
            
            if not merge_actions:
                logging.info("No skills to consolidate.")
                return
                
            for action in merge_actions:
                sources = action['source_skills']
                merged_name = action['merged_name']
                merged_summary = action['merged_summary']
                
                logging.info(f"Merging {sources} into {merged_name}...")
                
                combined_content = ""
                for src in sources:
                    src_path = os.path.join(SKILLS_DIR, f"{src}.md")
                    if os.path.exists(src_path):
                        with open(src_path, 'r', encoding='utf-8') as f:
                            combined_content += f"\n\n=== {src} ===\n" + f.read()
                            
                if not combined_content:
                    continue
                    
                # Second LLM call to rewrite the content
                rewrite_prompt = (
                    f"Combine and rewrite the following multiple overlapping micro-skills into a single, cohesive micro-skill document.\n"
                    f"Target Skill Name: {merged_name}\n"
                    f"Target Summary: {merged_summary}\n\n"
                    f"Retain ALL technical details, code snippets, and error-prevention lessons from all sources. "
                    f"Output ONLY the raw markdown content for the new file (NO markdown code block wrappers around the whole response).\n\n"
                    f"Source contents:\n{combined_content}"
                )
                
                rewrite_payload = {
                    "model": "MiniMax-Text-01",
                    "messages": [{"role": "user", "content": rewrite_prompt}],
                    "temperature": 0.1
                }
                
                rewrite_req = urllib.request.Request(url, headers=headers, data=json.dumps(rewrite_payload).encode('utf-8'), method='POST')
                with urllib.request.urlopen(rewrite_req, timeout=120) as rewrite_response:
                    rewrite_data = json.loads(rewrite_response.read().decode())
                    new_md_content = rewrite_data['choices'][0]['message']['content'].strip()
                    
                    if new_md_content.startswith("```markdown"):
                        new_md_content = new_md_content[11:]
                    if new_md_content.endswith("```"):
                        new_md_content = new_md_content[:-3]
                        
                    # Save new skill
                    new_path = os.path.join(SKILLS_DIR, f"{merged_name}.md")
                    with open(new_path, 'w', encoding='utf-8') as f:
                        f.write(new_md_content.strip())
                        
                    # Delete old skills
                    for src in sources:
                        src_path = os.path.join(SKILLS_DIR, f"{src}.md")
                        if os.path.exists(src_path):
                            os.remove(src_path)
                            
            # Finally, rebuild the catalog
            logging.info("Rebuilding SKILL_CATALOG.md...")
            new_catalog = "# 學習微技能目錄 (SKILL CATALOG)\n此目錄為拉斐爾已掌握的微技能模組。在進行任務前，應先檢索此目錄尋找可重用的經驗。\n\n"
            for md_file in glob.glob(os.path.join(SKILLS_DIR, "*.md")):
                if os.path.basename(md_file) == "SKILL_CATALOG.md":
                    continue
                # Just extract name from filename for now. We can also parse the first line or ask LLM to regenerate catalog.
                # Actually, simpler to just use a quick LLM call to regenerate catalog or just list filenames.
                # Let's ask the LLM to generate the final catalog.
            
            rebuild_prompt = (
                f"You are given a list of micro-skill filenames present in the system.\n"
                f"Please generate the content for SKILL_CATALOG.md. For each file, infer a short 1-line summary based on its name.\n"
                f"Output ONLY the raw markdown content.\n\n"
                f"Filenames: {[os.path.basename(f).replace('.md', '') for f in glob.glob(os.path.join(SKILLS_DIR, '*.md')) if os.path.basename(f) != 'SKILL_CATALOG.md']}"
            )
            rebuild_payload = {
                    "model": "MiniMax-Text-01",
                    "messages": [{"role": "user", "content": rebuild_prompt}],
                    "temperature": 0.1
            }
            rebuild_req = urllib.request.Request(url, headers=headers, data=json.dumps(rebuild_payload).encode('utf-8'), method='POST')
            with urllib.request.urlopen(rebuild_req, timeout=120) as rebuild_response:
                rebuild_data = json.loads(rebuild_response.read().decode())
                final_catalog = rebuild_data['choices'][0]['message']['content'].strip()
                if final_catalog.startswith("```markdown"):
                    final_catalog = final_catalog[11:]
                if final_catalog.endswith("```"):
                    final_catalog = final_catalog[:-3]
                    
                with open(CATALOG_PATH, 'w', encoding='utf-8') as f:
                    f.write("# 學習微技能目錄 (SKILL CATALOG)\n此目錄為拉斐爾已掌握的微技能模組。在進行任務前，應先檢索此目錄尋找可重用的經驗。\n\n" + final_catalog.strip())
            
            logging.info("Consolidation complete.")
            
    except Exception as e:
        logging.error(f"Failed to consolidate knowledge: {e}")

if __name__ == "__main__":
    consolidate_skills()
