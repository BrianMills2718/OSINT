#!/usr/bin/env python3
"""
Experiment: Compare Discord ALL-match vs ANY-match without changing main code.

Loads a few Discord export JSON files and searches for a given list of
keywords using both matching modes, then prints counts and a couple of sample
hits for each mode.

Usage:
  python tests/experiments/test_discord_any_vs_all.py "sigint" "signals intelligence" "electronic surveillance"
"""

import sys
import json
from pathlib import Path
from typing import List, Dict

EXPORTS_DIR = Path("data/exports")


def load_messages() -> List[Dict]:
    messages = []
    if not EXPORTS_DIR.exists():
        print(f"Exports dir not found: {EXPORTS_DIR}")
        return messages

    files = list(EXPORTS_DIR.glob("*.json"))
    for fp in files:
        try:
            with open(fp, "r", encoding="utf-8") as f:
                data = json.load(f)
            guild = data.get("guild", {})
            channel = data.get("channel", {})
            for msg in data.get("messages", []):
                messages.append({
                    "content": (msg.get("content") or ""),
                    "timestamp": msg.get("timestamp", ""),
                    "author": msg.get("author", {}).get("name", "Unknown"),
                    "server": guild.get("name", "Unknown Server"),
                    "channel": channel.get("name", "Unknown Channel"),
                    "id": msg.get("id", ""),
                })
        except Exception as e:
            print(f"Warning: skipping {fp.name}: {e}")
            continue
    return messages


def search(messages: List[Dict], keywords: List[str], mode: str) -> List[Dict]:
    kws = [k.lower() for k in keywords]
    results = []
    for m in messages:
        content = m["content"].lower()
        if mode == "ALL":
            ok = all(kw in content for kw in kws)
        else:
            ok = any(kw in content for kw in kws)
        if ok:
            matched = [kw for kw in kws if kw in content]
            score = len(matched) / max(1, len(kws))
            results.append({**m, "matched": matched, "score": score})
    results.sort(key=lambda x: (x["score"], x["timestamp"]), reverse=True)
    return results


def main():
    if len(sys.argv) < 2:
        print("Provide 1+ keywords, e.g.: sigint \"signals intelligence\"")
        sys.exit(2)
    keywords = sys.argv[1:]
    print(f"Keywords: {keywords}")
    messages = load_messages()
    print(f"Loaded messages: {len(messages)}")

    all_hits = search(messages, keywords, mode="ALL")
    any_hits = search(messages, keywords, mode="ANY")

    print("\n=== ALL-match ===")
    print(f"Total: {len(all_hits)}")
    for m in all_hits[:3]:
        print(f"- {m['timestamp']} [{m['server']} / {m['channel']}] by {m['author']}: matched={m['matched']}")
        print(f"  {m['content'][:140].replace('\n',' ')}\n")

    print("=== ANY-match ===")
    print(f"Total: {len(any_hits)}")
    for m in any_hits[:3]:
        print(f"- {m['timestamp']} [{m['server']} / {m['channel']}] by {m['author']}: matched={m['matched']}")
        print(f"  {m['content'][:140].replace('\n',' ')}\n")


if __name__ == "__main__":
    main()

