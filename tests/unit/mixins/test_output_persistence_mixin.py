#!/usr/bin/env python3
"""
Unit tests for OutputPersistenceMixin.

Tests:
- _generate_global_coverage_summary (pure logic)
- _save_research_output (file I/O, mocked)
"""

import json
import os
import pytest
import tempfile
from datetime import datetime
from pathlib import Path
from unittest.mock import MagicMock, patch


class MockResearchTask:
    """Mock ResearchTask for testing."""

    def __init__(self, task_id=1, query="test query"):
        self.id = task_id
        self.query = query
        self.hypotheses = None
        self.hypothesis_runs = []
        self.metadata = {}
        self.accumulated_results = []
        self.entities_found = []
        self.priority = 5
        self.priority_reasoning = ""
        self.estimated_value = 0.5
        self.estimated_redundancy = 0.0
        self.parent_task_id = None


class TestGenerateGlobalCoverageSummary:
    """Test _generate_global_coverage_summary method (pure logic)."""

    def setup_method(self):
        """Create mixin instance with required attributes."""
        from research.mixins.output_persistence_mixin import OutputPersistenceMixin

        class MockHost(OutputPersistenceMixin):
            completed_tasks = []

        self.host = MockHost()

    def test_no_completed_tasks_returns_initial_message(self):
        """Returns initial message when no tasks completed."""
        result = self.host._generate_global_coverage_summary()
        assert "No tasks completed" in result

    def test_summarizes_completed_tasks_count(self):
        """Includes completed task count in summary."""
        self.host.completed_tasks = [
            MockResearchTask(1, "query1"),
            MockResearchTask(2, "query2"),
            MockResearchTask(3, "query3")
        ]
        # Add results
        self.host.completed_tasks[0].accumulated_results = [{"url": "1"}]
        self.host.completed_tasks[1].accumulated_results = [{"url": "2"}, {"url": "3"}]
        self.host.completed_tasks[2].accumulated_results = []

        result = self.host._generate_global_coverage_summary()

        assert "Completed 3 tasks" in result
        assert "3 results" in result

    def test_includes_recent_assessments(self):
        """Includes assessments from recent tasks."""
        task1 = MockResearchTask(1)
        task1.metadata = {
            "coverage_decisions": [
                {"assessment": "Good coverage of contracts found."}
            ]
        }
        task1.accumulated_results = [{"url": "1"}]

        self.host.completed_tasks = [task1]

        result = self.host._generate_global_coverage_summary()

        assert "Task 1" in result
        assert "Good coverage" in result

    def test_includes_key_gaps(self):
        """Includes key gaps from coverage decisions."""
        task1 = MockResearchTask(1)
        task1.metadata = {
            "coverage_decisions": [
                {"assessment": "Test", "gaps_identified": ["Timeline missing", "Budget unclear"]}
            ]
        }
        task1.accumulated_results = []

        self.host.completed_tasks = [task1]

        result = self.host._generate_global_coverage_summary()

        assert "gaps" in result.lower()

    def test_deduplicates_gaps(self):
        """Deduplicates gaps across multiple tasks."""
        task1 = MockResearchTask(1)
        task1.metadata = {
            "coverage_decisions": [
                {"assessment": "Test", "gaps_identified": ["Timeline missing"]}
            ]
        }
        task1.accumulated_results = []

        task2 = MockResearchTask(2)
        task2.metadata = {
            "coverage_decisions": [
                {"assessment": "Test", "gaps_identified": ["Timeline missing", "Budget info"]}
            ]
        }
        task2.accumulated_results = []

        self.host.completed_tasks = [task1, task2]

        result = self.host._generate_global_coverage_summary()

        # Should only mention "Timeline missing" once (deduplicated)
        assert result.count("Timeline missing") <= 1


