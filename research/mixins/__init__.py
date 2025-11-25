"""
Mixins for SimpleDeepResearch class.

These mixins break up the god class into logical components
while maintaining shared state through the host class instance.
"""

from .entity_mixin import EntityAnalysisMixin
from .follow_up_task_mixin import FollowUpTaskMixin
from .hypothesis_mixin import HypothesisMixin
from .mcp_tool_mixin import MCPToolMixin
from .output_persistence_mixin import OutputPersistenceMixin
from .query_generation_mixin import QueryGenerationMixin
from .query_reformulation_mixin import QueryReformulationMixin
from .report_synthesizer_mixin import ReportSynthesizerMixin
from .result_filter_mixin import ResultFilterMixin
from .source_executor_mixin import SourceExecutorMixin

__all__ = [
    "EntityAnalysisMixin",
    "FollowUpTaskMixin",
    "HypothesisMixin",
    "MCPToolMixin",
    "OutputPersistenceMixin",
    "QueryGenerationMixin",
    "QueryReformulationMixin",
    "ReportSynthesizerMixin",
    "ResultFilterMixin",
    "SourceExecutorMixin"
]
