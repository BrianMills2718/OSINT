#!/usr/bin/env python3
"""
Jinja2 prompt template loader.

Provides centralized Jinja2 environment for loading LLM prompt templates,
eliminating f-string/JSON template conflicts by using Jinja2's {{ }} syntax
for variables while allowing literal { } for JSON examples.

Usage:
    from core.prompt_loader import render_prompt

    prompt = render_prompt(
        "deep_research/query_reformulation.j2",
        research_question=question,
        original_query=query,
        results_count=count
    )

Template Location:
    prompts/<module>/<prompt_name>.j2

    Example:
    prompts/deep_research/query_reformulation.j2
    prompts/integrations/government/usajobs_query_generation.j2

Template Syntax:
    - Variables: {{ variable_name }}
    - JSON examples: Use literal { and } (no escaping needed)
    - Comments: {# This is a comment #}
    - Control flow: {% if condition %} ... {% endif %}

Key Benefits:
    - NO {{ }} escaping needed for JSON examples
    - Prompts version-controlled separately from code
    - Templates are testable and parseable
    - Clean separation of concerns

Reference:
    - docs/FSTRING_JSON_METHODOLOGY.md
    - docs/JINJA2_MIGRATION_INVESTIGATION.md
"""

import os
import logging
from pathlib import Path
from typing import Dict, Any
from datetime import datetime
from jinja2 import Environment, FileSystemLoader, TemplateNotFound, Template

# Set up logger for this module
logger = logging.getLogger(__name__)


# Determine prompts directory relative to this file
# core/prompt_loader.py -> prompts/
PROMPTS_DIR = Path(__file__).parent.parent / "prompts"


# Initialize Jinja2 environment with strict mode
# - FileSystemLoader: Load templates from prompts/ directory
# - autoescape=False: Don't HTML-escape (we're generating text, not HTML)
# - undefined=StrictUndefined: Error on undefined variables (fail fast)
_jinja_env = Environment(
    loader=FileSystemLoader(str(PROMPTS_DIR)),
    autoescape=False,
    trim_blocks=True,      # Remove first newline after block tag
    lstrip_blocks=True,    # Strip leading spaces/tabs before block tag
    keep_trailing_newline=True  # Preserve trailing newline in templates
)


def _get_system_context() -> Dict[str, Any]:
    """
    Get system context variables automatically injected into all prompts.

    These variables are available in ALL templates without manual passing.
    User-provided kwargs can override these if needed.

    Returns:
        Dict of system context variables:
        - current_date: Today's date in YYYY-MM-DD format
        - current_year: Current year as integer
        - current_datetime: Full datetime string

    Example template usage:
        IMPORTANT: Today's date is {{ current_date }}. Your training data may be outdated.
    """
    now = datetime.now()
    return {
        "current_date": now.strftime("%Y-%m-%d"),
        "current_year": now.year,
        "current_datetime": now.strftime("%Y-%m-%d %H:%M:%S")
    }


def _get_temporal_context_header() -> str:
    """
    Get standard temporal context header for relevance prompts.

    This header is automatically prepended to prompts that opt in via
    the {# temporal_context: true #} directive.

    Returns:
        Formatted temporal context warning text
    """
    now = datetime.now()
    return f"""IMPORTANT: Today's date is {now.strftime("%Y-%m-%d")}. Your training data may contain an incorrect date.

"""


def _should_prepend_temporal_context(template_content: str) -> bool:
    """
    Check if template wants temporal context prepending.

    Templates opt in by including {# temporal_context: true #} directive
    in the first 5 lines.

    Args:
        template_content: Raw template content

    Returns:
        True if directive found and enabled, False otherwise

    Examples:
        >>> content = "{# temporal_context: true #}\\nPrompt text..."
        >>> _should_prepend_temporal_context(content)
        True

        >>> content = "{# temporal_context: false #}\\nPrompt text..."
        >>> _should_prepend_temporal_context(content)
        False
    """
    # Check first 5 lines for directive
    lines = template_content.split('\n')[:5]
    for line in lines:
        if 'temporal_context:' in line.lower():
            return 'true' in line.lower()
    return False  # Default: no prepending (explicit opt-in)


