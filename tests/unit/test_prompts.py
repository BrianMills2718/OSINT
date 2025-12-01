#!/usr/bin/env python3
"""
Unit tests for Jinja2 prompt templates.

Validates:
- All templates render without syntax errors
- Temporal context injection works
- JSON examples not interpreted as Jinja
- Variables substituted correctly

Run: pytest tests/unit/test_prompts.py -v
"""

import pytest
from pathlib import Path
import sys

# Add project root to path
sys.path.insert(0, str(Path(__file__).parent.parent.parent))

from core.prompt_loader import render_prompt

PROMPTS_DIR = Path(__file__).parent.parent.parent / "prompts"


@pytest.fixture
def mock_context():
    """Standard mock context for template rendering."""
    return {
        "goal": "Test goal",
        "evidence_text": "Test evidence",
        "original_objective": "Test objective",
        "temporal_context": "Today's date: 2025-12-01\nCurrent year: 2025",
        "research_question": "Test question",
        "available_sources": [
            {"id": "source1", "name": "Source 1", "description": "Test source"},
            {"id": "source2", "name": "Source 2", "description": "Test source"}
        ],
        "results": [],
        "hypothesis": "Test hypothesis",
        "task_query": "Test query",
        "question": "Test question",
        "context": {"test": "value"},
    }


class TestPromptTemplates:
    """Test suite for all Jinja2 templates."""

    def test_all_templates_found(self):
        """Should find 50+ prompt templates."""
        templates = list(PROMPTS_DIR.rglob("*.j2"))
        assert len(templates) >= 50, f"Expected 50+ templates, found {len(templates)}"

    def test_all_templates_render(self, mock_context):
        """All .j2 files should render without syntax errors."""
        templates = list(PROMPTS_DIR.rglob("*.j2"))

        errors = []
        successes = 0

        for template_path in templates:
            try:
                # Get relative path from prompts dir
                rel_path = str(template_path.relative_to(PROMPTS_DIR))

                # Attempt to render with mock context
                result = render_prompt(rel_path, **mock_context)

                assert result is not None, f"{rel_path}: render returned None"
                assert len(result) > 0, f"{rel_path}: render returned empty string"

                successes += 1

            except Exception as e:
                errors.append(f"{template_path.name}: {e}")

        # Report results
        if errors:
            error_msg = f"\n\n❌ {len(errors)} template(s) failed to render:\n" + "\n".join(errors)
            error_msg += f"\n\n✅ {successes} template(s) rendered successfully"
            pytest.fail(error_msg)

        print(f"\n✅ All {successes} templates rendered successfully!")

    def test_temporal_context_injected_filter_prompt(self, mock_context):
        """Filter prompt should include temporal context."""
        result = render_prompt(
            "recursive_agent/result_filtering.j2",
            goal="Test goal",
            evidence_text="Test evidence",
            original_objective="Test objective"
        )

        # Should have temporal context header (injected by prompt_loader)
        assert "TEMPORAL CONTEXT" in result or "Today's date:" in result or "2025" in result, \
            "Temporal context not found in filter prompt"

    def test_json_examples_preserved(self, mock_context):
        """JSON in {% raw %} blocks should not be interpreted."""
        result = render_prompt(
            "recursive_agent/result_filtering.j2",
            goal="Test goal",
            evidence_text="Test evidence",
            original_objective="Test objective"
        )

        # Should contain literal JSON structure
        assert "{" in result and "}" in result, "No JSON structure found"

        # Should not have unsubstituted Jinja variables
        assert "{{ goal }}" not in result, "Unsubstituted {{ goal }} found"
        assert "{{ evidence_text }}" not in result, "Unsubstituted {{ evidence_text }} found"

    def test_variables_substituted(self, mock_context):
        """Template variables should be replaced with actual values."""
        goal_text = "Find Anduril Industries contracts"
        evidence_text = "[Sample evidence content]"

        result = render_prompt(
            "recursive_agent/result_filtering.j2",
            goal=goal_text,
            evidence_text=evidence_text,
            original_objective="Research defense contractors"
        )

        # Check actual values appear
        assert goal_text in result, f"Goal '{goal_text}' not found in rendered output"
        assert evidence_text in result, f"Evidence '{evidence_text}' not found in rendered output"

        # Check no unsubstituted placeholders
        assert "{{ goal }}" not in result, "Placeholder {{ goal }} not substituted"
        assert "{{ evidence_text }}" not in result, "Placeholder {{ evidence_text }} not substituted"
        assert "{{ original_objective }}" not in result, "Placeholder {{ original_objective }} not substituted"

    def test_no_template_syntax_errors(self):
        """No templates should have Jinja2 syntax errors."""
        templates = list(PROMPTS_DIR.rglob("*.j2"))

        syntax_errors = []

        for template_path in templates:
            try:
                # Read template and check for common syntax errors
                content = template_path.read_text()

                # Check for mismatched braces
                if content.count("{{") != content.count("}}"):
                    syntax_errors.append(f"{template_path.name}: Mismatched double-brace pairs")

                if content.count("{%") != content.count("%}"):
                    syntax_errors.append(f"{template_path.name}: Mismatched percent-brace tags")

                # Check for raw/endraw pairs
                if "{% raw %}" in content:
                    raw_count = content.count("{% raw %}")
                    endraw_count = content.count("{% endraw %}")
                    if raw_count != endraw_count:
                        syntax_errors.append(
                            f"{template_path.name}: Mismatched raw/endraw tags "
                            f"({raw_count} raw, {endraw_count} endraw)"
                        )

            except Exception as e:
                syntax_errors.append(f"{template_path.name}: Error reading file - {e}")

        if syntax_errors:
            pytest.fail("\n\n❌ Syntax errors found:\n" + "\n".join(syntax_errors))

    def test_recursive_agent_prompts_exist(self):
        """Critical recursive agent prompts should exist."""
        required_prompts = [
            "recursive_agent/result_filtering.j2",
        ]

        for prompt_path in required_prompts:
            full_path = PROMPTS_DIR / prompt_path
            assert full_path.exists(), f"Required prompt missing: {prompt_path}"

    def test_integration_prompts_exist(self):
        """Key integration prompts should exist."""
        # Sample - not exhaustive
        expected_integrations = [
            "sam_query_generation.j2",
            "usaspending_query_generation.j2",
            "newsapi_query.j2",
        ]

        integrations_dir = PROMPTS_DIR / "integrations"
        if integrations_dir.exists():
            found_prompts = [p.name for p in integrations_dir.glob("*.j2")]

            for expected in expected_integrations:
                assert expected in found_prompts, \
                    f"Expected integration prompt missing: {expected}"


if __name__ == "__main__":
    # Allow running directly: python tests/unit/test_prompts.py
    pytest.main([__file__, "-v"])
