#!/usr/bin/env python3
"""
brand_tokens_transform.py
Converts W3C DTCG 2025.10 brand_tokens.json → CSS custom properties + Sass vars + JS module.

Usage:
    python3 brand_tokens_transform.py [--output ./dist]
"""

import json
import sys
import os
from pathlib import Path

SRC = Path(__file__).parent / "brand_tokens.json"
DIST = Path(__file__).parent / "dist"


def flatten_tokens(tokens, prefix=""):
    """Flatten nested $value references into dot-path keys."""
    result = {}
    for key, val in tokens.items():
        if isinstance(val, dict):
            if "$value" in val:
                result[prefix + key] = val["$value"]
            else:
                result.update(flatten_tokens(val, prefix + key + "."))
    return result


def resolve_refs(flat, key, seen=None):
    """Resolve {ref} references recursively."""
    if seen is None:
        seen = set()
    if key in seen:
        return key
    val = flat.get(key, key)
    if val.startswith("{") and val.endswith("}"):
        ref = val[1:-1]
        return resolve_refs(flat, ref, seen | {key})
    return val


def to_css(flat, semantic, component):
    """Generate CSS custom properties."""
    lines = [":root {"]
    for key in sorted(flat.keys()):
        val = resolve_refs(flat, key)
        lines.append(f"  --{key}: {val};")
    lines.append("}")
    return "\n".join(lines)


def to_js(flat, semantic, component):
    """Generate JS ES module with tokens."""
    entries = []
    for key in sorted(flat.keys()):
        val = resolve_refs(flat, key)
        safe = key.replace(".", "_")
        entries.append(f"  {safe}: \"{val}\"")
    return f"export const tokens = {{\n" + ",\n".join(entries) + "\n};\n"


def to_scss(flat):
    """Generate SCSS variables."""
    lines = []
    for key in sorted(flat.keys()):
        val = resolve_refs(flat, key)
        scss_key = f"${key.replace('.', '-')}"
        lines.append(f"{scss_key}: {val};")
    return "\n".join(lines)


def main():
    with open(SRC) as f:
        tokens = json.load(f)

    flat = flatten_tokens(tokens["$core"])
    semantic = flatten_tokens(tokens["$semantic"])
    component = flatten_tokens(tokens["$component"])

    all_tokens = {**flat, **semantic, **component}

    DIST.mkdir(exist_ok=True)

    css = to_css(flat, semantic, component)
    (DIST / "tokens.css").write_text(css)
    print(f"✅ tokens.css — {len(css.splitlines())} lines")

    js = to_js(flat, semantic, component)
    (DIST / "tokens.mjs").write_text(js)
    print(f"✅ tokens.mjs — {len(js.splitlines())} lines")

    scss = to_scss(all_tokens)
    (DIST / "_tokens.scss").write_text(scss)
    print(f"✅ _tokens.scss — {len(scss.splitlines())} lines")

    print(f"\n📁 Output: {DIST}")
    print(f"   Keys: {len(all_tokens)} tokens resolved")


if __name__ == "__main__":
    main()
