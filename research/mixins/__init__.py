"""
Mixins for SimpleDeepResearch class.

These mixins break up the god class into logical components
while maintaining shared state through the host class instance.
"""

from .entity_mixin import EntityAnalysisMixin
from .hypothesis_mixin import HypothesisMixin
from .report_synthesizer_mixin import ReportSynthesizerMixin
from .result_filter_mixin import ResultFilterMixin

__all__ = ["EntityAnalysisMixin", "HypothesisMixin", "ReportSynthesizerMixin", "ResultFilterMixin"]
