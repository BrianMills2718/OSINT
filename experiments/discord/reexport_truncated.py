#!/usr/bin/env python3
"""
Re-export specific Discord channels that had truncated/corrupt JSON files.
"""

import json
import subprocess
import time
from datetime import datetime
from pathlib import Path

DCE_CLI = Path("../../archive/reference/dce-cli/DiscordChatExporter.Cli")
EXPORTS_DIR = Path("../../data/exports")
LOGS_DIR = Path("../../data/logs")
CONFIG_FILE = Path("discord_servers.json")


def load_token() -> str:
    """Load Discord token from config file."""
    if not CONFIG_FILE.exists():
        raise FileNotFoundError(f"Config file not found: {CONFIG_FILE}")
    with open(CONFIG_FILE) as f:
        config = json.load(f)
    return config.get("token", "")

# Channels to re-export with their date ranges
# Format: (channel_id, after_date, before_date) - dates are None for full export
CHANNELS_TO_EXPORT = [
    # Bellingcat - announcements (full export, no date range)
    ("709768274031935560", None, None),

    # Project Owl - Middle East - palm-tree-oasis (4 date ranges)
    ("749424816255402055", "2025-08-10", "2025-08-17"),
    ("749424816255402055", "2025-09-21", "2025-09-28"),
    ("749424816255402055", "2025-09-28", "2025-10-05"),
    ("749424816255402055", "2025-10-05", "2025-10-12"),

    # Project Owl - Welcome Room - introductions
    ("839604984923422760", "2025-08-03", "2025-08-10"),

    # Project Owl - Europe/Russia - russia
    ("1023896418173341706", "2025-11-05", "2025-11-06"),

    # Project Owl - Europe/Russia - eurobog
    ("746747727160803418", "2025-11-13", "2025-11-14"),
]

# Note: The Americas channels (the-swamp, bubba-swamp, loud-volume-swamp, open-for-business-swamp)
# all had channel ID 1418332901220679720 which looks suspicious. These might need investigation.
# Adding them anyway:
AMERICAS_CHANNELS = [
    # Americas - the-swamp (3 date ranges)
    ("1418332901220679720", "2025-09-28", "2025-10-05"),
    ("1418332901220679720", "2025-10-05", "2025-10-12"),
    ("1418332901220679720", "2025-10-12", "2025-10-19"),

    # Americas - loud-volume-swamp
    ("1418332901220679720", "2025-11-04", "2025-11-05"),

    # Americas - open-for-business-swamp
    ("1418332901220679720", "2025-11-12", "2025-11-13"),

    # Americas - bubba-swamp
    ("1418332901220679720", "2025-11-14", "2025-11-15"),
]

def validate_json_file(filepath: Path) -> tuple[bool, str]:
    """Validate that a JSON file is complete and parseable."""
    try:
        with open(filepath, 'r', encoding='utf-8') as f:
            content = f.read()

        stripped = content.rstrip()
        if not stripped.endswith('}'):
            return (False, "File appears truncated - doesn't end with '}'")

        json.loads(content)
        return (True, "")
    except json.JSONDecodeError as e:
        return (False, f"JSON parse error: {e}")
    except Exception as e:
        return (False, f"Error reading file: {e}")


def export_channel(channel_id: str, token: str, after_date: str = None, before_date: str = None) -> bool:
    """Export a single channel, optionally with date range."""
    EXPORTS_DIR.mkdir(parents=True, exist_ok=True)
    LOGS_DIR.mkdir(parents=True, exist_ok=True)

    cmd = [
        str(DCE_CLI),
        "export",
        "-t", token,
        "-c", channel_id,
        "-f", "Json",
        "-o", str(EXPORTS_DIR) + "/"
    ]

    if after_date:
        cmd.extend(["--after", after_date])
    if before_date:
        cmd.extend(["--before", before_date])

    date_range = f"{after_date} to {before_date}" if after_date else "full export"
    print(f"\nExporting channel {channel_id} ({date_range})...")

    export_start_time = time.time()
    log_file = LOGS_DIR / "reexport_truncated.log"

    try:
        with open(log_file, 'a') as log:
            log.write(f"\n{'='*80}\n")
            log.write(f"Export started: {datetime.now()}\n")
            log.write(f"Channel: {channel_id}, Range: {date_range}\n")
            log.write(f"{'='*80}\n\n")

            result = subprocess.run(
                cmd,
                stdout=log,
                stderr=subprocess.STDOUT,
                timeout=3600
            )

            if result.returncode == 0:
                # Find and validate newly created files
                new_files = []
                for json_file in EXPORTS_DIR.glob("**/*.json"):
                    if json_file.stat().st_mtime > export_start_time:
                        is_valid, error = validate_json_file(json_file)
                        if is_valid:
                            new_files.append(json_file)
                            print(f"  ✓ Valid: {json_file.name}")
                        else:
                            print(f"  ✗ Invalid: {json_file.name} - {error}")
                            json_file.unlink()
                            log.write(f"Deleted invalid file: {json_file.name}\n")
                            return False

                log.write(f"✓ Export completed, {len(new_files)} valid file(s)\n")
                return True
            else:
                log.write(f"✗ Export failed with code {result.returncode}\n")
                return False

    except subprocess.TimeoutExpired:
        print(f"  ✗ Export timed out")
        return False
    except Exception as e:
        print(f"  ✗ Export failed: {e}")
        return False


def main():
    print("Re-exporting truncated Discord channels...")
    print("=" * 60)

    # Load token from config
    try:
        token = load_token()
        if not token:
            print("ERROR: No Discord token found in discord_servers.json")
            return
        print(f"Loaded token from config (ending in ...{token[-8:]})")
    except FileNotFoundError as e:
        print(f"ERROR: {e}")
        return

    successful = 0
    failed = 0

    # Export main channels
    for channel_id, after_date, before_date in CHANNELS_TO_EXPORT:
        if export_channel(channel_id, token, after_date, before_date):
            successful += 1
        else:
            failed += 1
        time.sleep(2)  # Brief pause between exports

    # Ask about Americas channels (since they have suspicious same channel ID)
    print("\n" + "=" * 60)
    print("Note: Americas channels all have the same channel ID (1418332901220679720)")
    print("This is unusual and may indicate they're threads or the original export had issues.")
    response = input("Attempt to export Americas channels? [y/N]: ")

    if response.lower() == 'y':
        for channel_id, after_date, before_date in AMERICAS_CHANNELS:
            if export_channel(channel_id, token, after_date, before_date):
                successful += 1
            else:
                failed += 1
            time.sleep(2)

    print("\n" + "=" * 60)
    print(f"Re-export complete: {successful} successful, {failed} failed")


if __name__ == "__main__":
    main()
