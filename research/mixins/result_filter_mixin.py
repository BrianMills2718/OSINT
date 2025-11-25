#!/usr/bin/env python3
"""
Result filtering mixin for deep research.

Provides result validation and filtering capabilities.
Extracted from SimpleDeepResearch to reduce god class complexity.
"""

import json
import logging
from datetime import datetime, timedelta, timezone
from typing import Dict, List, Tuple, TYPE_CHECKING

from core.prompt_loader import render_prompt
from config_loader import config
from llm_utils import acompletion

if TYPE_CHECKING:
    from research.deep_research import SimpleDeepResearch

logger = logging.getLogger(__name__)


class ResultFilterMixin:
    """
    Mixin providing result validation and filtering.

    Requires host class to have:
        - self._emit_progress(event_type: str, message: str, task_id=None, data=None): method
    """

    async def _validate_result_relevance(
        self: "SimpleDeepResearch",
        task_query: str,
        research_question: str,
        sample_results: List[Dict]
    ) -> Tuple[bool, str, List[int], bool, str, Dict]:
        """
        Validate result relevance, filter to best results, and decide if more searching needed.

        LLM makes decisions: ACCEPT/REJECT, which indices to keep, continue searching?, reasoning breakdown

        Args:
            task_query: Query that generated these results
            research_question: Original research question
            sample_results: All results to evaluate (Gemini 2.5 Flash has 65K token context)

        Returns:
            Tuple of (should_accept, reason, relevant_indices, should_continue, continuation_reason, reasoning_breakdown):
            - should_accept: True to ACCEPT results, False to REJECT
            - reason: LLM's explanation for accept/reject decision
            - relevant_indices: List of result indices to keep (e.g., [0, 2, 5])
            - should_continue: True to search for more results, False to stop
            - continuation_reason: LLM's explanation for continue/stop decision
            - reasoning_breakdown: Dict with filtering_strategy, interesting_decisions, patterns_noticed
        """
        if not sample_results:
            return (False, "No results to evaluate", [], False, "No results to evaluate", {})

        # Build numbered sample text (Result #0, Result #1, etc.)
        results_text = "\n\n".join([
            f"Result #{i}:\nTitle: {r.get('title', '')}\nSnippet: {r.get('snippet', r.get('description', ''))[:200]}"
            for i, r in enumerate(sample_results)
        ])

        prompt = render_prompt(
            "deep_research/relevance_evaluation.j2",
            research_question=research_question,
            task_query=task_query,
            results_text=results_text
        )

        schema = {
            "type": "object",
            "properties": {
                "decision": {
                    "type": "string",
                    "enum": ["ACCEPT", "REJECT"],
                    "description": "Decision: ACCEPT if any results relevant, REJECT if all off-topic"
                },
                "reason": {
                    "type": "string",
                    "description": "Brief explanation of accept/reject decision"
                },
                "relevant_indices": {
                    "type": "array",
                    "items": {"type": "integer"},
                    "description": "List of result indices to keep (e.g., [0, 2, 5]). Empty list if REJECT."
                },
                "continue_searching": {
                    "type": "boolean",
                    "description": "true = search for more results, false = sufficient coverage"
                },
                "continuation_reason": {
                    "type": "string",
                    "description": "Brief explanation of why to continue or stop searching"
                },
                "reasoning_breakdown": {
                    "type": "object",
                    "properties": {
                        "filtering_strategy": {
                            "type": "string",
                            "description": "Overall approach to filtering this batch"
                        },
                        "interesting_decisions": {
                            "type": "array",
                            "items": {
                                "type": "object",
                                "properties": {
                                    "result_index": {"type": "integer"},
                                    "action": {
                                        "type": "string",
                                        "enum": ["kept", "rejected"]
                                    },
                                    "reasoning": {"type": "string"}
                                },
                                "required": ["result_index", "action", "reasoning"],
                                "additionalProperties": False
                            }
                        },
                        "patterns_noticed": {
                            "type": "string",
                            "description": "Patterns or trends observed across results"
                        }
                    },
                    "required": ["filtering_strategy", "interesting_decisions", "patterns_noticed"],
                    "additionalProperties": False
                }
            },
            "required": ["decision", "reason", "relevant_indices", "continue_searching", "continuation_reason", "reasoning_breakdown"],
            "additionalProperties": False
        }

        try:
            response = await acompletion(
                model=config.get_model("analysis"),
                messages=[{"role": "user", "content": prompt}],
                response_format={
                    "type": "json_schema",
                    "json_schema": {
                        "strict": True,
                        "name": "relevance_validation",
                        "schema": schema
                    }
                }
            )

            result = json.loads(response.choices[0].message.content)
            decision = result.get("decision", "REJECT")
            reason = result.get("reason", "")
            relevant_indices = result.get("relevant_indices", [])
            should_continue = result.get("continue_searching", True)
            continuation_reason = result.get("continuation_reason", "")
            reasoning_breakdown = result.get("reasoning_breakdown", {})

            should_accept = (decision == "ACCEPT")

            logger.info(f"Result relevance: {decision} - {reason}")
            logger.info(f"Filtered indices: {relevant_indices} ({len(relevant_indices)} results kept)")
            logger.info(f"Continue searching: {should_continue} - {continuation_reason}")
            # Emit reasoning trace for transparency
            self._emit_progress(
                "relevance_scoring",
                f"Decision: {decision}",
                data={
                    "reason": reason,
                    "relevant_indices": relevant_indices,
                    "continue_searching": should_continue,
                    "continuation_reason": continuation_reason,
                    "reasoning_breakdown": reasoning_breakdown
                }
            )

            return (should_accept, reason, relevant_indices, should_continue, continuation_reason, reasoning_breakdown)

        # Exception caught - error logged, execution continues
        except Exception as e:
            logger.error(f"Relevance validation failed: {type(e).__name__}: {str(e)}", exc_info=True)
            # On error, assume relevant and keep all results (don't want to fail good results)
            # But still allow continuation to try finding better results
            all_indices = list(range(len(sample_results)))
            return (True, f"Error during validation: {type(e).__name__}", all_indices, True, "Error during validation", {})

    def _validate_result_dates(self: "SimpleDeepResearch", results: List[Dict]) -> List[Dict]:
        """
        Validate and filter results with suspicious dates.

        Rejects results with future dates (accounting for timezone differences).
        Adds warning flags for borderline cases.

        Args:
            results: List of result dicts

        Returns:
            Filtered list with valid dates, suspicious results flagged

        Added: 2025-11-18 (Codex recommendation)
        """
        # Timezone buffer: Allow dates up to 1 day in future (accounts for UTC offsets)
        now = datetime.now(timezone.utc)
        max_valid_date = now + timedelta(days=1)

        validated_results = []
        rejected_count = 0

        for result in results:
            # Check various date fields
            date_str = result.get('published_date') or result.get('date') or result.get('age')

            if not date_str:
                # No date found - keep result but flag
                result['_date_warning'] = 'no_date_found'
                validated_results.append(result)
                continue

            # Try to parse date from various formats
            future_date_found = False
            try:
                # Common formats: "Nov 17, 2025", "2025-11-17", "November 17, 2025"
                for fmt in ["%b %d, %Y", "%Y-%m-%d", "%B %d, %Y", "%Y/%m/%d"]:
                    try:
                        # Parse and make timezone-aware (assume UTC for comparison)
                        parsed_date = datetime.strptime(date_str.strip(), fmt).replace(tzinfo=timezone.utc)
                        if parsed_date > max_valid_date:
                            future_date_found = True
                            break
                    except ValueError:
                        continue
            # Date validation failure - non-critical, flag and include result
            except Exception as e:
                # Date parsing failed - keep result but flag
                logger.warning(f"Date validation failed for result: {e}", exc_info=True)
                result['_date_warning'] = 'date_parse_failed'
                validated_results.append(result)
                continue

            if future_date_found:
                # Reject future-dated result
                rejected_count += 1
                logger.warning(
                    f"Rejected result with future date: '{date_str}' in '{result.get('title', 'Unknown')}' "
                    f"(source: {result.get('source', 'Unknown')})"
                )
                continue

            # Valid date - keep result
            validated_results.append(result)

        if rejected_count > 0:
            logger.info(f"Date validation: Rejected {rejected_count}/{len(results)} results with future dates")

        return validated_results
