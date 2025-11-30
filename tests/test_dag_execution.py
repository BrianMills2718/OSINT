#!/usr/bin/env python3
"""
Unit and integration tests for DAG (Directed Acyclic Graph) execution.

Tests the dependency-based execution order of sub-goals.
"""

import pytest
from research.recursive_agent import RecursiveResearchAgent, SubGoal


class TestGroupByDependency:
    """Unit tests for _group_by_dependency topological sort."""

    def test_no_dependencies(self):
        """All goals have no dependencies → single group."""
        agent = RecursiveResearchAgent()
        sub_goals = [
            SubGoal("Goal A", "Rationale A", dependencies=[]),
            SubGoal("Goal B", "Rationale B", dependencies=[]),
            SubGoal("Goal C", "Rationale C", dependencies=[]),
        ]

        groups = agent._group_by_dependency(sub_goals)

        assert len(groups) == 1, "All independent goals should be in one group"
        assert len(groups[0]) == 3, "Group should contain all 3 goals"

    def test_simple_linear_dependency(self):
        """Goal B depends on Goal A → two groups."""
        agent = RecursiveResearchAgent()
        sub_goals = [
            SubGoal("Goal A", "Rationale A", dependencies=[]),
            SubGoal("Goal B depends on A", "Rationale B", dependencies=[0]),
        ]

        groups = agent._group_by_dependency(sub_goals)

        assert len(groups) == 2, "Should create 2 sequential groups"
        assert len(groups[0]) == 1, "First group has 1 goal"
        assert groups[0][0].description == "Goal A"
        assert len(groups[1]) == 1, "Second group has 1 goal"
        assert groups[1][0].description == "Goal B depends on A"

    def test_parallel_with_dependent(self):
        """A and B independent, C depends on both → two groups."""
        agent = RecursiveResearchAgent()
        sub_goals = [
            SubGoal("Goal A", "Rationale A", dependencies=[]),
            SubGoal("Goal B", "Rationale B", dependencies=[]),
            SubGoal("Goal C depends on A and B", "Rationale C", dependencies=[0, 1]),
        ]

        groups = agent._group_by_dependency(sub_goals)

        assert len(groups) == 2, "Should create 2 groups"
        assert len(groups[0]) == 2, "First group has A and B (parallel)"
        assert len(groups[1]) == 1, "Second group has C (waits for A and B)"

        # Verify C is in second group
        assert groups[1][0].description == "Goal C depends on A and B"

    def test_chain_dependency(self):
        """A → B → C → D (linear chain) → four groups."""
        agent = RecursiveResearchAgent()
        sub_goals = [
            SubGoal("Goal A", "Rationale A", dependencies=[]),
            SubGoal("Goal B", "Rationale B", dependencies=[0]),
            SubGoal("Goal C", "Rationale C", dependencies=[1]),
            SubGoal("Goal D", "Rationale D", dependencies=[2]),
        ]

        groups = agent._group_by_dependency(sub_goals)

        assert len(groups) == 4, "Linear chain creates 4 sequential groups"
        for i, group in enumerate(groups):
            assert len(group) == 1, f"Group {i} should have 1 goal"

    def test_diamond_dependency(self):
        """
        Diamond pattern:
        A is independent
        B and C depend on A (parallel)
        D depends on B and C

        Expected: 3 groups
        """
        agent = RecursiveResearchAgent()
        sub_goals = [
            SubGoal("Goal A", "Rationale A", dependencies=[]),
            SubGoal("Goal B", "Rationale B", dependencies=[0]),
            SubGoal("Goal C", "Rationale C", dependencies=[0]),
            SubGoal("Goal D", "Rationale D", dependencies=[1, 2]),
        ]

        groups = agent._group_by_dependency(sub_goals)

        assert len(groups) == 3, "Diamond creates 3 groups"
        assert len(groups[0]) == 1, "Group 0: A"
        assert len(groups[1]) == 2, "Group 1: B and C (parallel)"
        assert len(groups[2]) == 1, "Group 2: D"

    def test_circular_dependency_handled(self):
        """Circular dependencies → all goals in one group (graceful degradation)."""
        agent = RecursiveResearchAgent()
        sub_goals = [
            SubGoal("Goal A", "Rationale A", dependencies=[1]),  # A depends on B
            SubGoal("Goal B", "Rationale B", dependencies=[0]),  # B depends on A (circular!)
        ]

        groups = agent._group_by_dependency(sub_goals)

        # Code should handle this gracefully by putting all in one group
        assert len(groups) == 1, "Circular dependency should result in single group"
        assert len(groups[0]) == 2, "Both goals in one group"

    def test_partial_dependencies(self):
        """Mix of dependent and independent goals."""
        agent = RecursiveResearchAgent()
        sub_goals = [
            SubGoal("Goal A", "Rationale A", dependencies=[]),
            SubGoal("Goal B depends on A", "Rationale B", dependencies=[0]),
            SubGoal("Goal C independent", "Rationale C", dependencies=[]),
        ]

        groups = agent._group_by_dependency(sub_goals)

        assert len(groups) == 2, "Should create 2 groups"
        assert len(groups[0]) == 2, "First group: A and C (parallel)"
        assert len(groups[1]) == 1, "Second group: B (waits for A)"


# Integration and E2E tests will be added in subsequent commits
# after Phase 1 logging is validated
