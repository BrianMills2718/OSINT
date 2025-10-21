from pydantic import BaseModel, Field, field_validator
from typing import List, Dict, Any, Optional
from datetime import datetime

class EndpointPlan(BaseModel):
    """Single endpoint execution plan"""
    endpoint: str
    params: Dict[str, Any] = Field(default_factory=dict)  # Default to empty dict for Gemini compatibility
    expected_value: str
    reason: Optional[str] = ""

class EvaluationCriteria(BaseModel):
    """Criteria for evaluating results"""
    relevance_indicators: List[str] = Field(default_factory=list)
    quality_signals: List[str] = Field(default_factory=list)
    red_flags: List[str] = Field(default_factory=list)

class StrategyOutput(BaseModel):
    """LLM strategy generation output"""
    reasoning: str
    endpoints: List[EndpointPlan]
    evaluation_criteria: Optional[EvaluationCriteria] = None
    user_update: str
    confidence: float = 0.7
    
    @field_validator('confidence')
    @classmethod
    def validate_confidence(cls, v):
        if not 0 <= v <= 1:
            raise ValueError('Confidence must be between 0 and 1')
        return v

class Finding(BaseModel):
    """Single finding from evaluation"""
    content: str
    relevance_score: float
    reasoning: str
    source_endpoint: Optional[str] = None
    timestamp: datetime = Field(default_factory=datetime.now)
    
    @field_validator('relevance_score')
    @classmethod
    def validate_score(cls, v):
        if not 0 <= v <= 10:
            raise ValueError('Score must be between 0 and 10')
        return round(v, 1)

class RejectionFeedback(BaseModel):
    """Feedback on rejected results"""
    rejection_rate: float = 0.0
    rejection_themes: List[str] = Field(default_factory=list)
    rejected_keywords: List[str] = Field(default_factory=list)

class EvaluationOutput(BaseModel):
    """Complete evaluation output"""
    findings: List[Finding] = Field(default_factory=list)
    relevance_score: float = 0.0
    remaining_gaps: List[str] = Field(default_factory=list)
    rejection_feedback: Optional[RejectionFeedback] = None