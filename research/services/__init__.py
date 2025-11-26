#!/usr/bin/env python3
"""
Research services - extracted from mixins for composition over inheritance.

These are service classes that can be dependency-injected,
tested in isolation, and reused across different contexts.

Services (Phase 1 - Complete):
- QueryReformulator: Stateless service for query reformulation
- EntityAnalyzer: Stateful service for entity extraction and relationship tracking

Services (Phase 2 - Complete):
- ResultFilter: Stateless service for result validation and filtering
- QueryGenerator: Stateless service for hypothesis query generation
"""

from research.services.query_reformulator import QueryReformulator
from research.services.entity_analyzer import EntityAnalyzer
from research.services.result_filter import ResultFilter
from research.services.query_generator import QueryGenerator

__all__ = [
    "QueryReformulator",
    "EntityAnalyzer",
    "ResultFilter",
    "QueryGenerator",
]
