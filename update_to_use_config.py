#!/usr/bin/env python3
"""
Script to update all integrations and executors to use config.

This updates:
- Model names to use config.get_model()
- Timeouts to use config.get_timeout() or config.get_database_config()
- Default values to use config properties
"""

import re
from pathlib import Path

def update_integration(filepath: Path, db_id: str):
    """Update a database integration file to use config."""

    with open(filepath, 'r') as f:
        content = f.read()

    # Add config import after other imports
    if 'from config_loader import config' not in content:
        # Find the last import statement before the class definition
        import_pattern = r'(from api_request_tracker import log_request\n)'
        content = re.sub(
            import_pattern,
            r'\1from config_loader import config\n',
            content
        )

    # Replace hardcoded model with config
    content = re.sub(
        r'model="gpt-5-mini"',
        r'model=config.get_model("query_generation")',
        content
    )

    # Replace timeout in execute_search with config
    content = re.sub(
        r'timeout=\d+\)',
        f'timeout=config.get_database_config("{db_id}")["timeout"])',
        content
    )

    with open(filepath, 'w') as f:
        f.write(content)

    print(f"✓ Updated {filepath.name}")

def update_executor(filepath: Path):
    """Update an executor file to use config."""

    with open(filepath, 'r') as f:
        content = f.read()

    # Add config import
    if 'from config_loader import config' not in content:
        import_pattern = r'(from api_request_tracker import log_request\n)'
        if import_pattern not in content:
            import_pattern = r'(from database_integration_base import.*\n)'
        content = re.sub(
            import_pattern,
            r'\1from config_loader import config\n',
            content
        )

    # Replace default parameters in __init__
    content = re.sub(
        r'def __init__\(self, max_concurrent=\d+, max_refinements=\d+\):',
        r'def __init__(self, max_concurrent=None, max_refinements=None):',
        content
    )

    # Add config fallbacks in __init__ body
    if 'self.max_concurrent = max_concurrent or config.max_concurrent' not in content:
        # Find __init__ and add config usage
        content = re.sub(
            r'(def __init__.*\n.*""".*\n.*""")\n\s+super\(\).__init__\(max_concurrent\)',
            r'\1\n        max_concurrent = max_concurrent or config.max_concurrent\n        max_refinements = max_refinements or config.max_refinements\n        super().__init__(max_concurrent)',
            content,
            flags=re.DOTALL
        )

    # Replace hardcoded model with config
    content = re.sub(
        r'model="gpt-5-mini"',
        r'model=config.get_model("refinement")',
        content
    )

    with open(filepath, 'w') as f:
        f.write(content)

    print(f"✓ Updated {filepath.name}")

def update_analyzer(filepath: Path, operation: str):
    """Update an analyzer file to use config."""

    with open(filepath, 'r') as f:
        content = f.read()

    # Add config import
    if 'from config_loader import config' not in content:
        import_pattern = r'(from api_request_tracker import log_request\n)'
        content = re.sub(
            import_pattern,
            r'\1from config_loader import config\n',
            content
        )

    # Replace default model parameter
    content = re.sub(
        r'def __init__\(self, llm_model="gpt-5-mini"',
        r'def __init__(self, llm_model=None',
        content
    )

    # Add config fallback for llm_model
    content = re.sub(
        r'(def __init__.*timeout_seconds.*\):.*\n.*""".*\n.*""")\n\s+self\.llm_model = llm_model',
        rf'\1\n        self.llm_model = llm_model or config.get_model("{operation}")',
        content,
        flags=re.DOTALL
    )

    # Replace timeout with config
    content = re.sub(
        r'timeout_seconds=\d+',
        r'timeout_seconds=None',
        content
    )

    content = re.sub(
        r'self\.timeout_seconds = timeout_seconds',
        r'self.timeout_seconds = timeout_seconds or config.get_timeout("code_execution")',
        content
    )

    with open(filepath, 'w') as f:
        f.write(content)

    print(f"✓ Updated {filepath.name}")

def main():
    print("Updating files to use configuration system...")
    print("=" * 60)

    base_dir = Path(__file__).parent

    # Update integrations
    print("\nUpdating integrations...")
    update_integration(base_dir / "integrations/sam_integration.py", "sam")
    update_integration(base_dir / "integrations/dvids_integration.py", "dvids")
    update_integration(base_dir / "integrations/usajobs_integration.py", "usajobs")
    update_integration(base_dir / "integrations/clearancejobs_integration.py", "clearancejobs")

    # Update executors
    print("\nUpdating executors...")
    update_executor(base_dir / "agentic_executor.py")
    update_executor(base_dir / "intelligent_executor.py")

    # Update analyzers
    print("\nUpdating analyzers...")
    update_analyzer(base_dir / "adaptive_analyzer.py", "code_generation")
    update_analyzer(base_dir / "result_analyzer.py", "analysis")

    print("\n" + "=" * 60)
    print("✓ All files updated successfully!")
    print("\nFiles now use:")
    print("  - config.get_model() for LLM models")
    print("  - config.get_timeout() for timeouts")
    print("  - config.max_concurrent, config.max_refinements for execution params")

if __name__ == "__main__":
    main()
