#!/usr/bin/env python3
"""
Entry Point Smoke Tests

Validates that user-facing entry points load correctly and don't crash:
- apps/ai_research.py (CLI research interface)
- apps/unified_search_app.py (Streamlit UI)

These are SMOKE TESTS only - they verify basic functionality,
not comprehensive feature testing.
"""

import sys
import os
import subprocess
from pathlib import Path

# Add parent directory to path
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))


class EntryPointTester:
    """Smoke tests for entry point scripts."""

    def __init__(self):
        self.repo_root = Path(__file__).parent.parent
        self.errors = []
        self.warnings = []
        self.passes = []

    def test_all(self) -> bool:
        """Run all entry point tests. Returns True if all pass."""
        print(f"\n{'='*80}")
        print("ENTRY POINT SMOKE TESTS")
        print(f"{'='*80}")
        print(f"\nRepository: {self.repo_root}")
        print()

        # Run tests
        self._test_imports()
        self._test_ai_research_syntax()
        self._test_streamlit_syntax()
        self._test_deep_research_import()
        self._test_config_loader()

        # Print results
        self._print_results()

        return len(self.errors) == 0

    def _test_imports(self):
        """Test that all entry points can be imported."""
        print("Testing imports...")

        # Test ai_research.py imports (Streamlit UI)
        try:
            ai_research = self.repo_root / "apps" / "ai_research.py"

            if not ai_research.exists():
                self.errors.append("apps/ai_research.py not found")
                return

            with open(ai_research) as f:
                content = f.read()

            # Check for critical imports (it's a Streamlit app)
            required_imports = [
                "import streamlit",
                "from dotenv import load_dotenv"
            ]

            for imp in required_imports:
                if imp not in content:
                    self.warnings.append(f"ai_research.py missing import: {imp}")

            self.passes.append("ai_research.py file structure valid")

        except Exception as e:
            self.errors.append(f"Error reading ai_research.py: {e}")

        # Test unified_search_app.py
        try:
            unified_app = self.repo_root / "apps" / "unified_search_app.py"

            if not unified_app.exists():
                self.errors.append("apps/unified_search_app.py not found")
                return

            with open(unified_app) as f:
                content = f.read()

            # Check for Streamlit
            if "import streamlit" not in content:
                self.warnings.append("unified_search_app.py missing streamlit import")

            self.passes.append("unified_search_app.py file structure valid")

        except Exception as e:
            self.errors.append(f"Error reading unified_search_app.py: {e}")

    def _test_ai_research_syntax(self):
        """Test ai_research.py Python syntax."""
        print("Testing ai_research.py syntax...")

        try:
            result = subprocess.run(
                ["python3", "-m", "py_compile", "apps/ai_research.py"],
                cwd=self.repo_root,
                capture_output=True,
                text=True,
                timeout=10
            )

            if result.returncode == 0:
                self.passes.append("ai_research.py syntax valid")
            else:
                self.errors.append(f"ai_research.py syntax error: {result.stderr[:200]}")

        except subprocess.TimeoutExpired:
            self.errors.append("ai_research.py syntax check timed out")
        except FileNotFoundError:
            self.errors.append("python3 not found in PATH")
        except Exception as e:
            self.errors.append(f"Error testing ai_research.py: {e}")

    def _test_streamlit_syntax(self):
        """Test Streamlit app syntax (streamlit run --dry-run)."""
        print("Testing unified_search_app.py syntax...")

        # Check if streamlit is installed
        try:
            result = subprocess.run(
                ["streamlit", "--version"],
                capture_output=True,
                text=True,
                timeout=5
            )

            if result.returncode != 0:
                self.warnings.append("Streamlit not installed (pip install streamlit)")
                return

        except FileNotFoundError:
            self.warnings.append("Streamlit not installed (pip install streamlit)")
            return
        except Exception:
            self.warnings.append("Could not check Streamlit installation")
            return

        # Try syntax check
        try:
            # Note: streamlit doesn't have --dry-run, so we just verify Python syntax
            result = subprocess.run(
                ["python3", "-m", "py_compile", "apps/unified_search_app.py"],
                cwd=self.repo_root,
                capture_output=True,
                text=True,
                timeout=10
            )

            if result.returncode == 0:
                self.passes.append("unified_search_app.py syntax valid")
            else:
                self.errors.append(f"unified_search_app.py syntax error: {result.stderr[:200]}")

        except subprocess.TimeoutExpired:
            self.errors.append("unified_search_app.py syntax check timed out")
        except Exception as e:
            self.errors.append(f"Error checking unified_search_app.py syntax: {e}")

    def _test_deep_research_import(self):
        """Test that core research engine can be imported."""
        print("Testing research.deep_research import...")

        try:
            from research.deep_research import SimpleDeepResearch
            self.passes.append("SimpleDeepResearch imports successfully")

            # Verify it can be instantiated (doesn't require API keys)
            try:
                engine = SimpleDeepResearch(
                    max_tasks=1,
                    max_time_minutes=1,
                    save_output=False
                )
                self.passes.append("SimpleDeepResearch instantiates successfully")
            except Exception as e:
                self.warnings.append(f"SimpleDeepResearch instantiation issue: {e}")

        except ImportError as e:
            self.errors.append(f"Cannot import SimpleDeepResearch: {e}")
        except Exception as e:
            self.errors.append(f"Error testing SimpleDeepResearch: {e}")

    def _test_config_loader(self):
        """Test that config_loader works."""
        print("Testing config_loader...")

        try:
            from config_loader import config

            # Verify config can be accessed
            raw_config = config.get_raw_config()

            if not raw_config:
                self.warnings.append("config.get_raw_config() returned empty dict")
            else:
                self.passes.append("config_loader loads successfully")

            # Check for deep_research section
            deep_config = raw_config.get("research", {}).get("deep_research", {})

            if not deep_config:
                self.warnings.append("config.yaml missing research.deep_research section")
            else:
                self.passes.append("config.yaml has deep_research configuration")

        except ImportError as e:
            self.errors.append(f"Cannot import config_loader: {e}")
        except Exception as e:
            self.errors.append(f"Error testing config_loader: {e}")

    def _print_results(self):
        """Print test results."""
        print(f"\n{'='*80}")
        print("TEST RESULTS")
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
            print("❌ SMOKE TESTS FAILED")
        else:
            print("✅ SMOKE TESTS PASSED")
        print(f"{'='*80}\n")


if __name__ == "__main__":
    tester = EntryPointTester()
    passed = tester.test_all()
    sys.exit(0 if passed else 1)
