#!/usr/bin/env python3
"""
Unit tests for core/prompt_loader.py

Tests Jinja2 template loading infrastructure to ensure:
- Templates load correctly
- Variables interpolate correctly
- JSON examples work without escaping
- Error handling works (missing templates, undefined variables)
- Helper functions (list_templates, validate_template) work
"""

import pytest
from pathlib import Path
from jinja2 import TemplateNotFound, UndefinedError

from core.prompt_loader import (
    render_prompt,
    list_templates,
    validate_template,
    PROMPTS_DIR
)


class TestPromptLoaderInfrastructure:
    """Test core prompt loader functionality."""

    def test_prompts_dir_exists(self):
        """Test that prompts/ directory exists."""
        assert PROMPTS_DIR.exists(), f"prompts/ directory not found at {PROMPTS_DIR}"
        assert PROMPTS_DIR.is_dir(), f"prompts/ is not a directory: {PROMPTS_DIR}"

    def test_prompts_dir_structure(self):
        """Test that expected subdirectories exist."""
        assert (PROMPTS_DIR / "deep_research").exists(), "prompts/deep_research/ not found"
        assert (PROMPTS_DIR / "integrations" / "government").exists(), "prompts/integrations/government/ not found"
        assert (PROMPTS_DIR / "integrations" / "social").exists(), "prompts/integrations/social/ not found"


class TestRenderPrompt:
    """Test render_prompt() function with real templates."""

    @pytest.fixture
    def test_template_path(self, tmp_path):
        """Create a test template file."""
        # Create temporary prompts directory
        test_prompts_dir = tmp_path / "prompts"
        test_prompts_dir.mkdir()

        # Create test template
        template_path = test_prompts_dir / "test_template.j2"
        template_path.write_text("""
Your task: {{ task_description }}

Example JSON:
{
  "query": "{{ example_query }}",
  "params": {
    "time_filter": "year",
    "keywords": ["test", "example"]
  }
}

Original query: {{ original_query }}
""")
        return str(template_path.relative_to(test_prompts_dir.parent / "prompts"))

    def test_render_simple_variables(self):
        """Test rendering template with simple variable interpolation."""
        # Create minimal test template on-the-fly
        test_dir = PROMPTS_DIR / "test"
        test_dir.mkdir(exist_ok=True)
        test_template = test_dir / "simple.j2"
        test_template.write_text("Task: {{ task }}")

        try:
            result = render_prompt("test/simple.j2", task="test_task")
            assert result == "Task: test_task"
        finally:
            # Cleanup
            test_template.unlink()
            test_dir.rmdir()

    def test_render_json_no_escaping(self):
        """Test that JSON examples don't require escaping."""
        # Create test template with JSON
        test_dir = PROMPTS_DIR / "test"
        test_dir.mkdir(exist_ok=True)
        test_template = test_dir / "json_test.j2"
        test_template.write_text("""
Query: {{ query }}

JSON example:
{
  "param": {"nested": "value"},
  "array": ["item1", "item2"]
}
""")

        try:
            result = render_prompt("test/json_test.j2", query="test")
            # Verify JSON structure preserved (no escaping needed)
            assert '{"nested": "value"}' in result
            assert '["item1", "item2"]' in result
        finally:
            # Cleanup
            test_template.unlink()
            test_dir.rmdir()

    def test_render_missing_template(self):
        """Test error handling for missing template."""
        with pytest.raises(TemplateNotFound):
            render_prompt("nonexistent/template.j2", var="value")

    def test_render_undefined_variable(self):
        """Test error handling for undefined variables (strict mode)."""
        # Create test template requiring variable
        test_dir = PROMPTS_DIR / "test"
        test_dir.mkdir(exist_ok=True)
        test_template = test_dir / "strict.j2"
        test_template.write_text("Task: {{ required_var }}")

        try:
            # StrictUndefined should raise error on missing variable
            with pytest.raises(Exception):  # UndefinedError or TemplateSyntaxError
                render_prompt("test/strict.j2")  # Missing required_var
        finally:
            # Cleanup
            test_template.unlink()
            test_dir.rmdir()


