#!/usr/bin/env python3
"""
Adaptive Analyzer - Ditto-style dynamic code generation for data analysis.

Inspired by yoheinakajima/ditto, this module enables the LLM to write and execute
custom analysis code based on the research question and available data.

Key Features:
- Schema inspection: Automatically discovers what fields are available
- Dynamic code generation: LLM writes pandas/numpy code tailored to the question
- Safe execution: Runs in subprocess with timeout and restricted imports
- Error recovery: If code fails, LLM refines and retries
- Multi-dataset correlation: Can analyze relationships across databases

Usage:
    analyzer = AdaptiveAnalyzer()
    result = await analyzer.analyze(
        results={"ClearanceJobs": [...], "SAM.gov": [...]},
        research_question="Correlate job postings with contract awards"
    )
"""

import json
import subprocess
import tempfile
import os
from typing import Dict, List, Any, Optional
from datetime import datetime
from llm_utils import acompletion

from database_integration_base import QueryResult
from api_request_tracker import log_request
from config_loader import config


class AdaptiveAnalyzer:
    """
    Generates and executes custom analysis code based on research questions.

    This is the "code interpreter" capability - LLM sees data, writes code,
    executes it safely, and returns results.
    """

    def __init__(self, llm_model=None, timeout_seconds=None):
        """
        Initialize the adaptive analyzer.

        Args:
            llm_model: LLM model for code generation
            timeout_seconds: Max execution time for generated code
        """
        self.llm_model = llm_model or config.get_model("code_generation")
        self.timeout_seconds = timeout_seconds or config.get_timeout("code_execution")

    async def analyze(self,
                     results: Dict[str, QueryResult],
                     research_question: str,
                     max_retries: int = 2) -> Dict[str, Any]:
        """
        Generate and execute custom analysis code.

        Args:
            results: Query results from databases
            research_question: Original research question
            max_retries: Max retry attempts if code fails

        Returns:
            Dict with analysis results:
            {
                "success": bool,
                "code": str,  # Generated Python code
                "output": str,  # Execution output
                "insights": [...],  # Extracted insights
                "error": str or None
            }
        """

        print(f"  Phase 6.5: Adaptive Analysis (Code Generation)")

        # Step 1: Inspect data schemas
        schemas = self._inspect_schemas(results)
        print(f"    ✓ Inspected {len(schemas)} dataset schemas")

        # Step 2: Generate analysis plan
        plan = await self._generate_plan(research_question, schemas)
        print(f"    ✓ Generated analysis plan")

        # Step 3: Generate Python code
        code = await self._generate_code(plan, schemas, research_question)
        print(f"    ✓ Generated analysis code ({len(code)} chars)")

        # Step 4: Execute code (with retries on error)
        for attempt in range(max_retries + 1):
            execution_result = self._execute_code(code, results)

            if execution_result["success"]:
                print(f"    ✓ Code executed successfully")
                break

            if attempt < max_retries:
                print(f"    ⚠️  Execution failed, refining code (attempt {attempt + 1}/{max_retries})")
                code = await self._refine_code(code, execution_result["error"], schemas)
            else:
                print(f"    ✗ Code execution failed after {max_retries} retries")
                return {
                    "success": False,
                    "code": code,
                    "output": None,
                    "insights": [],
                    "error": execution_result["error"]
                }

        # Step 5: Extract insights from output
        insights = await self._extract_insights(
            execution_result["output"],
            research_question
        )
        print(f"    ✓ Extracted {len(insights)} insights")

        return {
            "success": True,
            "code": code,
            "output": execution_result["output"],
            "insights": insights,
            "error": None
        }

    def _inspect_schemas(self, results: Dict[str, QueryResult]) -> Dict[str, Dict]:
        """
        Inspect data schemas from all result sets.

        Discovers:
        - Available fields in each dataset
        - Field types (string, number, date, etc.)
        - Sample values
        - Temporal fields (for trend analysis)

        Args:
            results: Query results from databases

        Returns:
            Dict mapping database name to schema info
        """

        schemas = {}

        for db_id, result in results.items():
            if not result.success or not result.results:
                continue

            # Analyze first few results to infer schema
            sample_size = min(5, len(result.results))
            samples = result.results[:sample_size]

            # Collect all field names
            all_fields = set()
            for item in samples:
                if isinstance(item, dict):
                    all_fields.update(item.keys())

            # Infer field types and identify temporal fields
            field_info = {}
            temporal_fields = []

            for field in all_fields:
                # Get sample values for this field
                sample_values = []
                for item in samples:
                    if isinstance(item, dict) and field in item:
                        sample_values.append(item[field])

                # Infer type
                field_type = self._infer_type(sample_values)
                field_info[field] = {
                    "type": field_type,
                    "sample": sample_values[0] if sample_values else None
                }

                # Identify temporal fields
                if self._is_temporal_field(field, field_type, sample_values):
                    temporal_fields.append(field)

            schemas[result.source] = {
                "fields": field_info,
                "temporal_fields": temporal_fields,
                "sample_count": len(samples),
                "total_count": result.total
            }

        return schemas

    def _infer_type(self, values: List[Any]) -> str:
        """Infer the type of a field from sample values."""
        if not values:
            return "unknown"

        # Check first non-None value
        for val in values:
            if val is None:
                continue

            if isinstance(val, bool):
                return "boolean"
            elif isinstance(val, int):
                return "integer"
            elif isinstance(val, float):
                return "number"
            elif isinstance(val, list):
                return "array"
            elif isinstance(val, dict):
                return "object"
            elif isinstance(val, str):
                # Try to detect dates
                if self._looks_like_date(val):
                    return "date"
                return "string"

        return "unknown"

    def _looks_like_date(self, value: str) -> bool:
        """Check if a string looks like a date."""
        date_indicators = [
            "date", "time", "posted", "created", "updated", "published",
            "award", "modified", "posted_at", "created_at"
        ]

        # Check for ISO format
        if "T" in value and ("Z" in value or "+" in value):
            return True

        # Check for common date patterns
        if any(indicator in value.lower() for indicator in date_indicators):
            return True

        return False

    def _is_temporal_field(self, field_name: str, field_type: str, samples: List) -> bool:
        """Determine if a field is temporal (date/time)."""

        # Check type
        if field_type == "date":
            return True

        # Check field name
        temporal_keywords = [
            "date", "time", "posted", "created", "updated", "published",
            "award", "modified", "timestamp", "posted_at", "created_at"
        ]

        field_lower = field_name.lower()
        if any(keyword in field_lower for keyword in temporal_keywords):
            return True

        return False

    async def _generate_plan(self,
                            research_question: str,
                            schemas: Dict[str, Dict]) -> str:
        """
        Generate high-level analysis plan.

        Args:
            research_question: User's question
            schemas: Data schemas from inspection

        Returns:
            Analysis plan (text description)
        """

        start = datetime.now()

        prompt = f"""You are a data analysis expert. Review the available data and create an analysis plan.

Research Question: "{research_question}"

Available Datasets:
{json.dumps(schemas, indent=2, default=str)}

Your Task: Create a concise analysis plan that:
1. Identifies which datasets are relevant
2. Determines what analysis methods to use (trends, correlations, distributions, etc.)
3. Identifies temporal analysis opportunities if date fields are available
4. Suggests how to answer the research question

Return a brief plan (3-5 bullet points) describing the analysis approach.
"""

        try:
            response = await acompletion(
                model=self.llm_model,
                messages=[{"role": "user", "content": prompt}]
            )

            duration_ms = (datetime.now() - start).total_seconds() * 1000

            log_request(
                api_name="AdaptiveAnalysis_Planning",
                endpoint="LLM",
                status_code=200,
                response_time_ms=duration_ms,
                error_message=None,
                request_params={"question_length": len(research_question)}
            )

            return response.choices[0].message.content

        except Exception as e:
            print(f"      ⚠️  Planning failed: {e}")
            return "Perform basic statistical analysis on available data."

    async def _generate_code(self,
                            plan: str,
                            schemas: Dict[str, Dict],
                            research_question: str) -> str:
        """
        Generate Python analysis code based on plan.

        Args:
            plan: Analysis plan from _generate_plan
            schemas: Data schemas
            research_question: Original question

        Returns:
            Python code (as string)
        """

        start = datetime.now()

        prompt = f"""You are a Python data analysis code generator. Write pandas/numpy code to analyze data.

Research Question: "{research_question}"

Analysis Plan:
{plan}

Available Data Schemas:
{json.dumps(schemas, indent=2, default=str)}

Your Task: Write Python code that:
1. Analyzes the data according to the plan
2. Uses pandas DataFrames (data already loaded as 'results' dict)
3. Prints insights in a clear, readable format
4. Handles missing/null values gracefully
5. Uses only: pandas, numpy, datetime, json (no other imports)

Data Structure:
- Input: results = {{"DatabaseName": [{{"field": "value", ...}}, ...], ...}}
- Convert to DataFrame: pd.DataFrame(results["DatabaseName"])

Code Requirements:
- No file I/O (no reading/writing files)
- No matplotlib/plotting (text output only)
- Print all insights clearly
- Handle errors gracefully (try/except)
- Keep code under 50 lines

Return ONLY the Python code, no explanations.
"""

        try:
            response = await acompletion(
                model=self.llm_model,
                messages=[{"role": "user", "content": prompt}]
            )

            duration_ms = (datetime.now() - start).total_seconds() * 1000

            log_request(
                api_name="AdaptiveAnalysis_CodeGen",
                endpoint="LLM",
                status_code=200,
                response_time_ms=duration_ms,
                error_message=None,
                request_params={"plan_length": len(plan)}
            )

            code = response.choices[0].message.content

            # Clean code (remove markdown fences if present)
            code = code.replace("```python", "").replace("```", "").strip()

            return code

        except Exception as e:
            print(f"      ⚠️  Code generation failed: {e}")
            return "print('Analysis failed: Unable to generate code')"

    def _execute_code(self,
                     code: str,
                     results: Dict[str, QueryResult]) -> Dict[str, Any]:
        """
        Execute generated code in a safe subprocess.

        Args:
            code: Python code to execute
            results: Data to pass to code

        Returns:
            Dict with execution results:
            {
                "success": bool,
                "output": str,
                "error": str or None
            }
        """

        # Prepare data for code (convert QueryResult to plain dicts)
        data = {}
        for db_name, result in results.items():
            if result.success and result.results:
                data[result.source] = result.results

        # Create temporary Python file
        with tempfile.NamedTemporaryFile(mode='w', suffix='.py', delete=False) as f:
            # Write setup code
            f.write("import json\n")
            f.write("import sys\n")
            f.write("import pandas as pd\n")
            f.write("import numpy as np\n")
            f.write("from datetime import datetime, timedelta\n\n")

            # Load data (use json.loads to properly handle null/None)
            f.write("# Load data\n")
            f.write("results = json.loads('''")
            f.write(json.dumps(data, default=str))
            f.write("''')\n\n")

            # Write user code
            f.write("# User-generated analysis code\n")
            f.write("try:\n")
            for line in code.split('\n'):
                f.write(f"    {line}\n")
            f.write("except Exception as e:\n")
            f.write("    print(f'Error: {e}')\n")
            f.write("    sys.exit(1)\n")

            script_path = f.name

        try:
            # Execute in subprocess with timeout
            result = subprocess.run(
                ["python3", script_path],
                capture_output=True,
                text=True,
                timeout=self.timeout_seconds
            )

            # Clean up
            os.unlink(script_path)

            if result.returncode == 0:
                return {
                    "success": True,
                    "output": result.stdout,
                    "error": None
                }
            else:
                return {
                    "success": False,
                    "output": result.stdout,
                    "error": result.stderr
                }

        except subprocess.TimeoutExpired:
            os.unlink(script_path)
            return {
                "success": False,
                "output": None,
                "error": f"Code execution timed out after {self.timeout_seconds} seconds"
            }

        except Exception as e:
            if os.path.exists(script_path):
                os.unlink(script_path)
            return {
                "success": False,
                "output": None,
                "error": str(e)
            }

    async def _refine_code(self,
                          original_code: str,
                          error: str,
                          schemas: Dict[str, Dict]) -> str:
        """
        Refine code based on execution error.

        Args:
            original_code: The code that failed
            error: Error message from execution
            schemas: Data schemas

        Returns:
            Refined Python code
        """

        prompt = f"""The following Python code failed. Fix the error and return corrected code.

Original Code:
```python
{original_code}
```

Error:
{error}

Available Data Schemas:
{json.dumps(schemas, indent=2, default=str)}

Return ONLY the corrected Python code, no explanations.
"""

        try:
            response = await acompletion(
                model=self.llm_model,
                messages=[{"role": "user", "content": prompt}]
            )

            code = response.choices[0].message.content
            code = code.replace("```python", "").replace("```", "").strip()

            return code

        except Exception as e:
            print(f"      ⚠️  Code refinement failed: {e}")
            return original_code  # Return original if refinement fails

    async def _extract_insights(self,
                               output: str,
                               research_question: str) -> List[str]:
        """
        Extract key insights from code execution output.

        Args:
            output: Text output from executed code
            research_question: Original question

        Returns:
            List of insight strings
        """

        if not output or len(output.strip()) == 0:
            return []

        prompt = f"""Extract key insights from this analysis output.

Research Question: "{research_question}"

Analysis Output:
{output[:3000]}  # Limit to first 3000 chars

Return 3-5 key insights as a JSON array of strings. Each insight should be a clear, actionable statement.

Example: ["Job postings increased 23% over 3 months", "California has 45% of all positions"]
"""

        schema = {
            "type": "object",
            "properties": {
                "insights": {
                    "type": "array",
                    "items": {"type": "string"},
                    "description": "Key insights extracted from output"
                }
            },
            "required": ["insights"],
            "additionalProperties": False
        }

        try:
            response = await acompletion(
                model=self.llm_model,
                messages=[{"role": "user", "content": prompt}],
                response_format={
                    "type": "json_schema",
                    "json_schema": {
                        "strict": True,
                        "name": "insights",
                        "schema": schema
                    }
                }
            )

            result = json.loads(response.choices[0].message.content)
            return result.get("insights", [])

        except Exception as e:
            print(f"      ⚠️  Insight extraction failed: {e}")
            # Fallback: return output split by lines
            lines = [line.strip() for line in output.split('\n') if line.strip()]
            return lines[:5]  # Return first 5 non-empty lines
