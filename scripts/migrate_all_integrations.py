#!/usr/bin/env python3
"""
Comprehensive migration script for all integration file prompts to Jinja2.

Migrates 9 integration files (reddit already migrated):
- usajobs_integration.py
- clearancejobs_integration.py
- dvids_integration.py
- federal_register.py
- sam_integration.py
- fbi_vault.py
- twitter_integration.py
- discord_integration.py
- brave_search_integration.py
"""
import re
import os

# Read all integration files
files_to_migrate = {
    "usajobs": "integrations/government/usajobs_integration.py",
    "clearancejobs": "integrations/government/clearancejobs_integration.py",
    "dvids": "integrations/government/dvids_integration.py",
    "federal_register": "integrations/government/federal_register.py",
    "sam": "integrations/government/sam_integration.py",
    "fbi_vault": "integrations/government/fbi_vault.py",
    "twitter": "integrations/social/twitter_integration.py",
    "discord": "integrations/social/discord_integration.py",
    "brave_search": "integrations/social/brave_search_integration.py"
}

# Track migrations
completed = []
errors = []

for integration_name, filepath in files_to_migrate.items():
    try:
        with open(filepath, 'r') as f:
            content = f.read()

        # Check if already has render_prompt import
        has_import = "from core.prompt_loader import render_prompt" in content

        # Add import if missing
        if not has_import:
            # Find the last import from core/llm
            import_pattern = r'(from (llm_utils|core\.database_integration_base) import [^\n]+\n)'
            match = re.search(import_pattern, content)
            if match:
                insert_pos = match.end()
                content = content[:insert_pos] + "from core.prompt_loader import render_prompt\n" + content[insert_pos:]
            else:
                print(f"⚠️  {integration_name}: Could not find import location")
                errors.append(f"{integration_name}: No import location found")
                continue

        # Find the f-string prompt (starts with 'prompt = f"""' and ends with '"""')
        prompt_pattern = r'prompt = f"""(.+?)"""'
        match = re.search(prompt_pattern, content, re.DOTALL)

        if not match:
            print(f"⚠️  {integration_name}: No f-string prompt found")
            errors.append(f"{integration_name}: No prompt found")
            continue

        prompt_content = match.group(1)

        # Extract variables from the prompt (look for {variable_name})
        var_pattern = r'\{([a-zA-Z_][a-zA-Z0-9_]*)\}'
        variables = list(set(re.findall(var_pattern, prompt_content)))

        # Create Jinja2 template content (replace {var} with {{ var }})
        template_content = re.sub(r'\{([a-zA-Z_][a-zA-Z0-9_]*)\}', r'{{ \1 }}', prompt_content)

        # Remove escaped JSON braces ({{ becomes {, }} becomes })
        template_content = template_content.replace('{{ {', '{')
        template_content = template_content.replace('} }}', '}')

        # Write template file
        template_path = f"prompts/integrations/{integration_name}_query_generation.j2"
        os.makedirs(os.path.dirname(template_path), exist_ok=True)
        with open(template_path, 'w') as f:
            f.write(template_content)

        # Generate render_prompt() call
        var_params = ",\n            ".join([f"{var}={var}" for var in sorted(variables)])
        new_prompt_call = f'prompt = render_prompt(\n            "integrations/{integration_name}_query_generation.j2",\n            {var_params}\n        )'

        # Replace old prompt with new one
        old_prompt = match.group(0)
        content = content.replace(old_prompt, new_prompt_call)

        # Write updated Python file
        with open(filepath, 'w') as f:
            f.write(content)

        completed.append(integration_name)
        print(f"✅ {integration_name}: Migrated (vars: {', '.join(sorted(variables))})")

    except Exception as e:
        print(f"❌ {integration_name}: {str(e)}")
        errors.append(f"{integration_name}: {str(e)}")

print(f"\n{'='*60}")
print(f"✅ Completed: {len(completed)}/9")
print(f"❌ Errors: {len(errors)}/9")
if errors:
    print("\nErrors:")
    for err in errors:
        print(f"  - {err}")