class TestListTemplates:
    """Test list_templates() function."""

    def test_list_all_templates(self):
        """Test listing all templates."""
        templates = list_templates()
        assert isinstance(templates, list)
        # Should return list of paths (empty initially until templates migrate)
        # After migration, this will have templates

    def test_list_templates_by_module(self):
        """Test filtering templates by module."""
        # Create test templates
        test_dir = PROMPTS_DIR / "test_module"
        test_dir.mkdir(exist_ok=True)
        (test_dir / "template1.j2").write_text("test")
        (test_dir / "template2.j2").write_text("test")

        try:
            templates = list_templates("test_module")
            assert len(templates) == 2
            assert "test_module/template1.j2" in templates
            assert "test_module/template2.j2" in templates
        finally:
            # Cleanup
            (test_dir / "template1.j2").unlink()
            (test_dir / "template2.j2").unlink()
            test_dir.rmdir()

    def test_list_templates_nonexistent_module(self):
        """Test listing templates for nonexistent module."""
        templates = list_templates("nonexistent_module")
        assert templates == []


class TestValidateTemplate:
    """Test validate_template() function."""

    def test_validate_existing_template(self):
        """Test validation of existing template."""
        # Create test template
        test_dir = PROMPTS_DIR / "test"
        test_dir.mkdir(exist_ok=True)
        test_template = test_dir / "valid.j2"
        test_template.write_text("Task: {{ task }}")

        try:
            is_valid, error = validate_template("test/valid.j2")
            assert is_valid is True
            assert error == ""
        finally:
            # Cleanup
            test_template.unlink()
            test_dir.rmdir()

    def test_validate_missing_template(self):
        """Test validation of missing template."""
        is_valid, error = validate_template("nonexistent.j2")
        assert is_valid is False
        assert "not found" in error.lower()

    def test_validate_syntax_error(self):
        """Test validation of template with syntax errors."""
        # Create test template with syntax error
        test_dir = PROMPTS_DIR / "test"
        test_dir.mkdir(exist_ok=True)
        test_template = test_dir / "syntax_error.j2"
        test_template.write_text("Task: {{ unclosed")  # Missing closing }}

        try:
            is_valid, error = validate_template("test/syntax_error.j2")
            assert is_valid is False
            assert len(error) > 0
        finally:
            # Cleanup
            test_template.unlink()
            test_dir.rmdir()


class TestRealWorldUsage:
    """Test real-world usage patterns from FSTRING_JSON_METHODOLOGY.md"""

    def test_json_param_adjustments_pattern(self):
        """
        Test the exact pattern from docs/FSTRING_JSON_METHODOLOGY.md.

        This pattern appeared in deep_research.py:1658-1661 and caused errors
        with f-strings. Should work flawlessly with Jinja2.
        """
        # Create test template matching real-world usage
        test_dir = PROMPTS_DIR / "test"
        test_dir.mkdir(exist_ok=True)
        test_template = test_dir / "param_adjustments.j2"
        test_template.write_text("""
Return JSON with:
{
  "query": "new query text",
  "param_adjustments": {
    "reddit": {"time_filter": "year"},
    "usajobs": {"keywords": "broad keyword"}
  }
}

Original query: {{ original_query }}
Results count: {{ results_count }}
""")

        try:
            result = render_prompt(
                "test/param_adjustments.j2",
                original_query="test query",
                results_count=5
            )

            # Verify JSON structure intact (no escape sequences)
            assert '{"time_filter": "year"}' in result
            assert '{"keywords": "broad keyword"}' in result
            assert "Original query: test query" in result
            assert "Results count: 5" in result

            # Verify NO escaped braces (would be \{\{ or \}\} if escaped)
            assert "\\{" not in result
            assert "\\}" not in result
        finally:
            # Cleanup
            test_template.unlink()
            test_dir.rmdir()

    def test_usajobs_param_example_pattern(self):
        """
        Test USAJobs parameter example from FSTRING_JSON_METHODOLOGY.md.

        This was referenced as a common pattern needing the fix.
        """
        test_dir = PROMPTS_DIR / "test"
        test_dir.mkdir(exist_ok=True)
        test_template = test_dir / "usajobs_example.j2"
        test_template.write_text("""
Example params:
{
  "keywords": "cybersecurity",
  "location": "Washington, DC",
  "pay_grade_low": 11,
  "pay_grade_high": 13
}

Your query: {{ query }}
""")

        try:
            result = render_prompt("test/usajobs_example.j2", query="analyst positions")
            assert '"keywords": "cybersecurity"' in result
            assert '"pay_grade_low": 11' in result
            assert "Your query: analyst positions" in result
        finally:
            # Cleanup
            test_template.unlink()
            test_dir.rmdir()


# Run tests if executed directly
if __name__ == "__main__":
    pytest.main([__file__, "-v"])
