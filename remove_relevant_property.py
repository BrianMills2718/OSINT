#!/usr/bin/env python3
"""Remove 'relevant' property from all integration schemas."""

import re

files = [
    "integrations/government/dvids_integration.py",
    "integrations/government/clearancejobs_integration.py",
    "integrations/government/federal_register.py",
    "integrations/government/sam_integration.py",
    "integrations/government/fbi_vault.py",
    "integrations/government/usajobs_integration.py",
    "integrations/social/brave_search_integration.py",
    "integrations/social/twitter_integration.py",
]

for filepath in files:
    with open(filepath, 'r') as f:
        content = f.read()

    # Remove the "relevant" property definition (including multiline)
    # Pattern: "relevant": {\n    "type": "boolean",\n    "description": "..."\n},
    content = re.sub(
        r'"relevant":\s*\{[^}]+\},\s*\n',
        '',
        content,
        flags=re.MULTILINE
    )

    with open(filepath, 'w') as f:
        f.write(content)

    print(f"✓ {filepath}")

print("\n✓ Removed 'relevant' property from all schemas")
