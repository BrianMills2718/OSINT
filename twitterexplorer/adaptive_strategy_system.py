"""
Adaptive Strategy System - Pivots when searches fail to produce results

This module implements intelligent adaptation when investigation strategies
aren't producing results, including:
- Strategy effectiveness tracking
- Automatic pivoting to alternative approaches
- Broadening/narrowing search parameters
- Trying different information sources
"""

from typing import Dict, List, Any, Optional, Tuple
from dataclasses import dataclass
from datetime import datetime
import logging

@dataclass
class StrategyEffectiveness:
    """Track effectiveness of different strategies"""
    strategy_type: str
    attempts: int = 0
    results_found: int = 0
    effectiveness_score: float = 0.0
    last_attempt: Optional[datetime] = None
    
    def update(self, results_count: int):
        """Update effectiveness based on results"""
        self.attempts += 1
        self.results_found += results_count
        self.effectiveness_score = self.results_found / max(1, self.attempts)
        self.last_attempt = datetime.now()

class AdaptiveStrategySystem:
    """
    Manages adaptive investigation strategies that pivot when current
    approaches aren't working
    """
    
    def __init__(self):
        self.strategy_history: Dict[str, StrategyEffectiveness] = {}
        self.consecutive_failures = 0
        self.total_results = 0
        self.pivot_count = 0
        self.logger = logging.getLogger(__name__)
        
        # Strategy templates for different scenarios
        self.pivot_strategies = {
            "broaden_search": {
                "description": "Broaden search terms when too specific",
                "triggers": ["zero_results", "low_results"],
                "adaptations": [
                    "Remove quotes from exact phrases",
                    "Use OR instead of AND operators",
                    "Remove restrictive filters",
                    "Search for related terms instead"
                ]
            },
            "narrow_search": {
                "description": "Narrow search when too many irrelevant results",
                "triggers": ["information_overload", "low_relevance"],
                "adaptations": [
                    "Add more specific terms",
                    "Use exact phrase matching",
                    "Add date ranges",
                    "Focus on verified accounts"
                ]
            },
            "alternative_sources": {
                "description": "Try different information sources",
                "triggers": ["source_exhausted", "repeated_failures"],
                "adaptations": [
                    "Switch from search to user timelines",
                    "Look at trending topics instead",
                    "Check network connections (followers/following)",
                    "Examine lists and communities"
                ]
            },
            "lateral_thinking": {
                "description": "Approach from different angle",
                "triggers": ["stuck_pattern", "no_progress"],
                "adaptations": [
                    "Search for critics/debunkers instead of supporters",
                    "Look for related events/topics",
                    "Find influencers in the domain",
                    "Search for historical context"
                ]
            }
        }
    
    def analyze_situation(self, 
                         recent_searches: List[Dict],
                         total_results: int,
                         investigation_goal: str) -> Dict[str, Any]:
        """
        Analyze current investigation situation to determine if pivot needed
        
        Returns analysis with recommendations
        """
        analysis = {
            "needs_pivot": False,
            "pivot_reason": None,
            "recommended_strategy": None,
            "confidence": 0.0
        }
        
        # Check for consecutive failures
        if recent_searches:
            failures = sum(1 for s in recent_searches[-5:] 
                          if s.get('results_count', 0) == 0)
            
            if failures >= 3:
                analysis["needs_pivot"] = True
                analysis["pivot_reason"] = "consecutive_failures"
                analysis["recommended_strategy"] = "alternative_sources"
                analysis["confidence"] = 0.9
                self.consecutive_failures = failures
        
        # Check for overall low results
        if len(recent_searches) >= 5 and total_results < 10:
            analysis["needs_pivot"] = True
            analysis["pivot_reason"] = "low_overall_results"
            analysis["recommended_strategy"] = "broaden_search"
            analysis["confidence"] = 0.8
        
        # Check for pattern stuck (same queries repeated)
        if self._detect_stuck_pattern(recent_searches):
            analysis["needs_pivot"] = True
            analysis["pivot_reason"] = "stuck_in_pattern"
            analysis["recommended_strategy"] = "lateral_thinking"
            analysis["confidence"] = 0.85
        
        # Check for single endpoint overuse
        if self._detect_endpoint_fixation(recent_searches):
            analysis["needs_pivot"] = True
            analysis["pivot_reason"] = "endpoint_fixation"
            analysis["recommended_strategy"] = "alternative_sources"
            analysis["confidence"] = 0.75
        
        return analysis
    
    def generate_pivot_strategy(self,
                               current_context: Dict,
                               pivot_type: str,
                               investigation_goal: str) -> Dict[str, Any]:
        """
        Generate a pivot strategy based on analysis
        
        Returns new strategy with adapted approach
        """
        base_strategy = self.pivot_strategies.get(pivot_type, 
                                                  self.pivot_strategies["broaden_search"])
        
        # Track pivot
        self.pivot_count += 1
        
        # Generate adapted searches based on pivot type
        if pivot_type == "broaden_search":
            return self._generate_broadened_searches(current_context, investigation_goal)
        elif pivot_type == "alternative_sources":
            return self._generate_alternative_source_searches(current_context, investigation_goal)
        elif pivot_type == "lateral_thinking":
            return self._generate_lateral_searches(current_context, investigation_goal)
        else:
            return self._generate_narrowed_searches(current_context, investigation_goal)
    
    def _generate_broadened_searches(self, context: Dict, goal: str) -> Dict:
        """Generate broader search strategies"""
        # Extract key terms from goal
        key_terms = self._extract_key_terms(goal)
        
        return {
            "strategy_type": "broadened_search",
            "reasoning": f"Previous searches too specific. Broadening to capture more results.",
            "searches": [
                {
                    "endpoint": "search.php",
                    "parameters": {
                        "query": " OR ".join(key_terms[:3])  # Use OR for broader results
                    },
                    "reasoning": "Broad OR search to capture any mentions"
                },
                {
                    "endpoint": "trends.php",
                    "parameters": {
                        "country": "UnitedStates"
                    },
                    "reasoning": "Check if topic is trending"
                },
                {
                    "endpoint": "search.php",
                    "parameters": {
                        "query": key_terms[0],  # Single most important term
                        "search_type": "Latest"
                    },
                    "reasoning": "Most recent mentions of key term"
                }
            ]
        }
    
    def _generate_alternative_source_searches(self, context: Dict, goal: str) -> Dict:
        """Generate searches using alternative sources"""
        key_terms = self._extract_key_terms(goal)
        
        return {
            "strategy_type": "alternative_sources",
            "reasoning": "Traditional search not yielding results. Trying alternative information sources.",
            "searches": [
                {
                    "endpoint": "timeline.php",
                    "parameters": {
                        "screenname": "Reuters"  # Major news source
                    },
                    "reasoning": "Check major news outlet for coverage"
                },
                {
                    "endpoint": "timeline.php", 
                    "parameters": {
                        "screenname": "AP"  # Another news source
                    },
                    "reasoning": "Check alternative news source"
                },
                {
                    "endpoint": "list.php",
                    "parameters": {
                        "list_id": "1234"  # Would need actual list ID
                    },
                    "reasoning": "Check curated lists for domain experts"
                }
            ]
        }
    
    def _generate_lateral_searches(self, context: Dict, goal: str) -> Dict:
        """Generate lateral thinking searches"""
        key_terms = self._extract_key_terms(goal)
        
        # For debunking, look for supporters to understand claims first
        if "debunk" in goal.lower():
            return {
                "strategy_type": "lateral_approach",
                "reasoning": "Can't debunk what we don't understand. Finding the actual claims first.",
                "searches": [
                    {
                        "endpoint": "search.php",
                        "parameters": {
                            "query": f"{key_terms[0]} testimony OR experience OR story"
                        },
                        "reasoning": "Find the original claims/story"
                    },
                    {
                        "endpoint": "search.php",
                        "parameters": {
                            "query": f"{key_terms[0]} believers OR supporters"
                        },
                        "reasoning": "Find who supports these claims"
                    },
                    {
                        "endpoint": "search.php",
                        "parameters": {
                            "query": "UFO skeptics OR debunkers",
                            "search_type": "People"
                        },
                        "reasoning": "Find skeptic accounts to follow up with"
                    }
                ]
            }
        
        return {
            "strategy_type": "lateral_approach",
            "reasoning": "Approaching from different angle",
            "searches": []
        }
    
    def _generate_narrowed_searches(self, context: Dict, goal: str) -> Dict:
        """Generate more focused searches"""
        key_terms = self._extract_key_terms(goal)
        
        return {
            "strategy_type": "narrowed_search",
            "reasoning": "Focusing search to reduce noise",
            "searches": [
                {
                    "endpoint": "search.php",
                    "parameters": {
                        "query": f'"{" ".join(key_terms[:2])}"'  # Exact phrase
                    },
                    "reasoning": "Exact phrase match for precision"
                }
            ]
        }
    
    def _detect_stuck_pattern(self, recent_searches: List[Dict]) -> bool:
        """Detect if searches are stuck in repetitive pattern"""
        if len(recent_searches) < 5:
            return False
        
        # Check if same queries repeated
        recent_queries = [s.get('query', '') for s in recent_searches[-5:]]
        unique_queries = set(recent_queries)
        
        return len(unique_queries) < 3  # Less than 3 unique queries in last 5
    
    def _detect_endpoint_fixation(self, recent_searches: List[Dict]) -> bool:
        """Detect if using same endpoint too much"""
        if len(recent_searches) < 5:
            return False
        
        endpoints = [s.get('endpoint', '') for s in recent_searches[-5:]]
        unique_endpoints = set(endpoints)
        
        return len(unique_endpoints) == 1  # Only one endpoint in last 5 searches
    
    def _extract_key_terms(self, goal: str) -> List[str]:
        """Extract key terms from investigation goal"""
        # Simple extraction - could be enhanced with NLP
        stop_words = {'find', 'me', 'information', 'that', 'the', 'a', 'an', 
                     'about', 'for', 'with', 'on', 'in', 'to', 'from'}
        
        words = goal.lower().split()
        key_terms = [w for w in words if w not in stop_words and len(w) > 2]
        
        return key_terms
    
    def update_effectiveness(self, strategy_type: str, results_count: int):
        """Update strategy effectiveness tracking"""
        if strategy_type not in self.strategy_history:
            self.strategy_history[strategy_type] = StrategyEffectiveness(strategy_type)
        
        self.strategy_history[strategy_type].update(results_count)
        self.total_results += results_count
        
        # Reset consecutive failures if we got results
        if results_count > 0:
            self.consecutive_failures = 0
        else:
            self.consecutive_failures += 1
    
    def get_adaptation_report(self) -> str:
        """Generate report on adaptations made"""
        report_lines = [
            f"Adaptation Summary:",
            f"- Total pivots: {self.pivot_count}",
            f"- Consecutive failures: {self.consecutive_failures}",
            f"- Total results found: {self.total_results}",
            "",
            "Strategy Effectiveness:"
        ]
        
        for strategy_type, effectiveness in self.strategy_history.items():
            report_lines.append(
                f"- {strategy_type}: {effectiveness.effectiveness_score:.2f} "
                f"({effectiveness.results_found} results from {effectiveness.attempts} attempts)"
            )
        
        return "\n".join(report_lines)