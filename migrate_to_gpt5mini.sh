#!/bin/bash
# Script to migrate all code from gpt-4o-mini to gpt-5-mini

echo "Migrating codebase to gpt-5-mini..."
echo "=================================="

# Files to update
FILES=(
    "integrations/sam_integration.py"
    "integrations/dvids_integration.py"
    "integrations/usajobs_integration.py"
    "agentic_executor.py"
    "intelligent_executor.py"
    "adaptive_analyzer.py"
    "result_analyzer.py"
)

for file in "${FILES[@]}"; do
    if [ -f "$file" ]; then
        echo "Updating $file..."

        # Replace import litellm with from llm_utils import acompletion (if not already done)
        sed -i 's/^import litellm$/from llm_utils import acompletion/' "$file"

        # Replace gpt-4o-mini with gpt-5-mini
        sed -i 's/"gpt-4o-mini"/"gpt-5-mini"/g' "$file"
        sed -i "s/'gpt-4o-mini'/'gpt-5-mini'/g" "$file"

        # Replace litellm.acompletion with acompletion
        sed -i 's/litellm\.acompletion/acompletion/g' "$file"

        echo "  ✓ Updated $file"
    else
        echo "  ✗ File not found: $file"
    fi
done

echo ""
echo "=================================="
echo "Migration complete!"
echo ""
echo "Updated files:"
for file in "${FILES[@]}"; do
    if [ -f "$file" ]; then
        echo "  - $file"
    fi
done
