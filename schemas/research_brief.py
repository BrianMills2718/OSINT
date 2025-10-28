"""
Research Brief Schema

Pydantic models for deterministic research planning and task decomposition.
Used by ScopingAgent and ResearchSupervisor.
"""

from pydantic import BaseModel, Field
from typing import List, Dict, Optional


class SubQuestion(BaseModel):
    """Single subtask in a research plan"""

    question: str = Field(
        ...,
        min_length=10,
        max_length=500,
        description="Specific research sub-question"
    )

    rationale: str = Field(
        ...,
        max_length=200,
        description="Why this subtask matters (brief explanation)"
    )

    suggested_categories: List[str] = Field(
        ...,
        min_items=1,
        max_items=5,
        description="Source categories for routing (e.g., 'government_contracts', 'social_media')"
    )

    estimated_sources: int = Field(
        default=0,
        ge=0,
        description="Number of sources this subtask will query"
    )


class ResearchBrief(BaseModel):
    """Structured research plan generated from user query"""

    objective: str = Field(
        ...,
        min_length=20,
        max_length=500,
        description="1-2 sentence research objective"
    )

    sub_questions: List[SubQuestion] = Field(
        ...,
        min_items=1,
        max_items=10,  # Hard cap, config may set lower
        description="Decomposed research subtasks"
    )

    constraints: Dict[str, str] = Field(
        default_factory=dict,
        description="Research constraints (timeframe, geography, etc.)"
    )

    estimated_cost: float = Field(
        default=0.0,
        ge=0.0,
        description="Estimated LLM token cost in USD"
    )

    estimated_time: int = Field(
        default=0,
        ge=0,
        description="Estimated execution time in seconds"
    )

    model_config = {
        "json_schema_extra": {
            "examples": [
                {
                    "objective": "Map relationships between defense contractors working on AI security",
                    "sub_questions": [
                        {
                            "question": "What partnerships exist between defense contractors and commercial AI labs?",
                            "rationale": "Identify collaboration networks",
                            "suggested_categories": ["government_contracts", "social_media"],
                            "estimated_sources": 4
                        },
                        {
                            "question": "What subcontracting relationships are documented in federal procurement data?",
                            "rationale": "Track formal contractual relationships",
                            "suggested_categories": ["government_contracts"],
                            "estimated_sources": 2
                        }
                    ],
                    "constraints": {
                        "timeframe": "2024-2025",
                        "geography": "US-based contractors"
                    },
                    "estimated_cost": 1.20,
                    "estimated_time": 45
                }
            ]
        }
    }


class PlanApproval(BaseModel):
    """User approval response for research plan"""

    approved: bool = Field(
        ...,
        description="Whether user approved the plan"
    )

    feedback: Optional[str] = Field(
        default=None,
        max_length=1000,
        description="User feedback for plan revision (if not approved)"
    )

    edited_brief: Optional[ResearchBrief] = Field(
        default=None,
        description="Revised brief after incorporating feedback"
    )
