# MemPalace Fallback Search Pattern

## Overview

When session_search (first-layer memory) fails to find relevant content, MemPalace provides a semantic fallback layer using a palace/room/drawer structure with ChromaDB vector storage.

## Architecture

```
┌─────────────────────────────────────┐
│  User Query                         │
└──────────────┬──────────────────────┘
               │
               ▼
┌─────────────────────────────────────┐
│  Layer 1: session_search            │
│  - FTS5 SQLite over message store  │
│  - Fast, keyword + semantic         │
└──────────────┬──────────────────────┘
               │ (no match / low score)
               ▼
┌─────────────────────────────────────┐
│  Layer 2: mempalace__mempalace_search│
│  - ChromaDB vector store            │
│  - Palace/room/drawer structure    │
│  - IF→THEN patterns, daily diaries  │
└─────────────────────────────────────┘
```

## MemPalace Path

- Config: `~/.mempalace/palace/mempalace.yaml`
- Database: `~/.mempalace/palace/chroma.sqlite3`

## MCP Server Configuration

**Config location**: `~/.hermes/config.yaml` under `mcp_servers`

```yaml
mcp_servers:
  mempalace:
    command: python3
    args:
      - -m
      - mempalace.mcp_server
    enabled: true
```

⚠️ **Critical**: `args` must be a YAML list, NOT a string. If you set it via `hermes config set` with a JSON-like string value, Pydantic will reject it with:

```
1 validation error for StdioServerParameters
args
  Input should be a valid list [type=list_type, input_value='["-m", "mempalace.mcp_server"]', input_type=str]
```

**If args gets stored as a string**, fix it by editing `~/.hermes/config.yaml` directly with Python YAML:

```python
import yaml
with open('~/.hermes/config.yaml', 'r') as f:
    cfg = yaml.safe_load(f)
cfg['mcp_servers']['mempalace']['args'] = ['-m', 'mempalace.mcp_server']
with open('~/.hermes/config.yaml', 'w') as f:
    yaml.dump(cfg, f, default_flow_style=False, allow_unicode=True, sort_keys=False)
```

**Why `hermes config set` fails**: It serializes list values as JSON strings instead of YAML lists. Always verify in config.yaml after setting.

## Trigger Conditions

- session_search returns empty results
- session_search returns low-confidence results (score below threshold)
- User explicitly mentions "we discussed this before" but session_search misses it
- Cross-domain knowledge requires broader semantic matching

## MCP Tool

```
mempalace__mempalace_search(query: string, limit?: int, max_distance?: number) → semantic search results
```

Available MemPalace tools (29 total):
- `mempalace_search` — Semantic search (primary fallback tool)
- `mempalace_kg_query` — Knowledge graph entity relationships
- `mempalace_diary_read` — Read diary entries in AAAK format
- `mempalace_graph_stats` — Palace graph statistics
- `mempalace_status` — Total drawers, wings, rooms count

## MemPalace vs session_search

| Aspect | session_search | MemPalace |
|--------|----------------|-----------|
| Storage | SQLite FTS5 | ChromaDB |
| Scope | Conversation history | Long-term knowledge |
| Structure | Flat messages | Palace/room/drawer hierarchy |
| Content | Sessions, decisions | IF→THEN patterns, diaries, domain knowledge |
| Speed | Faster | Slower (vector ops) |

## Usage Pattern

```python
# Step 1: Try session_search first
results = session_search(query="...", limit=3)
if results and results[0].score > 0.7:
    return results  # Use session_search results
else:
    # Step 2: Fallback to MemPalace
    results = mempalace__mempalace_search(query=query, limit=5)
    return results
```

## Verification Commands

```bash
# Test MCP connection
hermes mcp test mempalace

# List MCP servers
hermes mcp list

# List available tools
hermes tools list | grep mempalace
```

## Hermes Configuration Files (Two-Layer Memory)

The two-layer search pattern is documented in three core files:
- `~/.hermes/memories/HEARTBEAT.md` — Phase 3 search rules
- `~/.hermes/memories/SOUL.md` — Session continuation Step 3
- `~/.hermes/memories/MEMORY.md` — MemPalace system info

## OpenClaw (Raphael) Reference

Raphael uses the same pattern documented in:
- `~/.openclaw/workspace/raphael-status-site/tabs/mdfiles.html`
- Two-layer search: memory_search → mempalace_search