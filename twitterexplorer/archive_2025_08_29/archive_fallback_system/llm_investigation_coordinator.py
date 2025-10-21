# llm_investigation_coordinator.py
"""
LLM-Centric Intelligence Architecture for Investigation Coordination

This replaces the fragmented intelligence (smart LLM strategy → dumb hardcoded execution)
with unified intelligence (single LLM coordinator making all investigation decisions).
"""

import json
import time
from typing import Dict, List, Any, Optional, Tuple
from dataclasses import dataclass
from datetime import datetime
import logging

from investigation_prompts import (
    format_coordinator_prompt, 
    format_evaluation_prompt, 
    format_synthesis_prompt,
    TERMINATION_ASSESSMENT_PROMPT,
    FAILED_STRATEGY_ANALYSIS_PROMPT
)

@dataclass
class InvestigationContext:
    """Context for ongoing investigation"""
    goal: str
    current_understanding: str = "Starting investigation"
    information_gaps: List[str] = None
    accumulated_evidence: List[Dict] = None
    search_history: List[Dict] = None
    confidence_level: float = 0.0
    
    def __post_init__(self):
        if self.information_gaps is None:
            self.information_gaps = ["All aspects of the topic need investigation"]
        if self.accumulated_evidence is None:
            self.accumulated_evidence = []
        if self.search_history is None:
            self.search_history = []