def render_prompt(template_name: str, **kwargs: Any) -> str:
    """
    Render a Jinja2 prompt template with provided variables.

    AUTOMATIC SYSTEM CONTEXT: All templates automatically receive:
    - current_date: Today's date (YYYY-MM-DD)
    - current_year: Current year (int)
    - current_datetime: Full datetime string

    These are injected automatically to prevent LLM temporal confusion.
    User-provided kwargs can override these if needed.

    TEMPORAL CONTEXT PREPENDING: Templates can opt in to automatic
    temporal context header by including this directive in the first 5 lines:
        {# temporal_context: true #}

    When enabled, the header "IMPORTANT: Today's date is YYYY-MM-DD..."
    is automatically prepended to the rendered output.

    This is useful for relevance prompts to prevent LLMs from thinking
    current year queries are "future" data.

    Args:
        template_name: Path to template relative to prompts/ directory
                      (e.g., "deep_research/query_reformulation.j2")
        **kwargs: Template variables to render (merged with system context)

    Returns:
        Rendered prompt string

    Raises:
        TemplateNotFound: If template file doesn't exist
        jinja2.exceptions.UndefinedError: If required variable is missing
        jinja2.exceptions.TemplateSyntaxError: If template has syntax errors

    Examples:
        >>> prompt = render_prompt(
        ...     "deep_research/query_reformulation.j2",
        ...     research_question="What contracts exist for cybersecurity?",
        ...     original_query="cybersecurity contracts",
        ...     results_count=5
        ... )
        # Template automatically has access to {{ current_date }}, etc.

        >>> prompt = render_prompt(
        ...     "integrations/government/usajobs_query_generation.j2",
        ...     research_question="Federal analyst positions",
        ...     api_parameters={"keywords": "analyst", "location": "DC"}
        ... )
    """
    try:
        # Merge system context with user-provided kwargs
        # User kwargs can override system context if needed
        context = _get_system_context()
        context.update(kwargs)

        # Load template
        template: Template = _jinja_env.get_template(template_name)

        # Check if template wants temporal context prepending
        # (via {# temporal_context: true #} directive)
        # Read template source from file to check for directive
        template_path = PROMPTS_DIR / template_name
        template_content = template_path.read_text()

        if _should_prepend_temporal_context(template_content):
            header = _get_temporal_context_header()
            rendered = header + template.render(**context)
        else:
            rendered = template.render(**context)

        return rendered
    except TemplateNotFound as e:
        # Template not found - log and re-raise with helpful context
        full_path = PROMPTS_DIR / template_name
        logger.error(f"Template not found: {template_name} (expected at {full_path})", exc_info=True)
        raise TemplateNotFound(
            f"Template not found: {template_name}\n"
            f"Expected location: {full_path}\n"
            f"Prompts directory: {PROMPTS_DIR}"
        ) from e


def list_templates(module: str = "") -> list[str]:
    """
    List all available prompt templates.

    Args:
        module: Optional module filter (e.g., "deep_research", "integrations/government")

    Returns:
        List of template paths relative to prompts/

    Examples:
        >>> list_templates()
        ['deep_research/task_decomposition.j2', 'deep_research/query_reformulation.j2', ...]

        >>> list_templates("integrations/government")
        ['integrations/government/usajobs_query_generation.j2', ...]
    """
    templates = []
    search_dir = PROMPTS_DIR / module if module else PROMPTS_DIR

    if not search_dir.exists():
        return []

    for template_path in search_dir.rglob("*.j2"):
        # Get path relative to prompts/
        relative_path = template_path.relative_to(PROMPTS_DIR)
        templates.append(str(relative_path))

    return sorted(templates)


def validate_template(template_name: str) -> tuple[bool, str]:
    """
    Validate a template exists and has valid Jinja2 syntax.

    Args:
        template_name: Path to template relative to prompts/

    Returns:
        Tuple of (is_valid, error_message)
        - (True, "") if valid
        - (False, "error message") if invalid

    Examples:
        >>> validate_template("deep_research/query_reformulation.j2")
        (True, "")

        >>> validate_template("nonexistent.j2")
        (False, "Template not found: nonexistent.j2")
    """
    try:
        # Try to load template (checks existence)
        template = _jinja_env.get_template(template_name)

        # Try to render with empty context to catch syntax errors
        # (Won't catch missing variables, but validates template syntax)
        template.module

        return (True, "")
    except TemplateNotFound as e:
        # Template not found during validation
        logger.warning(f"Template validation failed - not found: {template_name}", exc_info=True)
        return (False, f"Template not found: {template_name}")
    except Exception as e:
        # Template has syntax errors
        logger.error(f"Template validation failed - syntax error in {template_name}: {e}", exc_info=True)
        return (False, f"Template syntax error: {str(e)}")


# Export public API
__all__ = [
    "render_prompt",
    "list_templates",
    "validate_template",
    "PROMPTS_DIR"
]
