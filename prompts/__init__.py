"""
Jinja2 prompt templates for LLM prompts.

This package contains all Jinja2 templates for LLM prompts used throughout
the SigInt Platform. Templates eliminate f-string/JSON template conflicts
by using Jinja2's {{ }} syntax for variables while allowing literal { }
for JSON examples.

Directory Structure:
    prompts/
    ├── __init__.py (this file)
    ├── deep_research/        # Deep research prompts
    │   ├── task_decomposition.j2
    │   ├── source_selection.j2
    │   ├── entity_extraction.j2
    │   ├── relevance_evaluation.j2
    │   ├── query_reformulation.j2
    │   ├── query_reformulation_simple.j2
    │   └── report_synthesis.j2
    └── integrations/         # Integration-specific prompts
        ├── government/       # Government database prompts
        │   ├── usajobs_query_generation.j2
        │   ├── sam_query_generation.j2
        │   ├── clearancejobs_query_generation.j2
        │   ├── dvids_query_generation.j2
        │   ├── federal_register_query_generation.j2
        │   └── fbi_vault_query_generation.j2
        └── social/           # Social media prompts
            ├── reddit_query_generation.j2
            ├── twitter_query_generation.j2
            ├── discord_query_generation.j2
            └── brave_search_query_generation.j2

Usage:
    from core.prompt_loader import render_prompt

    # Render a template with variables
    prompt = render_prompt(
        "deep_research/query_reformulation.j2",
        research_question=question,
        original_query=query,
        results_count=count
    )

Template Syntax:
    - Variables: {{ variable_name }}
    - JSON examples: Use literal { and } (no escaping needed)
    - Comments: {# This is a comment #}
    - Control flow: {% if condition %} ... {% endif %}
    - Loops: {% for item in items %} ... {% endfor %}

Key Benefits:
    - NO {{ }} escaping needed for JSON examples
    - Prompts version-controlled separately from code
    - Templates are testable and parseable
    - Clean separation of concerns
    - Easy to edit without touching Python code

Reference:
    - docs/FSTRING_JSON_METHODOLOGY.md - Problem analysis and solutions
    - docs/JINJA2_MIGRATION_INVESTIGATION.md - Migration details
    - core/prompt_loader.py - Template loading infrastructure

Example Template (prompts/deep_research/query_reformulation.j2):
    ```jinja2
    Your task: Reformulate the research query to improve results.

    Research question: {{ research_question }}
    Original query: {{ original_query }}
    Results found: {{ results_count }}

    Return JSON with:
    {
      "query": "new query text",
      "param_adjustments": {
        "reddit": {"time_filter": "year"},
        "usajobs": {"keywords": "broad keyword"}
      }
    }
    ```

Note: This __init__.py is intentionally minimal. Templates are loaded
dynamically by prompt_loader.py using Jinja2's FileSystemLoader.
"""

# Version of prompt template system
__version__ = "1.0.0"

# Export nothing - all access through prompt_loader.py
__all__ = []
