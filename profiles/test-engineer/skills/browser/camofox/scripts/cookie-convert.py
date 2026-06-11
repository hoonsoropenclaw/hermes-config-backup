#!/usr/bin/env python3
"""
Camofox Cookie Format Converter

Converts Chrome Cookie-Editor JSON export to Camofox API format.
Camofox format: {"cookies": [{"name":..., "value":..., "domain":..., ...}]}

Usage:
    python3 scripts/cookie-convert.py cookies-export.json

Output: /tmp/cookies_for_camofox.json (Camofox-ready format)
"""

import json
import sys

def convert(cookies):
    converted = []
    for c in cookies:
        converted.append({
            "name": c.get("name", ""),
            "value": c.get("value", ""),
            "domain": c.get("domain", ""),
            "path": c.get("path", "/"),
            "expires": c.get("expirationDate", 0),
            "httpOnly": c.get("httpOnly", False),
            "secure": c.get("secure", False)
        })
    return {"cookies": converted}

if __name__ == "__main__":
    if len(sys.argv) < 2:
        print("Usage: cookie-convert.py <cookies-export.json>")
        sys.exit(1)

    input_file = sys.argv[1]
    with open(input_file, 'r') as f:
        cookies = json.load(f)

    # Handle wrapped export format
    if isinstance(cookies, dict) and "cookies" in cookies:
        cookies = cookies["cookies"]

    output = convert(cookies)
    output_path = '/tmp/cookies_for_camofox.json'
    with open(output_path, 'w') as f:
        json.dump(output, f, indent=2)

    print(f"Converted {len(output['cookies'])} cookies → {output_path}")