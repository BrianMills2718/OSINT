#!/usr/bin/env python3
"""
Phase 3C Artifact Validation Test

Validates that Phase 3C research outputs meet quality standards:
- Hypothesis generation and execution
- Coverage assessment decisions
- Delta metrics (new vs duplicate results/entities)
- Proper telemetry logging
- Report completeness

Can be run on existing research artifacts or generate new ones.
"""

import asyncio
import sys
import os
import json
from pathlib import Path
from typing import Dict, List, Optional

# Add parent directory to path
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from research.deep_research import SimpleDeepResearch


class Phase3CValidator:
    """Validates Phase 3C research artifacts."""

    def __init__(self, artifact_dir: str):
        self.artifact_dir = Path(artifact_dir)
        self.errors: List[str] = []
        self.warnings: List[str] = []
        self.passes: List[str] = []

    def validate_all(self) -> bool:
        """Run all validation checks. Returns True if all pass."""
        print(f"\n{'='*80}")
        print(f"PHASE 3C ARTIFACT VALIDATION")
        print(f"{'='*80}")
        print(f"\nArtifact: {self.artifact_dir}")
        print()

        # Check directory exists
        if not self.artifact_dir.exists():
            self.errors.append(f"Artifact directory not found: {self.artifact_dir}")
            self._print_results()
            return False

        # Run validation checks
        self._validate_metadata()
        self._validate_hypothesis_execution()
        self._validate_coverage_decisions()
        self._validate_delta_metrics()
        self._validate_execution_log()
        self._validate_report()

        # Print results
        self._print_results()

        return len(self.errors) == 0

    def _validate_metadata(self):
        """Check metadata.json exists and has required fields."""
        metadata_path = self.artifact_dir / "metadata.json"

        if not metadata_path.exists():
            self.errors.append("metadata.json not found")
            return

        try:
            with open(metadata_path) as f:
                metadata = json.load(f)

            required_fields = ['research_question', 'tasks_executed', 'total_results',
                             'output_directory', 'hypothesis_execution_summary']
            missing = [f for f in required_fields if f not in metadata]

            if missing:
                self.errors.append(f"metadata.json missing fields: {missing}")
            else:
                self.passes.append("metadata.json has all required fields")

        except json.JSONDecodeError as e:
            self.errors.append(f"metadata.json invalid JSON: {e}")
        except Exception as e:
            self.errors.append(f"Error reading metadata.json: {e}")

    def _validate_hypothesis_execution(self):
        """Validate hypothesis execution summary."""
        metadata_path = self.artifact_dir / "metadata.json"
        if not metadata_path.exists():
            return  # Already reported in _validate_metadata

        with open(metadata_path) as f:
            metadata = json.load(f)

        hyp_summary = metadata.get('hypothesis_execution_summary', {})

        if not hyp_summary:
            self.errors.append("No hypothesis_execution_summary in metadata")
            return

        total_hypotheses = sum(len(runs) for runs in hyp_summary.values())
        if total_hypotheses == 0:
            self.errors.append("No hypotheses executed")
            return

        self.passes.append(f"Hypothesis execution: {total_hypotheses} hypotheses across {len(hyp_summary)} tasks")

    def _validate_coverage_decisions(self):
        """Validate coverage assessment decisions."""
        metadata_path = self.artifact_dir / "metadata.json"
        if not metadata_path.exists():
            return

        with open(metadata_path) as f:
            metadata = json.load(f)

        hyp_summary = metadata.get('hypothesis_execution_summary', {})

        # Check for coverage decisions in hypothesis runs
        coverage_found = False
        for task_id, runs in hyp_summary.items():
            for run in runs:
                if 'coverage_assessment' in run:
                    coverage_found = True
                    assessment = run['coverage_assessment']

                    # Validate schema
                    required = ['decision', 'rationale', 'coverage_score',
                              'incremental_gain_last', 'confidence']
                    missing = [f for f in required if f not in assessment]

                    if missing:
                        self.errors.append(f"Coverage assessment missing fields: {missing}")
                    else:
                        score = assessment.get('coverage_score', 0)
                        gain = assessment.get('incremental_gain_last', 0)
                        self.passes.append(f"Coverage assessment valid (score={score}%, gain={gain}%)")

        if not coverage_found:
            self.warnings.append("No coverage assessments (may have only executed 1 hypothesis)")

    def _validate_delta_metrics(self):
        """Validate delta metrics calculation."""
        metadata_path = self.artifact_dir / "metadata.json"
        if not metadata_path.exists():
            return

        with open(metadata_path) as f:
            metadata = json.load(f)

        hyp_summary = metadata.get('hypothesis_execution_summary', {})

        for task_id, runs in hyp_summary.items():
            for run in runs:
                if 'delta_metrics' not in run:
                    self.errors.append(f"Task {task_id} H{run.get('hypothesis_id', '?')} missing delta_metrics")
                    continue

                delta = run['delta_metrics']
                required = ['results_new', 'results_duplicate', 'entities_new', 'entities_duplicate']
                missing = [f for f in required if f not in delta]

                if missing:
                    self.errors.append(f"Delta metrics missing fields: {missing}")
                else:
                    new_results = delta['results_new']
                    dup_results = delta['results_duplicate']
                    self.passes.append(f"Delta metrics: {new_results} new + {dup_results} dup results")

    def _validate_execution_log(self):
        """Validate execution_log.jsonl."""
        log_path = self.artifact_dir / "execution_log.jsonl"

        if not log_path.exists():
            self.warnings.append("execution_log.jsonl not found")
            return

        try:
            coverage_events = []
            with open(log_path) as f:
                for line in f:
                    entry = json.loads(line)
                    if entry.get('action_type') == 'coverage_assessment':
                        coverage_events.append(entry)

            if coverage_events:
                self.passes.append(f"Execution log: {len(coverage_events)} coverage events")

                # Validate event structure
                event = coverage_events[0]
                payload = event.get('action_payload', {})
                required = ['decision', 'coverage_score', 'time_elapsed_seconds',
                          'hypotheses_remaining']
                missing = [f for f in required if f not in payload]

                if missing:
                    self.errors.append(f"Coverage event missing fields: {missing}")
                else:
                    self.passes.append("Coverage events have all required fields")
            else:
                self.warnings.append("No coverage events in log (may have only executed 1 hypothesis)")

        except json.JSONDecodeError as e:
            self.errors.append(f"execution_log.jsonl invalid JSON: {e}")
        except Exception as e:
            self.errors.append(f"Error reading execution_log.jsonl: {e}")

    def _validate_report(self):
        """Validate final report."""
        # Find report.md (may have timestamp suffix)
        report_files = list(self.artifact_dir.glob("report*.md"))

        if not report_files:
            self.errors.append("No report.md file found")
            return

        report_path = report_files[0]

        try:
            with open(report_path) as f:
                report = f.read()

            # Check for key sections
            if "# Research Report:" in report or "## Executive Summary" in report:
                self.passes.append("Report has proper structure")
            else:
                self.warnings.append("Report may be missing standard sections")

            # Check for coverage section (optional - depends on whether coverage ran)
            if "Coverage Assessment" in report:
                self.passes.append("Report includes coverage assessment section")
            else:
                self.warnings.append("Report missing coverage assessment (may not have coverage decisions)")

            # Check minimum length
            if len(report) < 500:
                self.warnings.append(f"Report very short ({len(report)} chars)")
            else:
                self.passes.append(f"Report has substantial content ({len(report)} chars)")

        except Exception as e:
            self.errors.append(f"Error reading report: {e}")

    def _print_results(self):
        """Print validation results."""
        print(f"\n{'='*80}")
        print("VALIDATION RESULTS")
        print(f"{'='*80}")

        if self.passes:
            print(f"\n✅ PASSED ({len(self.passes)}):")
            for p in self.passes:
                print(f"   {p}")

        if self.warnings:
            print(f"\n⚠️  WARNINGS ({len(self.warnings)}):")
            for w in self.warnings:
                print(f"   {w}")

        if self.errors:
            print(f"\n❌ ERRORS ({len(self.errors)}):")
            for e in self.errors:
                print(f"   {e}")

        print(f"\n{'='*80}")
        if self.errors:
            print("❌ VALIDATION FAILED")
        else:
            print("✅ VALIDATION PASSED")
        print(f"{'='*80}\n")


