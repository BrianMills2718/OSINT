#!/usr/bin/env python3
"""
Result Analyzer - Phase 6 & 7 of intelligent search.

Phase 6: Analyze collected results (quantitative + qualitative)
Phase 7: Synthesize coherent answer to research question

Enables:
- Trend detection (surge in job postings by location/position/clearance)
- Distribution analysis (where are most jobs? what skills dominate?)
- Comparative analysis (more/less than baseline?)
- Natural language synthesis (coherent answer to user's question)
"""

import json
from typing import Dict, List, Any, Optional
from datetime import datetime
from collections import Counter
from llm_utils import acompletion

from database_integration_base import QueryResult
from api_request_tracker import log_request
from config_loader import config
from adaptive_analyzer import AdaptiveAnalyzer


class ResultAnalyzer:
    """
    Analyzes search results across multiple databases and synthesizes answers.

    Usage:
        analyzer = ResultAnalyzer()

        # Phase 6: Analyze
        analysis = await analyzer.analyze_results(
            results=query_results,
            research_question="What cybersecurity trends are emerging?"
        )

        # Phase 7: Synthesize
        answer = await analyzer.synthesize_answer(
            analysis=analysis,
            research_question="What cybersecurity trends are emerging?"
        )
    """

    def __init__(self, llm_model=None, enable_adaptive=True):
        """
        Initialize the result analyzer.

        Args:
            llm_model: LLM model to use for qualitative analysis and synthesis
            enable_adaptive: Enable adaptive code-based analysis (Ditto-style)
        """
        self.llm_model = llm_model or config.get_model("analysis")
        self.enable_adaptive = enable_adaptive
        if enable_adaptive:
            self.adaptive_analyzer = AdaptiveAnalyzer(llm_model=llm_model)

    async def analyze_results(self,
                             results: Dict[str, QueryResult],
                             research_question: str) -> Dict[str, Any]:
        """
        Phase 6: Analyze collected results.

        Performs both quantitative and qualitative analysis on results
        from all databases.

        Args:
            results: Dict mapping database ID to QueryResult
            research_question: Original research question

        Returns:
            Dict with analysis results:
            {
                "quantitative": {...},  # Stats, counts, distributions, trends
                "qualitative": {...},   # LLM interpretation
                "databases_analyzed": [...]
            }
        """

        print(f"  Phase 6: Analyzing results...")

        # Quantitative analysis (fast, deterministic)
        quant = self._quantitative_analysis(results)
        print(f"    ✓ Quantitative: {quant['total_results']:,} results across {quant['databases']} databases")

        # Adaptive analysis (Ditto-style code generation)
        adaptive = None
        if self.enable_adaptive:
            try:
                adaptive = await self.adaptive_analyzer.analyze(results, research_question)
                if adaptive["success"]:
                    print(f"    ✓ Adaptive: Code-based analysis completed")
                else:
                    print(f"    ⚠️  Adaptive: {adaptive['error']}")
            except Exception as e:
                print(f"    ⚠️  Adaptive analysis failed: {e}")

        # Qualitative analysis (LLM-powered)
        qual = await self._qualitative_analysis(results, research_question, quant, adaptive)
        print(f"    ✓ Qualitative: Key findings identified")

        analysis = {
            "quantitative": quant,
            "qualitative": qual,
            "databases_analyzed": list(results.keys()),
            "timestamp": datetime.now().isoformat()
        }

        # Add adaptive results if available
        if adaptive and adaptive["success"]:
            analysis["adaptive"] = adaptive

        return analysis

    def _quantitative_analysis(self, results: Dict[str, QueryResult]) -> Dict[str, Any]:
        """
        Perform quantitative analysis on results.

        Analyzes:
        - Total result counts by database
        - Field distributions (locations, positions, etc.)
        - Trends and surges (if temporal data available)
        - Statistical summaries

        Args:
            results: Query results from all databases

        Returns:
            Dict with quantitative metrics
        """

        analysis = {
            "total_results": 0,
            "databases": 0,
            "by_database": {},
            "distributions": {},
            "trends": {}
        }

        # Count by database
        for db_id, result in results.items():
            if not result.success:
                continue

            analysis["databases"] += 1
            analysis["total_results"] += result.total

            analysis["by_database"][result.source] = {
                "total": result.total,
                "returned": len(result.results),
                "response_time_ms": result.response_time_ms
            }

            # Analyze distributions in results
            if result.results:
                dist = self._analyze_distributions(result.source, result.results)
                if dist:
                    analysis["distributions"][result.source] = dist

        return analysis

    def _analyze_distributions(self, source: str, results: List[Dict]) -> Optional[Dict]:
        """
        Analyze field distributions in results.

        Detects common patterns:
        - Location distribution (for jobs)
        - Position/title distribution
        - Date/time distribution (for temporal analysis)
        - Clearance level distribution (for security jobs)

        Args:
            source: Database source name
            results: List of result items

        Returns:
            Dict with distribution analysis or None if not enough data
        """

        if len(results) < 3:
            return None

        distributions = {}

        # Common field patterns to analyze
        field_patterns = {
            # Jobs
            "locations": ["location", "city", "state", "locations"],
            "positions": ["job_name", "title", "position", "PositionTitle"],
            "clearances": ["clearance", "security_clearance"],
            "companies": ["company_name", "organization", "OrganizationName"],

            # Media
            "media_types": ["type", "media_type"],
            "branches": ["branch", "military_branch"],

            # Contracts
            "agencies": ["agency", "organizationName", "fullParentPathName"],
            "contract_types": ["type", "procurement_type"],
        }

        for dist_name, possible_fields in field_patterns.items():
            values = []

            for result in results:
                for field in possible_fields:
                    if field in result:
                        value = result[field]

                        # Handle nested structures (e.g., locations array)
                        if isinstance(value, list):
                            for item in value:
                                if isinstance(item, dict) and "location" in item:
                                    values.append(item["location"])
                                elif isinstance(item, str):
                                    values.append(item)
                        elif isinstance(value, str) and value:
                            values.append(value)
                        break  # Found the field, don't check others

            if values:
                # Count occurrences
                counter = Counter(values)
                top_10 = counter.most_common(10)

                distributions[dist_name] = {
                    "total_unique": len(counter),
                    "top_10": [{"value": v, "count": c} for v, c in top_10],
                    "total_items": len(values)
                }

        return distributions if distributions else None

    async def _qualitative_analysis(self,
                                   results: Dict[str, QueryResult],
                                   research_question: str,
                                   quant: Dict,
                                   adaptive: Optional[Dict] = None) -> Dict[str, Any]:
        """
        Perform LLM-powered qualitative analysis.

        Uses LLM to interpret results and identify:
        - Key findings
        - Patterns and trends
        - Anomalies or surprises
        - Answer to research question

        Args:
            results: Query results
            research_question: Original question
            quant: Quantitative analysis results

        Returns:
            Dict with qualitative insights
        """

        start = datetime.now()

        # Build sample data for LLM (don't send all results, too expensive)
        samples = {}
        for db_id, result in results.items():
            if result.success and result.results:
                # Take top 5 results as sample
                samples[result.source] = result.results[:5]

        # Include adaptive analysis insights if available
        adaptive_section = ""
        if adaptive and adaptive.get("success"):
            adaptive_section = f"""

Adaptive Analysis (Code-Generated Insights):
{chr(10).join(adaptive.get('insights', []))}

Full Analysis Output:
{adaptive.get('output', '')[:2000]}
"""

        prompt = f"""You are a research analyst reviewing search results to answer a research question.

Research Question: "{research_question}"

Quantitative Summary:
- Total results: {quant['total_results']:,}
- Databases searched: {quant['databases']}
- By database: {json.dumps(quant['by_database'], indent=2)}
{adaptive_section}
Sample Results from each database:
{json.dumps(samples, indent=2, default=str)[:5000]}

Your task: Analyze these results and provide insights.

Focus on:
1. **Key Findings**: What are the most important discoveries?
2. **Patterns**: What patterns or trends do you notice?
3. **Surges/Anomalies**: Any unusual concentrations (location, position, time, etc.)?
4. **Answer**: Based on results, what's the answer to the research question?

Return JSON with these fields:
- key_findings (array of strings): 3-5 most important discoveries
- patterns (array of strings): Notable patterns or trends
- surges (array of objects): {{"type": "location/position/etc", "value": "...", "significance": "..."}}
- answer_preview (string): 2-3 sentence answer to research question
- confidence (string): "high" / "medium" / "low" based on result quality/quantity
"""

        schema = {
            "type": "object",
            "properties": {
                "key_findings": {
                    "type": "array",
                    "items": {"type": "string"},
                    "description": "3-5 most important discoveries"
                },
                "patterns": {
                    "type": "array",
                    "items": {"type": "string"},
                    "description": "Notable patterns or trends"
                },
                "surges": {
                    "type": "array",
                    "items": {
                        "type": "object",
                        "properties": {
                            "type": {"type": "string"},
                            "value": {"type": "string"},
                            "significance": {"type": "string"}
                        },
                        "required": ["type", "value", "significance"],
                        "additionalProperties": False
                    },
                    "description": "Unusual concentrations or surges"
                },
                "answer_preview": {
                    "type": "string",
                    "description": "2-3 sentence answer preview"
                },
                "confidence": {
                    "type": "string",
                    "enum": ["high", "medium", "low"],
                    "description": "Confidence level in findings"
                }
            },
            "required": ["key_findings", "patterns", "surges", "answer_preview", "confidence"],
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
                        "name": "qualitative_analysis",
                        "schema": schema
                    }
                }
            )

            duration_ms = (datetime.now() - start).total_seconds() * 1000

            # Log LLM call
            log_request(
                api_name="QualitativeAnalysis",
                endpoint="LLM",
                status_code=200,
                response_time_ms=duration_ms,
                error_message=None,
                request_params={"question_length": len(research_question)}
            )

            return json.loads(response.choices[0].message.content)

        except Exception as e:
            print(f"    ⚠️  Qualitative analysis failed: {e}")
            return {
                "key_findings": ["Analysis unavailable"],
                "patterns": [],
                "surges": [],
                "answer_preview": "Unable to generate analysis",
                "confidence": "low"
            }

    async def synthesize_answer(self,
                               analysis: Dict[str, Any],
                               research_question: str) -> Dict[str, Any]:
        """
        Phase 7: Synthesize coherent answer to research question.

        Takes analysis from Phase 6 and generates a comprehensive,
        well-structured answer.

        Args:
            analysis: Analysis from Phase 6
            research_question: Original research question

        Returns:
            Dict with synthesized answer:
            {
                "answer": "...",  # Comprehensive answer
                "summary": "...", # One-paragraph summary
                "evidence": [...], # Supporting evidence
                "recommendations": [...] # Next steps (optional)
            }
        """

        print(f"  Phase 7: Synthesizing answer...")

        start = datetime.now()

        quant = analysis["quantitative"]
        qual = analysis["qualitative"]

        prompt = f"""You are a research assistant providing a comprehensive answer to a research question.

Research Question: "{research_question}"

Analysis Results:

Quantitative:
- Total results found: {quant['total_results']:,}
- Databases searched: {quant['databases']}
- Results by database: {json.dumps(quant['by_database'], indent=2)}

Qualitative Insights:
- Key findings: {json.dumps(qual['key_findings'])}
- Patterns: {json.dumps(qual['patterns'])}
- Surges/Anomalies: {json.dumps(qual['surges'])}
- Confidence: {qual['confidence']}

Your task: Synthesize a comprehensive, well-structured answer.

Requirements:
1. **Answer**: 2-4 paragraphs directly answering the question
2. **Summary**: Single paragraph executive summary
3. **Evidence**: List of specific evidence supporting your answer
4. **Confidence**: Explain confidence level and any limitations

Return JSON with:
- answer (string): Full answer, 2-4 paragraphs
- summary (string): Executive summary, 1 paragraph
- evidence (array): Specific evidence points
- limitations (array): What's missing or uncertain
"""

        schema = {
            "type": "object",
            "properties": {
                "answer": {
                    "type": "string",
                    "description": "Comprehensive answer, 2-4 paragraphs"
                },
                "summary": {
                    "type": "string",
                    "description": "Executive summary, 1 paragraph"
                },
                "evidence": {
                    "type": "array",
                    "items": {"type": "string"},
                    "description": "Specific evidence supporting answer"
                },
                "limitations": {
                    "type": "array",
                    "items": {"type": "string"},
                    "description": "Limitations or uncertainties"
                }
            },
            "required": ["answer", "summary", "evidence", "limitations"],
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
                        "name": "synthesis",
                        "schema": schema
                    }
                }
            )

            duration_ms = (datetime.now() - start).total_seconds() * 1000

            # Log LLM call
            log_request(
                api_name="Synthesis",
                endpoint="LLM",
                status_code=200,
                response_time_ms=duration_ms,
                error_message=None,
                request_params={"question_length": len(research_question)}
            )

            synthesis = json.loads(response.choices[0].message.content)

            print(f"    ✓ Answer synthesized")

            return {
                **synthesis,
                "timestamp": datetime.now().isoformat(),
                "based_on": {
                    "total_results": quant["total_results"],
                    "databases": quant["databases"],
                    "confidence": qual["confidence"]
                }
            }

        except Exception as e:
            print(f"    ⚠️  Synthesis failed: {e}")
            return {
                "answer": qual.get("answer_preview", "Unable to synthesize answer"),
                "summary": qual.get("answer_preview", "Analysis unavailable"),
                "evidence": [],
                "limitations": ["Synthesis process failed"],
                "timestamp": datetime.now().isoformat()
            }
