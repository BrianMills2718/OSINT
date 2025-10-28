"""
Scoping Agent

Transforms user queries into structured research briefs with clarification and planning.

Key Features:
- Conservative clarification (only for vague queries)
- Deterministic brief schema (Pydantic validation)
- Prevents scope creep (max subtasks enforced)
- Direct passthrough for simple queries

Architecture:
- needs_clarification(): Decides if query needs clarification
- generate_brief(): Creates structured ResearchBrief from query
"""

import json
import logging
from typing import Dict, Optional
from schemas.research_brief import ResearchBrief, SubQuestion
from llm_utils import acompletion_with_role


class ScopingAgent:
    """
    Generate structured research briefs from user queries.

    Conservative approach: only clarify vague queries, keep simple queries simple.
    """

    def __init__(self, config: Optional[Dict] = None):
        """
        Initialize ScopingAgent with configuration.

        Args:
            config: Configuration dict with keys:
                - max_subtasks: Max sub-questions per brief (default: 5)
                - auto_clarify_threshold: Confidence score to skip clarification (default: 0.7)
        """
        config = config or {}
        self.max_subtasks = config.get('max_subtasks', 5)
        self.auto_clarify_threshold = config.get('auto_clarify_threshold', 0.7)

        logging.info(
            f"ScopingAgent initialized: max_subtasks={self.max_subtasks}, "
            f"auto_clarify_threshold={self.auto_clarify_threshold}"
        )

    async def needs_clarification(self, query: str) -> bool:
        """
        Determine if query needs clarification.

        Conservative heuristics:
        - Queries > 15 words assumed clear
        - Use LLM to judge clarity (0-1 scale)

        Args:
            query: User's research query

        Returns:
            True if clarification needed, False otherwise
        """
        # Heuristic: long queries are usually clear
        if len(query.split()) > 15:
            logging.debug(f"Query length {len(query.split())} > 15 words, skipping clarification")
            return False

        # Use LLM to judge clarity
        try:
            response = await acompletion_with_role(
                role="scoping",
                messages=[{
                    "role": "system",
                    "content": (
                        "Rate the clarity of this research query on a 0-1 scale.\n"
                        "1.0 = perfectly clear, specific, actionable\n"
                        "0.0 = vague, ambiguous, needs clarification\n\n"
                        "Examples:\n"
                        "- 'What is SAM.gov?' → 1.0 (clear)\n"
                        "- 'Tell me about AI security' → 0.3 (vague)\n"
                        "- 'Map defense contractor AI relationships' → 0.9 (clear enough)\n\n"
                        "Return ONLY a number between 0.0 and 1.0, nothing else."
                    )
                }, {
                    "role": "user",
                    "content": query
                }]
                # Note: gpt-5-mini doesn't support temperature or max_tokens
            )

            clarity_score_str = response.choices[0].message.content.strip()
            clarity_score = float(clarity_score_str)

            needs_clarify = clarity_score < self.auto_clarify_threshold

            logging.info(
                f"Query clarity score: {clarity_score:.2f} "
                f"(threshold: {self.auto_clarify_threshold}, "
                f"needs_clarification: {needs_clarify})"
            )

            return needs_clarify

        except Exception as e:
            logging.warning(f"Clarity scoring failed: {e}, assuming query is clear")
            return False  # Conservative: assume clear on error

    async def generate_brief(self, query: str) -> ResearchBrief:
        """
        Generate structured research brief from query.

        Key constraints (Codex-approved):
        - Only decompose complex queries
        - Stay focused on actual ask (no side quests)
        - Simple queries → 1 sub-question (original query)
        - Max subtasks enforced via config

        Args:
            query: User's research query

        Returns:
            Validated ResearchBrief
        """
        # System prompt with strict constraints
        system_prompt = """You are a research planning assistant. Generate a structured research brief.

CRITICAL CONSTRAINTS:
- Only decompose if query is genuinely complex (multiple aspects/questions)
- Sub-questions must be DIRECTLY related to the objective
- Do NOT invent side quests or expand scope beyond user's ask
- Simple queries (< 15 words, single topic) should have 1 sub-question (the original query verbatim)
- Complex queries can have 2-5 sub-questions

For SIMPLE queries like "What is SAM.gov?" or "Who is hiring for AI security?":
- Objective: Restate the query as a clear objective
- Sub-questions: 1 question (original query verbatim)
- Suggested categories: Best source category for this query

For COMPLEX queries like "Map defense contractor AI security relationships":
- Objective: Summarize the overall research goal (1-2 sentences)
- Sub-questions: 2-5 focused questions that together address the objective
- Each sub-question:
  - question: Specific, answerable question
  - rationale: Brief explanation (why this matters, max 150 chars)
  - suggested_categories: 1-3 source categories (e.g., "government_contracts", "social_media", "jobs")

Available source categories:
- government_contracts: SAM.gov (federal contracts/procurement)
- government_jobs: USAJobs, ClearanceJobs (federal job postings)
- government_media: DVIDS, FBI Vault (military media, FBI documents)
- social_media: Twitter, Discord, Reddit (community discussions)
- web_search: Brave Search (general web search)

Return valid JSON matching this schema."""

        # Get Pydantic schema for structured output
        # Remove optional fields from schema that LLM generates
        # (we'll compute estimates after generation)
        brief_schema = {
            "type": "object",
            "properties": {
                "objective": {
                    "type": "string",
                    "maxLength": 500,
                    "description": "1-2 sentence research objective"
                },
                "sub_questions": {
                    "type": "array",
                    "minItems": 1,
                    "maxItems": 10,
                    "items": {
                        "type": "object",
                        "properties": {
                            "question": {
                                "type": "string",
                                "maxLength": 500
                            },
                            "rationale": {
                                "type": "string",
                                "maxLength": 200
                            },
                            "suggested_categories": {
                                "type": "array",
                                "minItems": 1,
                                "maxItems": 5,
                                "items": {"type": "string"}
                            }
                        },
                        "required": ["question", "rationale", "suggested_categories"],
                        "additionalProperties": False
                    }
                }
            },
            "required": ["objective", "sub_questions"],
            "additionalProperties": False
        }

        try:
            response = await acompletion_with_role(
                role="scoping",
                messages=[
                    {"role": "system", "content": system_prompt},
                    {"role": "user", "content": f"Generate research brief for: {query}"}
                ],
                response_format={
                    "type": "json_schema",
                    "json_schema": {
                        "strict": True,
                        "name": "research_brief",
                        "schema": brief_schema
                    }
                }
                # Note: gpt-5-mini doesn't support temperature parameter
            )

            brief_data = json.loads(response.choices[0].message.content)
            brief = ResearchBrief(**brief_data)

            # Enforce max_subtasks constraint
            if len(brief.sub_questions) > self.max_subtasks:
                logging.warning(
                    f"LLM generated {len(brief.sub_questions)} subtasks, "
                    f"truncating to {self.max_subtasks}"
                )
                brief.sub_questions = brief.sub_questions[:self.max_subtasks]

            # Estimate cost and time (rough heuristics)
            num_sources_estimate = sum(len(sq.suggested_categories) for sq in brief.sub_questions)
            brief.estimated_cost = num_sources_estimate * 0.15  # $0.15 per source call (rough)
            brief.estimated_time = num_sources_estimate * 10    # 10s per source call (rough)

            logging.info(
                f"Generated research brief: {len(brief.sub_questions)} subtasks, "
                f"~{num_sources_estimate} sources, "
                f"~${brief.estimated_cost:.2f}, "
                f"~{brief.estimated_time}s"
            )

            return brief

        except Exception as e:
            logging.error(f"Brief generation failed: {e}", exc_info=True)

            # Fallback: create single-question brief from original query
            logging.warning("Falling back to single-question brief")

            # Ensure objective meets min length (20 chars)
            objective = query if len(query) >= 20 else f"Research query: {query}"

            return ResearchBrief(
                objective=objective,
                sub_questions=[
                    SubQuestion(
                        question=query if len(query) >= 10 else f"Answer: {query}",
                        rationale="Direct answer to user query",
                        suggested_categories=["government_contracts", "social_media", "web_search"]
                    )
                ],
                estimated_cost=0.50,
                estimated_time=30
            )

    async def clarify_and_generate(self, query: str) -> ResearchBrief:
        """
        Main entry point: check if clarification needed, then generate brief.

        Phase 1: Clarification not implemented (future work)
        Phase 2: Multi-turn dialogue to refine vague queries

        Args:
            query: User's research query

        Returns:
            Validated ResearchBrief
        """
        # Phase 1: Skip clarification, go straight to brief generation
        # Phase 2: Implement multi-turn clarification dialogue

        needs_clarify = await self.needs_clarification(query)

        if needs_clarify:
            logging.info("Query needs clarification, but Phase 1 skips this (future work)")
            # Future: Implement clarification dialogue here

        return await self.generate_brief(query)
