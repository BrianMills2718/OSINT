#!/usr/bin/env python3
"""
Strip bloat from Discord export JSON files.
Keeps only essential message data.
"""

import json
import sys
from pathlib import Path


def strip_message(msg):
    """Keep only essential message fields."""
    stripped = {
        "id": msg["id"],
        "timestamp": msg["timestamp"],
        "content": msg["content"],
        "author": {
            "id": msg["author"]["id"],
            "name": msg["author"]["name"],
            "nickname": msg["author"].get("nickname")
        }
    }

    # Add timestampEdited if it exists
    if msg.get("timestampEdited"):
        stripped["timestampEdited"] = msg["timestampEdited"]

    # Keep attachments (just essential fields)
    if msg.get("attachments"):
        stripped["attachments"] = [
            {
                "fileName": att["fileName"],
                "url": att["url"],
                "fileSizeBytes": att.get("fileSizeBytes")
            }
            for att in msg["attachments"]
        ]

    # Keep embeds (just title and description)
    if msg.get("embeds"):
        stripped["embeds"] = [
            {
                "title": emb.get("title"),
                "description": emb.get("description"),
                "url": emb.get("url")
            }
            for emb in msg["embeds"]
        ]

    # Keep reactions (just emoji and count, not full user lists)
    if msg.get("reactions"):
        stripped["reactions"] = [
            {
                "emoji": r["emoji"],
                "count": r["count"]
            }
            for r in msg["reactions"]
        ]

    # Keep reference for replies
    if msg.get("reference"):
        stripped["reference"] = {
            "messageId": msg["reference"].get("messageId"),
            "channelId": msg["reference"].get("channelId")
        }

    return stripped


def strip_discord_export(input_file, output_file=None):
    """Strip bloat from Discord export JSON."""
    input_path = Path(input_file)

    if output_file is None:
        output_file = input_path.parent / f"{input_path.stem}_stripped.json"

    print(f"Reading {input_file}...")
    with open(input_file, 'r', encoding='utf-8') as f:
        data = json.load(f)

    original_size = input_path.stat().st_size

    # Keep minimal metadata
    stripped_data = {
        "guild": {
            "id": data["guild"]["id"],
            "name": data["guild"]["name"]
        },
        "channel": {
            "id": data["channel"]["id"],
            "category": data["channel"].get("category"),
            "name": data["channel"]["name"]
        },
        "exportedAt": data["exportedAt"],
        "messages": [strip_message(msg) for msg in data["messages"]]
    }

    print(f"Stripped {len(data['messages'])} messages...")

    print(f"Writing to {output_file}...")
    with open(output_file, 'w', encoding='utf-8') as f:
        json.dump(stripped_data, f, indent=2, ensure_ascii=False)

    new_size = Path(output_file).stat().st_size
    reduction = (1 - new_size / original_size) * 100

    print(f"\nOriginal size: {original_size / 1024 / 1024:.2f} MB")
    print(f"Stripped size: {new_size / 1024 / 1024:.2f} MB")
    print(f"Reduction: {reduction:.1f}%")

    return output_file


if __name__ == "__main__":
    if len(sys.argv) < 2:
        print("Usage: python strip_discord_json.py <input_file> [output_file]")
        sys.exit(1)

    input_file = sys.argv[1]
    output_file = sys.argv[2] if len(sys.argv) > 2 else None

    strip_discord_export(input_file, output_file)
