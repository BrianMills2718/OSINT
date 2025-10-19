#!/usr/bin/env python3
"""
Discord Server Scraping Manager

Manages multiple Discord servers, tracks scrape history,
and automates daily incremental updates.
"""

import json
import subprocess
import sys
from datetime import datetime, timedelta
from pathlib import Path
from typing import Optional


CONFIG_FILE = Path("discord_servers.json")
DCE_CLI = Path("dce-cli/DiscordChatExporter.Cli")
EXPORTS_DIR = Path("exports")
STRIPPED_DIR = Path("exports_stripped")


def load_config():
    """Load server configuration."""
    if not CONFIG_FILE.exists():
        return {"servers": [], "token": None}

    with open(CONFIG_FILE, 'r') as f:
        return json.load(f)


def save_config(config):
    """Save server configuration."""
    with open(CONFIG_FILE, 'w') as f:
        json.dump(config, f, indent=2)


def add_server(server_id: str, name: str, channels: Optional[list] = None):
    """Add a new server to the config."""
    config = load_config()

    # Check if server already exists
    for server in config["servers"]:
        if server["id"] == server_id:
            print(f"Server {server_id} already exists. Use update-server to modify.")
            return

    config["servers"].append({
        "id": server_id,
        "name": name,
        "last_scraped": None,
        "channels": channels or [],  # Empty list = all channels
        "enabled": True,
        "notes": ""
    })

    save_config(config)
    print(f"Added server: {name} ({server_id})")


def list_servers():
    """List all configured servers."""
    config = load_config()

    if not config["servers"]:
        print("No servers configured.")
        return

    print(f"\n{'ID':<20} {'Name':<30} {'Last Scraped':<12} {'Enabled':<8}")
    print("-" * 80)

    for server in config["servers"]:
        enabled = "✓" if server["enabled"] else "✗"
        last = server["last_scraped"] or "Never"
        print(f"{server['id']:<20} {server['name']:<30} {last:<12} {enabled:<8}")


def export_server(server_id: str, token: str, since_date: Optional[str] = None):
    """Export a server's messages."""
    EXPORTS_DIR.mkdir(exist_ok=True)

    cmd = [
        str(DCE_CLI),
        "exportguild",
        "-t", token,
        "-g", server_id,
        "-f", "Json",
        "-o", str(EXPORTS_DIR) + "/"
    ]

    # Add incremental update flag
    if since_date:
        cmd.extend(["--after", since_date])

    print(f"Exporting server {server_id}...")
    if since_date:
        print(f"  Only messages after: {since_date}")

    try:
        result = subprocess.run(cmd, check=True, capture_output=True, text=True)
        print(f"✓ Export completed for server {server_id}")
        return True
    except subprocess.CalledProcessError as e:
        print(f"✗ Export failed for server {server_id}")
        print(f"  Error: {e.stderr}")
        return False


def strip_exports():
    """Strip bloat from all new exports."""
    from strip_discord_json import strip_discord_export

    STRIPPED_DIR.mkdir(exist_ok=True)

    # Find all non-stripped exports
    exports = list(EXPORTS_DIR.glob("*.json"))
    exports = [e for e in exports if "_stripped" not in e.name]

    print(f"\nStripping bloat from {len(exports)} file(s)...")

    for export_file in exports:
        stripped_file = STRIPPED_DIR / export_file.name.replace(".json", "_stripped.json")

        # Skip if already stripped and newer
        if stripped_file.exists() and stripped_file.stat().st_mtime > export_file.stat().st_mtime:
            continue

        try:
            strip_discord_export(str(export_file), str(stripped_file))
        except Exception as e:
            print(f"  ✗ Failed to strip {export_file.name}: {e}")


def run_daily_scrape():
    """Run daily scrape for all enabled servers."""
    config = load_config()

    if not config.get("token"):
        print("Error: No Discord token configured.")
        print("Set token with: discord_server_manager.py set-token YOUR_TOKEN")
        return

    token = config["token"]
    enabled_servers = [s for s in config["servers"] if s["enabled"]]

    if not enabled_servers:
        print("No enabled servers to scrape.")
        return

    print(f"Starting daily scrape for {len(enabled_servers)} server(s)...\n")

    today = datetime.now().strftime("%Y-%m-%d")

    for server in enabled_servers:
        # Calculate since date
        if server["last_scraped"]:
            since_date = server["last_scraped"]
        else:
            # First time - go back 30 days
            since_date = (datetime.now() - timedelta(days=30)).strftime("%Y-%m-%d")

        # Export server
        success = export_server(server["id"], token, since_date)

        if success:
            # Update last scraped date
            server["last_scraped"] = today

    # Save updated config
    save_config(config)

    # Strip all exports
    strip_exports()

    print(f"\n✓ Daily scrape completed at {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")


def set_token(token: str):
    """Set Discord token in config."""
    config = load_config()
    config["token"] = token
    save_config(config)
    print("Discord token updated.")


def main():
    if len(sys.argv) < 2:
        print("""
Discord Server Scraping Manager

Usage:
  discord_server_manager.py add-server <server_id> <name>
  discord_server_manager.py list
  discord_server_manager.py run-daily
  discord_server_manager.py set-token <token>
  discord_server_manager.py export <server_id>

Examples:
  # Add a server
  discord_server_manager.py add-server 989253812634157096 "Save America"

  # Set your Discord token
  discord_server_manager.py set-token "YOUR_TOKEN_HERE"

  # Run daily scrape (use in cron)
  discord_server_manager.py run-daily

  # List all servers
  discord_server_manager.py list
        """)
        sys.exit(1)

    command = sys.argv[1]

    if command == "add-server":
        if len(sys.argv) < 4:
            print("Usage: add-server <server_id> <name>")
            sys.exit(1)
        add_server(sys.argv[2], sys.argv[3])

    elif command == "list":
        list_servers()

    elif command == "run-daily":
        run_daily_scrape()

    elif command == "set-token":
        if len(sys.argv) < 3:
            print("Usage: set-token <token>")
            sys.exit(1)
        set_token(sys.argv[2])

    elif command == "export":
        if len(sys.argv) < 3:
            print("Usage: export <server_id>")
            sys.exit(1)
        config = load_config()
        if not config.get("token"):
            print("Error: Set token first with: set-token YOUR_TOKEN")
            sys.exit(1)
        export_server(sys.argv[2], config["token"])

    else:
        print(f"Unknown command: {command}")
        sys.exit(1)


if __name__ == "__main__":
    main()
