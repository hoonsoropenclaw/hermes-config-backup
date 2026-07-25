#!/usr/bin/env python3
"""
MemPalace CLI - 命令列介面工具
用途：快速查詢、新增、管理 MemPalace 記憶
作者：拉斐爾無盡學習系統
"""

import json
import sys
import os
from datetime import datetime

# 嘗試載入 mcp (如果可用)
try:
    from mcp import Client
    MCP_AVAILABLE = True
except ImportError:
    MCP_AVAILABLE = False
    print("⚠️ MCP SDK not installed. Using curl-based CLI.", file=sys.stderr)


class MemPalaceCLI:
    """MemPalace 命令列工具"""
    
    def __init__(self, workspace_dir=None):
        self.workspace_dir = workspace_dir or os.path.expanduser("~/.hermes")
        self.host = os.environ.get("OPENCLAW_GATEWAY_HOST", "localhost")
        self.port = os.environ.get("OPENCLAW_GATEWAY_PORT", "18789")
        self.api_base = f"http://{self.host}:{self.port}/api"
        
    def _api_call(self, endpoint, method="GET", data=None):
        """發送 API 請求到 OpenClaw Gateway"""
        import urllib.request
        import urllib.error
        
        url = f"{self.api_base}/{endpoint}"
        headers = {"Content-Type": "application/json"}
        
        req = urllib.request.Request(url, headers=headers, method=method)
        if data:
            req.data = json.dumps(data).encode("utf-8")
        
        try:
            with urllib.request.urlopen(req, timeout=30) as resp:
                return json.loads(resp.read().decode("utf-8"))
        except urllib.error.HTTPError as e:
            return {"error": f"HTTP {e.code}", "detail": e.read().decode("utf-8")}
        except Exception as e:
            return {"error": str(e)}
    
    def status(self):
        """顯示 MemPalace 狀態"""
        result = self._api_call("mempalace/status")
        if "error" in result:
            print(f"❌ {result['error']}")
            return False
        print("🧠 MemPalace 狀態")
        print(f"   總 drawers: {result.get('total_drawers', 'N/A')}")
        print(f"   Wings: {result.get('wing_count', 'N/A')}")
        print(f"   Rooms: {result.get('room_count', 'N/A')}")
        return True
    
    def search(self, query, wing=None, max_distance=1.5, limit=10):
        """搜尋記憶"""
        params = f"?query={query}&max_distance={max_distance}&limit={limit}"
        if wing:
            params += f"&wing={wing}"
        result = self._api_call(f"mempalace/search{params}")
        
        if "error" in result:
            print(f"❌ {result['error']}")
            return []
        
        drawers = result.get("results", [])
        print(f"🔍 搜尋「{query}」找到 {len(drawers)} 筆記錄")
        for d in drawers:
            preview = d.get("text", "")[:100]
            wing = d.get("wing", "unknown")
            room = d.get("room", "unknown")
            sim = 1 - d.get("distance", 0.5)
            print(f"   [{wing}/{room}] ({sim:.2f}) {preview}...")
        return drawers
    
    def taxonomy(self):
        """顯示分類架構"""
        result = self._api_call("mempalace/taxonomy")
        if "error" in result:
            print(f"❌ {result['error']}")
            return
        
        taxonomy = result.get("taxonomy", {})
        print("📚 MemPalace 分類架構")
        for wing, rooms in taxonomy.items():
            room_count = len(rooms) if isinstance(rooms, dict) else 0
            total = sum(rooms.values()) if isinstance(rooms, dict) else rooms
            print(f"   {wing}: {total} drawers")
            if isinstance(rooms, dict):
                for room, count in rooms.items():
                    print(f"      └─ {room}: {count}")
    
    def kg_query(self, entity):
        """查詢知識圖譜"""
        result = self._api_call(f"mempalace/kg/query?entity={entity}")
        if "error" in result:
            print(f"❌ {result['error']}")
            return []
        
        facts = result.get("facts", [])
        print(f"🕸️ 知識圖譜：{entity}")
        for f in facts:
            pred = f.get("predicate", "?")
            obj = f.get("object", "?")
            current = "✓" if f.get("current") else "✗"
            print(f"   {f['subject']} --[{pred}]--> {obj} {current}")
        return facts
    
    def kg_add(self, subject, predicate, obj, valid_from=None):
        """新增知識圖譜事實"""
        data = {"subject": subject, "predicate": predicate, "object": obj}
        if valid_from:
            data["valid_from"] = valid_from
        result = self._api_call("mempalace/kg/add", method="POST", data=data)
        if result.get("success"):
            print(f"✅ 新增 KG: {subject} --[{predicate}]--> {obj}")
        else:
            print(f"❌ 新增失敗: {result}")
    
    def diary_read(self, agent_name, last_n=10):
        """讀取日記"""
        result = self._api_call(f"mempalace/diary/read?agent_name={agent_name}&last_n={last_n}")
        if "error" in result:
            print(f"❌ {result['error']}")
            return []
        
        entries = result.get("entries", [])
        print(f"📔 日記（{agent_name}）最近 {len(entries)} 筆")
        for e in entries:
            date = e.get("date", "?")
            content = e.get("content", "")[:80]
            print(f"   [{date}] {content}...")
        return entries
    
    def diary_write(self, agent_name, entry, topic="general"):
        """寫入日記"""
        data = {"agent_name": agent_name, "entry": entry, "topic": topic}
        result = self._api_call("mempalace/diary/write", method="POST", data=data)
        if result.get("success"):
            print(f"✅ 日記寫入成功")
        else:
            print(f"❌ 寫入失敗: {result}")
    
    def list_tunnels(self):
        """列出所有 tunnel"""
        result = self._api_call("mempalace/tunnels/list")
        if "error" in result:
            print(f"❌ {result['error']}")
            return []
        
        print("🌉 MemPalace Tunnels")
        tunnels = result if isinstance(result, list) else result.get("tunnels", [])
        for t in tunnels:
            room = t.get("room", "?")
            wings = t.get("wings", [])
            count = t.get("count", 0)
            print(f"   {room} → {', '.join(wings)} ({count})")
        return tunnels
    
    def traverse(self, start_room, max_hops=2):
        """遍歷房間連接"""
        result = self._api_call(f"mempalace/traverse?start_room={start_room}&max_hops={max_hops}")
        if "error" in result:
            print(f"❌ {result['error']}")
            return []
        
        print(f"🗺️ 遍歷 {start_room}")
        rooms = result if isinstance(result, list) else result.get("rooms", [result])
        for r in rooms:
            hop = r.get("hop", 0)
            room = r.get("room", "?")
            wings = r.get("wings", [])
            prefix = "  " * hop
            print(f"   {prefix}└─ [{hop}] {room} → {', '.join(wings)}")
        return rooms