class TestSaveResearchOutput:
    """Test _save_research_output method (file I/O)."""

    def setup_method(self):
        """Create mixin instance with required attributes."""
        from research.mixins.output_persistence_mixin import OutputPersistenceMixin

        class MockHost(OutputPersistenceMixin):
            start_time = datetime(2024, 6, 15, 10, 30, 0)
            output_dir = tempfile.mkdtemp()
            completed_tasks = []
            failed_tasks = []
            results_by_task = {}
            max_tasks = 10
            max_retries_per_task = 3
            max_time_minutes = 30
            min_results_per_task = 5
            max_concurrent_tasks = 3
            hypothesis_branching_enabled = False
            hypothesis_mode = "off"
            max_hypotheses_per_task = 5
            manager_enabled = False
            saturation_detection_enabled = False
            saturation_check_interval = 5
            saturation_confidence_threshold = 0.8

        self.host = MockHost()

    def teardown_method(self):
        """Clean up temp directory."""
        import shutil
        if hasattr(self.host, 'output_dir') and os.path.exists(self.host.output_dir):
            shutil.rmtree(self.host.output_dir)

    def test_creates_output_directory(self):
        """Creates timestamped output directory."""
        question = "What are defense contracts?"
        result_dict = {
            "report": "# Test Report",
            "total_results": 0,
            "tasks_executed": 0,
            "tasks_failed": 0,
            "elapsed_minutes": 1.0,
            "sources_searched": [],
            "entities_discovered": []
        }

        output_path = self.host._save_research_output(question, result_dict)

        assert os.path.exists(output_path)
        assert "2024-06-15_10-30-00" in output_path
        assert "what_are_defense_contracts" in output_path

    def test_saves_results_json(self):
        """Saves results.json with correct structure."""
        question = "Test question"
        result_dict = {
            "report": "# Test",
            "total_results": 5,
            "tasks_executed": 1,
            "tasks_failed": 0,
            "elapsed_minutes": 1.0,
            "sources_searched": ["SAM.gov"],
            "entities_discovered": ["Lockheed Martin"]
        }

        output_path = self.host._save_research_output(question, result_dict)

        results_file = Path(output_path) / "results.json"
        assert results_file.exists()

        with open(results_file) as f:
            saved_results = json.load(f)

        assert "total_results" in saved_results
        assert "results_by_task" in saved_results

    def test_saves_report_markdown(self):
        """Saves report.md with report content."""
        question = "Test"
        result_dict = {
            "report": "# My Research Report\n\nContent here.",
            "total_results": 0,
            "tasks_executed": 0,
            "tasks_failed": 0,
            "elapsed_minutes": 1.0,
            "sources_searched": [],
            "entities_discovered": []
        }

        output_path = self.host._save_research_output(question, result_dict)

        report_file = Path(output_path) / "report.md"
        assert report_file.exists()

        content = report_file.read_text()
        assert "# My Research Report" in content

    def test_saves_metadata_json(self):
        """Saves metadata.json with research parameters."""
        question = "Test"
        result_dict = {
            "report": "# Test",
            "total_results": 0,
            "tasks_executed": 1,
            "tasks_failed": 0,
            "elapsed_minutes": 5.5,
            "sources_searched": ["SAM.gov"],
            "entities_discovered": []
        }

        output_path = self.host._save_research_output(question, result_dict)

        metadata_file = Path(output_path) / "metadata.json"
        assert metadata_file.exists()

        with open(metadata_file) as f:
            metadata = json.load(f)

        assert metadata["research_question"] == "Test"
        assert "engine_config" in metadata
        assert metadata["engine_config"]["max_tasks"] == 10

    def test_aggregates_raw_task_files(self):
        """Aggregates results from raw task files."""
        question = "Test"

        # Create raw directory with task file
        output_dir = Path(self.host.output_dir)
        self.host.start_time = datetime(2024, 6, 15, 10, 30, 0)
        slug = "test"
        dir_name = f"2024-06-15_10-30-00_{slug}"
        raw_dir = output_dir / dir_name / "raw"
        raw_dir.mkdir(parents=True, exist_ok=True)

        # Create a raw task file
        task_data = {"total_results": 3, "results": [{"url": "1"}, {"url": "2"}, {"url": "3"}]}
        with open(raw_dir / "task_1_results.json", "w") as f:
            json.dump(task_data, f)

        result_dict = {
            "report": "# Test",
            "total_results": 0,
            "tasks_executed": 1,
            "tasks_failed": 0,
            "elapsed_minutes": 1.0,
            "sources_searched": [],
            "entities_discovered": []
        }

        output_path = self.host._save_research_output(question, result_dict)

        # Check that results were aggregated
        with open(Path(output_path) / "results.json") as f:
            saved = json.load(f)

        assert saved["total_results"] >= 3

    def test_deduplicates_results_by_url_and_title(self):
        """Deduplicates results by (url, title) pair."""
        question = "Test"

        # Set up results with duplicates
        self.host.results_by_task = {
            1: {
                "total_results": 3,
                "results": [
                    {"url": "https://example.com/1", "title": "Same Title"},
                    {"url": "https://example.com/1", "title": "Same Title"},  # Duplicate
                    {"url": "https://example.com/2", "title": "Different"}
                ]
            }
        }

        result_dict = {
            "report": "# Test",
            "total_results": 3,
            "tasks_executed": 1,
            "tasks_failed": 0,
            "elapsed_minutes": 1.0,
            "sources_searched": [],
            "entities_discovered": []
        }

        output_path = self.host._save_research_output(question, result_dict)

        with open(Path(output_path) / "results.json") as f:
            saved = json.load(f)

        # Should be deduplicated to 2 unique results
        assert saved["total_results"] == 2
        assert saved["duplicates_removed"] == 1

    def test_slug_generation_handles_special_chars(self):
        """Question slug handles special characters."""
        question = "What are F-35 contracts? (2024)"

        result_dict = {
            "report": "# Test",
            "total_results": 0,
            "tasks_executed": 0,
            "tasks_failed": 0,
            "elapsed_minutes": 1.0,
            "sources_searched": [],
            "entities_discovered": []
        }

        output_path = self.host._save_research_output(question, result_dict)

        # Should have alphanumeric slug
        assert "what_are_f_35_contracts" in output_path.lower()


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