class LLMInvestigationCoordinator:
    """
    LLM-centric coordinator that makes all investigation decisions
    
    EVIDENCE REQUIREMENT: Must make intelligent decisions based on full context
    - Select appropriate endpoints based on information needs
    - Evaluate semantic relevance, not just quantity
    - Build progressive understanding
    - Avoid repetitive failed strategies
    - Provide real-time user communication
    """
    
    def __init__(self, llm_handler):
        self.llm = llm_handler
        self.context = None
        self.available_endpoints = {
            'search.php': {
                'description': 'General keyword searches for broad topic exploration',
                'params': ['query', 'result_type'],
                'best_for': 'General topics, keyword exploration, trending content'
            },
            'timeline.php': {
                'description': 'Specific user timeline posts and statements',
                'params': ['screenname', 'count'],
                'best_for': 'Direct statements from specific users/figures'
            },
            'screenname.php': {
                'description': 'User profile information and validation', 
                'params': ['screenname'],
                'best_for': 'User verification, profile information'
            },
            'hashtag.php': {
                'description': 'Hashtag-based trending discussions',
                'params': ['hashtag', 'result_type'], 
                'best_for': 'Trending topics, viral discussions'
            }
        }
        self.logger = logging.getLogger(__name__)
        
    def start_investigation(self, goal: str) -> InvestigationContext:
        """Initialize new investigation context"""
        self.context = InvestigationContext(goal=goal)
        self.logger.info(f"Started investigation: {goal}")
        return self.context
        
    def decide_next_action(self, goal: str, current_understanding: str, 
                          gaps: List[str], search_history: List[Dict]) -> Dict[str, Any]:
        """
        EVIDENCE REQUIREMENT: Must make intelligent decisions based on full context
        
        Returns: {
            'endpoint': str,
            'parameters': dict,
            'reasoning': str,
            'evaluation_criteria': dict,
            'user_update': str
        }
        """
        try:
            # Analyze search history for failure patterns
            failed_strategies = self._identify_failed_patterns(search_history)
            
            # Create decision prompt
            prompt = format_coordinator_prompt(
                investigation_goal=goal,
                current_understanding=current_understanding,
                information_gaps=gaps,
                recent_searches=search_history,
                available_endpoints=self.available_endpoints,
                failed_strategies=failed_strategies
            )
            
            # Get LLM decision
            response = self._get_llm_completion(prompt, "decision_making")
            
            if not response:
                raise RuntimeError("LLM completion returned empty response - cannot make investigation decision")
                
            decision = self._parse_llm_response(response)
            
            # Handle both single and batch decision formats
            if 'searches' in decision:
                # Batch format - convert to single decision format for compatibility
                # For now, use the first search in the batch
                if decision['searches']:
                    first_search = decision['searches'][0]
                    single_decision = {
                        'endpoint': first_search['endpoint'],
                        'parameters': first_search['parameters'],
                        'params': first_search['parameters'],  # Alias for compatibility
                        'reasoning': decision.get('reasoning', first_search.get('reasoning', '')),
                        'evaluation_criteria': decision.get('evaluation_criteria', {}),
                        'user_update': decision.get('user_update', 'Executing search strategy'),
                        'batch_searches': decision['searches']  # Preserve full batch for future use
                    }
                    self._validate_decision(single_decision)
                    return single_decision
                else:
                    # Empty searches array, create fallback
                    fallback_decision = self._create_fallback_decision(goal, gaps)
                    self._validate_decision(fallback_decision)
                    return fallback_decision
            else:
                # Single decision format
                self._validate_decision(decision)
                return decision
                
        except Exception as e:
            self.logger.error(f"Error in decide_next_action: {e}")
            raise RuntimeError(f"LLM coordinator failed to make investigation decision: {e}")
    
    def evaluate_results(self, goal: str, results: List[Dict], 
                        search_context: Dict) -> Dict[str, Any]:
        """
        EVIDENCE REQUIREMENT: Must evaluate semantic relevance, not just quantity
        
        Returns: {
            'relevance_score': float,  # 0-10 based on actual content
            'information_value': float,  # 0-10 based on investigation progress
            'key_insights': list,
            'remaining_gaps': list,
            'should_continue': bool
        }
        """
        try:
            # Create evaluation prompt
            prompt = format_evaluation_prompt(
                investigation_goal=goal,
                search_query=search_context.get('query', 'Unknown'),
                endpoint=search_context.get('endpoint', 'Unknown'),
                expected_info=search_context.get('evaluation_criteria', {}).get('information_targets', []),
                search_results=results
            )
            
            # Get LLM evaluation
            response = self._get_llm_completion(prompt, "result_evaluation")
            
            if not response:
                raise RuntimeError("LLM completion returned empty response - cannot evaluate search results")
                
            evaluation = self._parse_llm_response(response)
            self._validate_evaluation(evaluation)
            return evaluation
                
        except Exception as e:
            self.logger.error(f"Error in evaluate_results: {e}")
            raise RuntimeError(f"LLM coordinator failed to evaluate search results: {e}")
    
    def synthesize_understanding(self, goal: str, accumulated_evidence: List[Dict]) -> Dict[str, Any]:
        """
        EVIDENCE REQUIREMENT: Must build progressive understanding
        
        Returns: {
            'current_understanding': str,
            'confidence_level': float,
            'key_findings': list,
            'critical_gaps': list
        }
        """
        try:
            # Analyze successful and failed patterns
            successful_patterns = self._identify_successful_patterns(accumulated_evidence)
            failed_patterns = []
            if hasattr(self, 'context') and self.context:
                failed_patterns = self._identify_failed_patterns(self.context.search_history)
            
            # Create synthesis prompt
            prompt = format_synthesis_prompt(
                investigation_goal=goal,
                accumulated_evidence=accumulated_evidence,
                total_searches=len(self.context.search_history) if self.context else 0,
                successful_patterns=successful_patterns,
                failed_patterns=failed_patterns
            )
            
            # Get LLM synthesis
            response = self._get_llm_completion(prompt, "understanding_synthesis")
            
            if not response:
                raise RuntimeError("LLM completion returned empty response - cannot synthesize understanding")
                
            synthesis = self._parse_llm_response(response)
            self._validate_synthesis(synthesis)
            
            # Update context if available
            if self.context:
                self.context.current_understanding = synthesis.get('current_understanding', '')
                self.context.confidence_level = synthesis.get('confidence_level', 0.0)
                self.context.information_gaps = synthesis.get('critical_gaps', [])
            
            return synthesis
                
        except Exception as e:
            self.logger.error(f"Error in synthesize_understanding: {e}")
            raise RuntimeError(f"LLM coordinator failed to synthesize understanding: {e}")
    
    def assess_termination(self, goal: str, current_understanding: str,
                          key_findings: List[str], search_count: int,
                          time_elapsed: float) -> Dict[str, Any]:
        """
        Assess whether investigation goals have been sufficiently met
        
        Returns: {
            'should_terminate': bool,
            'termination_reason': str,
            'satisfaction_scores': dict,
            'overall_satisfaction': float
        }
        """
        try:
            prompt = TERMINATION_ASSESSMENT_PROMPT.format(
                investigation_goal=goal,
                original_goal=goal,
                current_understanding=current_understanding,
                key_findings=', '.join(key_findings) if key_findings else 'No significant findings yet',
                search_count=search_count,
                time_elapsed=f"{time_elapsed:.1f} minutes"
            )
            
            response = self._get_llm_completion(prompt, "termination_assessment")
            
            if response:
                assessment = self._parse_llm_response(response)
                return assessment
            else:
                # Conservative fallback - continue investigation
                return {
                    'should_terminate': False,
                    'termination_reason': 'Unable to assess completion, continuing investigation',
                    'satisfaction_scores': {
                        'information_coverage': 0.3,
                        'source_diversity': 0.3,
                        'evidence_quality': 0.5,
                        'claim_specificity': 0.2,
                        'gap_resolution': 0.2
                    },
                    'overall_satisfaction': 0.3
                }
                
        except Exception as e:
            self.logger.error(f"Error in assess_termination: {e}")
            # Conservative fallback
            return {
                'should_terminate': False,
                'termination_reason': f'Assessment error: {str(e)}, continuing investigation',
                'satisfaction_scores': {},
                'overall_satisfaction': 0.0
            }
    
    def _get_llm_completion(self, prompt: str, interaction_type: str) -> Optional[str]:
        """Get completion from LLM with error handling"""
        try:
            start_time = time.time()
            
            # Use LiteLLM completion
            response = self.llm.completion(
                model="gemini/gemini-2.5-flash",
                messages=[
                    {"role": "system", "content": "You are an expert Twitter investigation coordinator. Always return valid JSON."},
                    {"role": "user", "content": prompt}
                ],
                response_format={"type": "json_object"}
            )
            
            processing_time = time.time() - start_time
            self.logger.info(f"LLM {interaction_type} completed in {processing_time:.2f}s")
            
            return response.choices[0].message.content
            
        except Exception as e:
            self.logger.error(f"LLM completion failed for {interaction_type}: {e}")
            return None
    
    def _parse_llm_response(self, response) -> Dict[str, Any]:
        """Parse LLM JSON response with error handling"""
        try:
            # Handle direct dict response (for testing)
            if isinstance(response, dict):
                return response
            
            # Handle string response
            if isinstance(response, str):
                # Clean up response - remove markdown formatting if present
                cleaned = response.strip()
                if cleaned.startswith('```json'):
                    cleaned = cleaned[7:]
                if cleaned.endswith('```'):
                    cleaned = cleaned[:-3]
                cleaned = cleaned.strip()
                
                return json.loads(cleaned)
            
            # Handle other response types
            return {}
            
        except json.JSONDecodeError as e:
            self.logger.error(f"Failed to parse LLM response as JSON: {e}")
            self.logger.error(f"Raw response: {response[:500]}...")
            raise RuntimeError(f"LLM returned invalid JSON response: {e}. Response: {response[:200]}...")
    
    def _identify_failed_patterns(self, search_history: List[Dict]) -> List[str]:
        """Identify patterns that consistently fail"""
        failed_patterns = []
        
        # Count query repetitions with low effectiveness
        query_stats = {}
        for search in search_history:
            query = search.get('query', search.get('params', {}).get('query', 'unknown'))
            effectiveness = search.get('effectiveness_score', 0)
            
            if query not in query_stats:
                query_stats[query] = {'count': 0, 'total_effectiveness': 0}
            
            query_stats[query]['count'] += 1
            query_stats[query]['total_effectiveness'] += effectiveness
        
        # Identify failed patterns (repeated 3+ times with low effectiveness)
        for query, stats in query_stats.items():
            if stats['count'] >= 3:
                avg_effectiveness = stats['total_effectiveness'] / stats['count']
                if avg_effectiveness < 5.0:  # Below moderate effectiveness
                    failed_patterns.append(f"'{query}' (repeated {stats['count']} times, avg effectiveness: {avg_effectiveness:.1f})")
        
        return failed_patterns
    
    def _identify_successful_patterns(self, accumulated_evidence: List[Dict]) -> List[str]:
        """Identify successful search patterns from evidence"""
        successful_patterns = []
        
        # Look for patterns in successful evidence gathering
        if accumulated_evidence:
            sources = set()
            categories = set()
            
            for evidence in accumulated_evidence:
                if evidence.get('source'):
                    sources.add(evidence['source'])
                if evidence.get('category'):
                    categories.add(evidence['category'])
            
            if sources:
                successful_patterns.append(f"Successful sources: {', '.join(list(sources)[:3])}")
            if categories:
                successful_patterns.append(f"Successful categories: {', '.join(list(categories)[:3])}")
        
        return successful_patterns
    
    
    def _extract_potential_usernames(self, goal: str) -> List[str]:
        """Extract potential usernames/figures from investigation goal"""
        
        # Common figure mapping
        figure_map = {
            'trump': 'realDonaldTrump',
            'elon': 'elonmusk',
            'musk': 'elonmusk',
            'biden': 'JoeBiden',
            'obama': 'BarackObama',
        }
        
        goal_lower = goal.lower()
        potential_users = []
        
        for keyword, username in figure_map.items():
            if keyword in goal_lower:
                potential_users.append(username)
        
        return potential_users
    
    def _create_fallback_decision(self, goal: str, gaps: List[str]) -> Dict[str, Any]:
        """Create fallback decision when LLM response is invalid"""
        # Extract potential usernames from goal
        potential_users = self._extract_potential_usernames(goal)
        
        if potential_users:
            # Use timeline.php for specific figures
            return {
                'endpoint': 'timeline.php',
                'parameters': {'screenname': potential_users[0], 'count': 20},
                'params': {'screenname': potential_users[0], 'count': 20},
                'reasoning': f'Fallback strategy: Get direct statements from {potential_users[0]}',
                'evaluation_criteria': {
                    'relevance_indicators': [word for word in goal.lower().split() if len(word) > 3],
                    'success_threshold': 0.6,
                    'information_targets': gaps
                },
                'user_update': f'Using fallback strategy to get direct statements from key figure'
            }
        else:
            # Use search.php as general fallback
            return {
                'endpoint': 'search.php',
                'parameters': {'query': ' '.join(goal.split()[:4]), 'result_type': 'latest'},
                'params': {'query': ' '.join(goal.split()[:4]), 'result_type': 'latest'},
                'reasoning': 'Fallback strategy: General search for investigation topic',
                'evaluation_criteria': {
                    'relevance_indicators': [word for word in goal.lower().split() if len(word) > 3],
                    'success_threshold': 0.6,
                    'information_targets': gaps
                },
                'user_update': 'Using fallback search strategy'
            }

    def _validate_decision(self, decision: Dict[str, Any]) -> None:
        """Validate decision structure"""
        required_keys = ['endpoint', 'parameters', 'reasoning', 'evaluation_criteria', 'user_update']
        for key in required_keys:
            if key not in decision:
                decision[key] = f"Missing {key}"
        
        # Ensure params alias exists
        if 'params' not in decision and 'parameters' in decision:
            decision['params'] = decision['parameters']
    
    def _validate_evaluation(self, evaluation: Dict[str, Any]) -> None:
        """Validate evaluation structure"""
        required_keys = ['relevance_score', 'information_value', 'key_insights', 'remaining_gaps', 'should_continue']
        for key in required_keys:
            if key not in evaluation:
                if key in ['relevance_score', 'information_value']:
                    evaluation[key] = 0.0
                elif key == 'should_continue':
                    evaluation[key] = True
                else:
                    evaluation[key] = []
    
    def _validate_synthesis(self, synthesis: Dict[str, Any]) -> None:
        """Validate synthesis structure"""
        required_keys = ['current_understanding', 'confidence_level', 'key_findings', 'critical_gaps']
        for key in required_keys:
            if key not in synthesis:
                if key == 'confidence_level':
                    synthesis[key] = 0.0
                elif key == 'current_understanding':
                    synthesis[key] = "Understanding synthesis unavailable"
                else:
                    synthesis[key] = []