async def test_existing_artifacts():
    """Test validation on existing Phase 3C artifacts."""
    print("\nValidating existing Phase 3C artifacts...")

    # Artifacts documented in CLAUDE.md
    artifacts = [
        "data/research_output/2025-11-16_04-55-21_what_is_gs_2210_job_series",
        "data/research_output/2025-11-16_05-28-26_how_do_i_qualify_for_federal_cybersecurity_jobs"
    ]

    all_passed = True

    for artifact_path in artifacts:
        if os.path.exists(artifact_path):
            validator = Phase3CValidator(artifact_path)
            passed = validator.validate_all()
            all_passed = all_passed and passed
        else:
            print(f"\n⚠️  Artifact not found: {artifact_path}")
            print("   (May have been moved or deleted)")

    return all_passed


async def test_new_artifact():
    """Generate and validate a new Phase 3C artifact."""
    print("\n" + "="*80)
    print("GENERATING NEW PHASE 3C ARTIFACT FOR VALIDATION")
    print("="*80)

    # Create engine with Phase 3C config
    engine = SimpleDeepResearch(
        max_tasks=2,  # Small but enough to test
        max_retries_per_task=1,
        max_time_minutes=15,
        save_output=True
    )

    # Configure Phase 3C
    engine.hypothesis_mode = "execution"
    engine.hypothesis_branching_enabled = True
    engine.max_hypotheses_per_task = 3
    engine.coverage_mode = True
    engine.max_hypotheses_to_execute = 3
    engine.max_time_per_task_seconds = 180

    # Simple query
    query = "What federal agencies hire cybersecurity professionals?"

    print(f"\nQuery: {query}")
    print("Expected: 2 tasks, 3 hypotheses each, coverage assessment")
    print("\nExecuting... (may take 5-10 minutes)\n")

    result = await engine.research(query)

    if result.get('output_directory'):
        print(f"\nArtifact created: {result['output_directory']}")
        print("\nValidating...")

        validator = Phase3CValidator(result['output_directory'])
        return validator.validate_all()
    else:
        print("\n❌ No output_directory in result")
        return False


if __name__ == "__main__":
    # Choose which test to run
    import argparse

    parser = argparse.ArgumentParser(description="Validate Phase 3C research artifacts")
    parser.add_argument("--existing", action="store_true",
                       help="Validate existing artifacts from CLAUDE.md")
    parser.add_argument("--new", action="store_true",
                       help="Generate and validate new artifact")
    parser.add_argument("--artifact", type=str,
                       help="Validate specific artifact directory")

    args = parser.parse_args()

    if args.artifact:
        # Validate specific artifact
        validator = Phase3CValidator(args.artifact)
        passed = validator.validate_all()
        sys.exit(0 if passed else 1)

    elif args.new:
        # Generate and validate new artifact
        passed = asyncio.run(test_new_artifact())
        sys.exit(0 if passed else 1)

    else:
        # Default: validate existing artifacts
        passed = asyncio.run(test_existing_artifacts())
        sys.exit(0 if passed else 1)
