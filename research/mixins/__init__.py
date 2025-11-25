"""
Mixins for SimpleDeepResearch class.

These mixins break up the god class into logical components
while maintaining shared state through the host class instance.
"""

from .entity_mixin import EntityAnalysisMixin
from .report_synthesizer_mixin import ReportSynthesizerMixin

__all__ = ["EntityAnalysisMixin", "ReportSynthesizerMixin"]
