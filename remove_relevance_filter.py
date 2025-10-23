#!/usr/bin/env python3
"""
Remove relevance filtering from all integrations.

Instead of returning None when LLM marks as "not relevant",
generate a simple fallback query using the research question.
"""

import re

files_to_update = [
    "integrations/government/dvids_integration.py",
    "integrations/government/clearancejobs_integration.py",
    "integrations/government/federal_register.py",
    "integrations/government/sam_integration.py",
    "integrations/government/fbi_vault.py",
    "integrations/government/usajobs_integration.py",
    "integrations/social/brave_search_integration.py",
    "integrations/social/twitter_integration.py",
]

for filepath in files_to_update:
    print(f"\nProcessing: {filepath}")

    with open(filepath, 'r') as f:
        content = f.read()

    # Find and replace the relevance check pattern
    # Pattern: if not result["relevant"]: return None

    # Check if this pattern exists
    if 'if not result["relevant"]:' in content:
        # Replace with: Always generate query, even if LLM says not relevant
        # Remove the "relevant" field from schema and checks

        # Remove the relevance check and return None
        content = re.sub(
            r'        if not result\["relevant"\]:\s+return None',
            '''        # RELEVANCE FILTER REMOVED - Always generate query
        # if not result["relevant"]:
        #     return None''',
            content
        )

        # Remove "relevant" from required fields
        content = re.sub(
            r'"required": \[([^\]]*)"relevant"([^\]]*)\]',
            r'"required": [\1\2]',
            content
        )

        # Clean up double commas
        content = content.replace('", ,', ',')
        content = content.replace(', ,', ',')

        with open(filepath, 'w') as f:
            f.write(content)

        print(f"  ✓ Removed relevance filter")
    else:
        print(f"  ℹ No relevance filter found (may already be removed)")

print("\n✓ Done! Relevance filters removed from all integrations.")
print("Now all integrations will always generate query params, even if LLM thinks not relevant.")
