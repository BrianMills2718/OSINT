#!/usr/bin/env python3
"""
Intelligent Executor - Complete AI Research Assistant.

Combines all 7 phases:
Phase 1-3: Search (relevance, generation, execution) - from ParallelExecutor
Phase 4-5: Refinement (evaluate, refine) - from AgenticExecutor
Phase 6: Analysis (quantitative + qualitative) - from ResultAnalyzer
Phase 7: Synthesis (coherent answer) - from ResultAnalyzer

Usage:
    executor = IntelligentExecutor()
    response = await executor.research(
        research_question="What cybersecurity trends are emerging in government contracting?",
        databases=[...],
        api_keys={...}
    )

    # response contains:
    # - search_results: Raw results from databases
    # - analysis: Quantitative + qualitative insights
    # - answer: Synthesized answer to question
"""

import uuid
from typing import Dict, List
from datetime import datetime

from core.agentic_executor import AgenticExecutor
from core.result_analyzer import ResultAnalyzer
from core.database_integration_base import DatabaseIntegration


class IntelligentExecutor:
    """
    Complete AI research assistant combining search, refinement, analysis, and synthesis.

    This is the full implementation of:
    "explain my research question and have the LLM be able to intelligently search
    across databases and collect and analyze the data and refine its searches"
    """

    def __init__(self, max_concurrent=None, max_refinements=None, llm_model=None):
        """
        Initialize the intelligent executor.

        Args:
            max_concurrent: Max parallel API calls
            max_refinements: Max refinement iterations
            llm_model: LLM model for analysis and synthesis
        """
        self.executor = AgenticExecutor(
            max_concurrent=max_concurrent,
            max_refinements=max_refinements
        )
        self.analyzer = ResultAnalyzer(llm_model=llm_model)
        self.session_id = str(uuid.uuid4())[:8]

    async def research(self,
                      research_question: str,
                      databases: List[DatabaseIntegration],
                      api_keys: Dict[str, str],
                      limit: int = 10,
                      analyze: bool = True) -> Dict:
        """
        Execute complete research workflow.

        Args:
            research_question: The research question to answer
            databases: List of databases to search
            api_keys: API keys for databases
            limit: Max results per database
            analyze: If True, perform Phase 6-7 (analysis + synthesis)

        Returns:
            Dict with complete research results:
            {
                "question": "...",
                "search_results": {...},  # Phase 1-5 results
                "analysis": {...},        # Phase 6 results
                "answer": {...},          # Phase 7 results
                "metadata": {...}
            }
        """

        print("🧠 Intelligent Research Assistant")
        print("=" * 80)
        print(f"Question: {research_question}")
        print(f"Session: {self.session_id}")
        print("=" * 80)

        overall_start = datetime.now()

        # Phase 1-5: Search and Refine (Agentic Executor)
        print(f"\n📚 Phase 1-5: Intelligent Search")
        search_results = await self.executor.execute_all(
            research_question=research_question,
            databases=databases,
            api_keys=api_keys,
            limit=limit
        )

        response = {
            "question": research_question,
            "session_id": self.session_id,
            "search_results": search_results,
            "metadata": {
                "start_time": overall_start.isoformat(),
                "databases_searched": len(databases)
            }
        }

        # Check if we got any results
        successful_results = {k: v for k, v in search_results.items() if v.success and v.total > 0}

        if not successful_results:
            print("\n⚠️  No results found across any database")
            response["analysis"] = {
                "quantitative": {"total_results": 0, "databases": 0},
                "qualitative": {
                    "key_findings": ["No results found"],
                    "confidence": "low"
                }
            }
            response["answer"] = {
                "answer": f"No results were found for the research question: '{research_question}'. This could mean the query was too specific, the databases don't contain relevant information, or there may be API issues.",
                "summary": "No results found.",
                "evidence": [],
                "limitations": ["No data available"]
            }

            overall_time = (datetime.now() - overall_start).total_seconds()
            response["metadata"]["total_time_seconds"] = overall_time
            return response

        # Phase 6-7: Analysis and Synthesis (if requested)
        if analyze:
            print(f"\n🔬 Phase 6-7: Analysis & Synthesis")

            # Phase 6: Analyze
            analysis = await self.analyzer.analyze_results(
                results=search_results,
                research_question=research_question
            )
            response["analysis"] = analysis

            # Phase 7: Synthesize
            answer = await self.analyzer.synthesize_answer(
                analysis=analysis,
                research_question=research_question
            )
            response["answer"] = answer

        else:
            print(f"\n⊘ Skipping analysis (analyze=False)")

        # Final timing
        overall_time = (datetime.now() - overall_start).total_seconds()
        response["metadata"]["total_time_seconds"] = overall_time

        print(f"\n✓ Research complete in {overall_time:.1f}s")
        print("=" * 80)

        return response

    def format_answer(self, response: Dict) -> str:
        """
        Format research response as human-readable text.

        Args:
            response: Response from research()

        Returns:
            Formatted string
        """

        output = []
        output.append("=" * 80)
        output.append("RESEARCH RESULTS")
        output.append("=" * 80)
        output.append(f"\nQuestion: {response['question']}")

        # Search Results Summary
        output.append(f"\n{'=' * 80}")
        output.append("SEARCH RESULTS")
        output.append("=" * 80)

        if "search_results" in response:
            for db_id, result in response["search_results"].items():
                if result.success:
                    output.append(f"\n{result.source}:")
                    output.append(f"  ✓ Found {result.total:,} results")
                    output.append(f"  ⏱ Response time: {result.response_time_ms:.0f}ms")
                else:
                    output.append(f"\n{result.source}:")
                    output.append(f"  ✗ Failed: {result.error}")

        # Analysis
        if "analysis" in response:
            analysis = response["analysis"]
            quant = analysis.get("quantitative", {})
            qual = analysis.get("qualitative", {})

            output.append(f"\n{'=' * 80}")
            output.append("ANALYSIS")
            output.append("=" * 80)

            # Quantitative
            output.append(f"\n📊 Quantitative:")
            output.append(f"  Total Results: {quant.get('total_results', 0):,}")
            output.append(f"  Databases: {quant.get('databases', 0)}")

            # Adaptive (code-generated)
            if "adaptive" in analysis and analysis["adaptive"].get("success"):
                adaptive = analysis["adaptive"]
                output.append(f"\n🤖 Adaptive Analysis (Code-Generated):")
                for insight in adaptive.get("insights", []):
                    output.append(f"    • {insight}")

            # Qualitative
            output.append(f"\n🔍 Qualitative Insights:")

            if "key_findings" in qual:
                output.append(f"\n  Key Findings:")
                for finding in qual["key_findings"]:
                    output.append(f"    • {finding}")

            if "patterns" in qual and qual["patterns"]:
                output.append(f"\n  Patterns:")
                for pattern in qual["patterns"]:
                    output.append(f"    • {pattern}")

            if "surges" in qual and qual["surges"]:
                output.append(f"\n  Surges/Anomalies:")
                for surge in qual["surges"]:
                    output.append(f"    • {surge['type']}: {surge['value']} - {surge['significance']}")

            output.append(f"\n  Confidence: {qual.get('confidence', 'unknown').upper()}")

        # Answer
        if "answer" in response:
            answer = response["answer"]

            output.append(f"\n{'=' * 80}")
            output.append("ANSWER")
            output.append("=" * 80)

            output.append(f"\n{answer.get('answer', 'No answer available')}")

            if "evidence" in answer and answer["evidence"]:
                output.append(f"\n\nEvidence:")
                for evidence in answer["evidence"]:
                    output.append(f"  • {evidence}")

            if "limitations" in answer and answer["limitations"]:
                output.append(f"\n\nLimitations:")
                for limitation in answer["limitations"]:
                    output.append(f"  • {limitation}")

        # Metadata
        metadata = response.get("metadata", {})
        output.append(f"\n{'=' * 80}")
        output.append(f"Session: {response.get('session_id', 'N/A')}")
        output.append(f"Time: {metadata.get('total_time_seconds', 0):.1f}s")
        output.append("=" * 80)

        return "\n".join(output)