def main():
    if len(sys.argv) < 2:
        print("""
🧠 MemPalace CLI - 拉斐爾記憶系統命令列工具

用法：
    python3 mempalace_cli.py status                    # 顯示狀態
    python3 mempalace_cli.py search <query>           # 搜尋記憶
    python3 mempalace_cli.py taxonomy                 # 顯示分類
    python3 mempalace_cli.py kg <entity>              # 查詢知識圖譜
    python3 mempalace_cli.py kg-add <sub> <pred> <obj> # 新增KG事實
    python3 mempalace_cli.py diary <agent> [N]         # 讀取日記
    python3 mempalace_cli.py diary-write <agent> <msg> # 寫入日記
    python3 mempalace_cli.py tunnels                   # 列出tunnels
    python3 mempalace_cli.py traverse <room> [hops]   # 遍歷房間
        """)
        sys.exit(1)
    
    cli = MemPalaceCLI()
    cmd = sys.argv[1]
    
    if cmd == "status":
        cli.status()
    elif cmd == "search":
        query = sys.argv[2] if len(sys.argv) > 2 else ""
        wing = sys.argv[3] if len(sys.argv) > 3 else None
        if not query:
            print("❌ 需要搜尋關鍵字")
            sys.exit(1)
        cli.search(query, wing)
    elif cmd == "taxonomy":
        cli.taxonomy()
    elif cmd == "kg":
        entity = sys.argv[2] if len(sys.argv) > 2 else "all"
        if entity == "all":
            cli._api_call("mempalace/kg/timeline")
        else:
            cli.kg_query(entity)
    elif cmd == "kg-add":
        if len(sys.argv) < 5:
            print("❌ 需要三個參數：subject predicate object")
            sys.exit(1)
        cli.kg_add(sys.argv[2], sys.argv[3], sys.argv[4])
    elif cmd == "diary":
        agent = sys.argv[2] if len(sys.argv) > 2 else "raphael"
        n = int(sys.argv[3]) if len(sys.argv) > 3 else 10
        cli.diary_read(agent, n)
    elif cmd == "diary-write":
        if len(sys.argv) < 4:
            print("❌ 需要 agent_name 和 entry 內容")
            sys.exit(1)
        cli.diary_write(sys.argv[2], sys.argv[3])
    elif cmd == "tunnels":
        cli.list_tunnels()
    elif cmd == "traverse":
        room = sys.argv[2] if len(sys.argv) > 2 else "diary"
        hops = int(sys.argv[3]) if len(sys.argv) > 3 else 2
        cli.traverse(room, hops)
    else:
        print(f"❌ 未知指令：{cmd}")
        sys.exit(1)


if __name__ == "__main__":
    main()
