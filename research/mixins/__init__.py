"""
Mixins for SimpleDeepResearch class.

These mixins break up the god class into logical components
while maintaining shared state through the host class instance.

Extracted to services (see research/services/):
- QueryReformulationMixin -> QueryReformulator
- EntityAnalysisMixin -> EntityAnalyzer
"""

from .content_enrichment_mixin import ContentEnrichmentMixin
from .follow_up_task_mixin import FollowUpTaskMixin
from .hypothesis_mixin import HypothesisMixin
from .mcp_tool_mixin import MCPToolMixin
from .output_persistence_mixin import OutputPersistenceMixin
from .query_generation_mixin import QueryGenerationMixin
from .report_synthesizer_mixin import ReportSynthesizerMixin
from .result_filter_mixin import ResultFilterMixin
from .source_executor_mixin import SourceExecutorMixin

__all__ = [
    "ContentEnrichmentMixin",
    "FollowUpTaskMixin",
    "HypothesisMixin",
    "MCPToolMixin",
    "OutputPersistenceMixin",
    "QueryGenerationMixin",
    "ReportSynthesizerMixin",
    "ResultFilterMixin",
    "SourceExecutorMixin"
]
