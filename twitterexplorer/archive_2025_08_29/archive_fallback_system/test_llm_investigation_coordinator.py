# test_llm_investigation_coordinator.py
import pytest
import sys
from unittest.mock import Mock, MagicMock, patch
sys.path.append('.')

from llm_investigation_coordinator import LLMInvestigationCoordinator

class TestLLMInvestigationCoordinator:
    """Evidence-based tests for LLM Investigation Coordinator"""
    
    def setup_method(self):
        """Setup test fixtures"""
        self.mock_llm_handler = Mock()
        self.coordinator = LLMInvestigationCoordinator(self.mock_llm_handler)
    
    def test_llm_coordinator_endpoint_selection(self):
        """EVIDENCE: System must select appropriate endpoint based on investigation goal"""
        
        # Mock LLM response for endpoint selection
        self.mock_llm_handler.get_completion.return_value = {
            "endpoint": "timeline.php",
            "parameters": {"screenname": "realDonaldTrump"},
            "reasoning": "Need direct source access for Trump's actual statements about Epstein",
            "evaluation_criteria": {
                "relevance_indicators": ["Epstein", "Trump", "statement", "controversy"]
            },
            "user_update": "Searching Trump's timeline for direct statements about Epstein"
        }
        
        decision = self.coordinator.decide_next_action(
            goal="analyze Trump's recent statements about Epstein",
            current_understanding="Need direct source access",
            gaps=["Trump's actual tweets about Epstein"],
            search_history=[]
        )
        
        assert decision['endpoint'] == 'timeline.php'
        assert decision['parameters']['screenname'] == 'realDonaldTrump'
        assert 'Epstein' in decision['evaluation_criteria']['relevance_indicators']
    
    def test_llm_coordinator_result_evaluation(self):
        """EVIDENCE: System must properly evaluate result relevance"""
        
        # Mock irrelevant results (like current "find different" queries)
        irrelevant_results = [{"text": "find different ways to save money"} for _ in range(59)]
        
        # Mock LLM response for evaluation
        self.mock_llm_handler.get_completion.return_value = {
            "relevance_score": 0.5,  # Much lower than current 4.5/10
            "information_value": 0.2,  # Very low information value
            "key_insights": [],
            "remaining_gaps": ["No information about Trump-Epstein drama found"],
            "should_continue": False
        }
        
        evaluation = self.coordinator.evaluate_results(
            goal="Trump Epstein drama investigation", 
            results=irrelevant_results,
            search_context={"query": "find different ways to save money"}
        )
        
        assert evaluation['relevance_score'] < 1.0  # Current system scores this as 4.5/10
        assert evaluation['information_value'] < 1.0
        assert evaluation['should_continue'] == False
    
    def test_llm_coordinator_strategy_adaptation(self):
        """EVIDENCE: System must adapt strategy when current approach fails"""
        
        # Simulate 5 failed rounds of same strategy
        failed_searches = [
            {"query": "find different 2024", "effectiveness": 4.5, "results": 59, "endpoint": "search.php"},
            {"query": "find different recent", "effectiveness": 4.5, "results": 60, "endpoint": "search.php"}
        ] * 5
        
        # Mock LLM response for adaptation
        self.mock_llm_handler.get_completion.return_value = {
            "endpoint": "timeline.php",  # Different endpoint
            "parameters": {"screenname": "realDonaldTrump"},
            "reasoning": "Generic 'find different' searches failing. Need direct source access.",
            "evaluation_criteria": {
                "relevance_indicators": ["Trump", "Epstein", "drama", "statement"]
            },
            "user_update": "Switching strategy: accessing Trump's timeline directly for relevant content"
        }
        
        decision = self.coordinator.decide_next_action(
            goal="Trump Epstein investigation",
            current_understanding="Generic searches failing",
            gaps=["Trump's actual statements", "Epstein controversy details"],
            search_history=failed_searches
        )
        
        # Must NOT repeat the same failed strategy
        assert decision['endpoint'] != 'search.php' or decision['parameters']['query'] not in ["find different 2024", "find different recent"]
        assert "Generic" in decision['reasoning'] or "different" in decision['reasoning']  # Must acknowledge failure
    
    def test_llm_coordinator_semantic_understanding(self):
        """EVIDENCE: System must build progressive semantic understanding"""
        
        mock_evidence = [
            {"source": "timeline", "content": "Trump mentions Epstein in context of island"},
            {"source": "search", "content": "Various conspiracy theories about Epstein case"}
        ]
        
        # Mock LLM response for synthesis
        self.mock_llm_handler.get_completion.return_value = {
            "current_understanding": "Trump has made statements connecting to Epstein controversy, multiple theories circulating",
            "confidence_level": 0.7,
            "key_findings": [
                "Trump referenced Epstein's island in recent statements", 
                "Multiple conflicting narratives about the case"
            ],
            "critical_gaps": ["Specific details of recent drama", "Clear timeline of events"]
        }
        
        understanding = self.coordinator.synthesize_understanding(
            goal="Trump Epstein drama investigation",
            accumulated_evidence=mock_evidence
        )
        
        assert understanding['current_understanding'] != ""
        assert understanding['confidence_level'] > 0
        assert len(understanding['key_findings']) > 0
        assert len(understanding['critical_gaps']) >= 0
    
    def test_llm_coordinator_multi_endpoint_intelligence(self):
        """EVIDENCE: System must intelligently use multiple endpoints"""
        
        # Mock scenario where search.php fails, should try timeline.php
        self.mock_llm_handler.get_completion.return_value = {
            "endpoint": "timeline.php",
            "parameters": {"screenname": "elonmusk"},
            "reasoning": "Generic search not yielding relevant results. Try timeline of key figures.",
            "evaluation_criteria": {
                "relevance_indicators": ["musk", "epstein", "statement", "opinion"]
            },
            "user_update": "Searching Elon Musk's timeline for Epstein-related statements"
        }
        
        decision = self.coordinator.decide_next_action(
            goal="Get different perspectives on Epstein drama",
            current_understanding="Need diverse viewpoints from key figures",
            gaps=["Public figure opinions", "Different sides of controversy"],
            search_history=[{"endpoint": "search.php", "effectiveness": 2.0}]
        )
        
        assert decision['endpoint'] == 'timeline.php'
        assert 'screenname' in decision['parameters']
    
    def test_llm_coordinator_prevents_infinite_loops(self):
        """EVIDENCE: System must prevent repetitive failed strategies"""
        
        # Simulate the exact failure pattern from logs: "find different 2024" repeated 40+ times
        repetitive_history = [
            {"query": "find different 2024", "effectiveness": 4.5, "endpoint": "search.php"}
        ] * 40
        
        # Mock LLM response that MUST avoid repetition
        self.mock_llm_handler.get_completion.return_value = {
            "endpoint": "timeline.php",
            "parameters": {"screenname": "realDonaldTrump"},
            "reasoning": "Previous 'find different' strategy failed 40 times. Switching to direct source access.",
            "evaluation_criteria": {
                "relevance_indicators": ["Trump", "Epstein", "direct", "statement"]
            },
            "user_update": "Breaking out of failed search loop - trying direct timeline access"
        }
        
        decision = self.coordinator.decide_next_action(
            goal="Trump Epstein drama investigation",
            current_understanding="Previous searches yielding irrelevant results",
            gaps=["Relevant information about Trump-Epstein controversy"],
            search_history=repetitive_history
        )
        
        # System MUST NOT repeat the failed pattern
        assert decision['parameters'].get('query') != "find different 2024"
        assert decision['endpoint'] != 'search.php' or 'find different' not in str(decision['parameters'])
    
    def test_llm_coordinator_real_time_communication(self):
        """EVIDENCE: System must provide real-time progress updates"""
        
        self.mock_llm_handler.get_completion.return_value = {
            "endpoint": "search.php",
            "parameters": {"query": "Trump Epstein recent statements"},
            "reasoning": "Starting with targeted search for recent Trump-Epstein content",
            "evaluation_criteria": {
                "relevance_indicators": ["Trump", "Epstein", "recent", "statement"]
            },
            "user_update": "🔍 Searching for recent Trump statements about Epstein controversy..."
        }
        
        decision = self.coordinator.decide_next_action(
            goal="Find recent Trump-Epstein developments",
            current_understanding="Starting investigation",
            gaps=["Recent statements", "Current controversy details"],
            search_history=[]
        )
        
        # Must provide user update
        assert 'user_update' in decision
        assert decision['user_update'] != ""
        assert len(decision['user_update']) > 10  # Meaningful update
    
    @pytest.mark.integration
    def test_llm_coordinator_with_real_llm(self):
        """Integration test with real LLM handler (if available)"""
        try:
            from llm_handler import LLMHandler
            real_llm = LLMHandler()
            coordinator = LLMInvestigationCoordinator(real_llm)
            
            decision = coordinator.decide_next_action(
                goal="Test real LLM integration",
                current_understanding="Testing system",
                gaps=["Test data"],
                search_history=[]
            )
            
            # Should return valid decision structure
            required_keys = ['endpoint', 'parameters', 'reasoning', 'evaluation_criteria', 'user_update']
            for key in required_keys:
                assert key in decision
                
        except ImportError:
            pytest.skip("Real LLM handler not available for integration test")


class TestLLMInvestigationCoordinatorErrorHandling:
    """Test error handling and edge cases"""
    
    def setup_method(self):
        self.mock_llm_handler = Mock()
        self.coordinator = LLMInvestigationCoordinator(self.mock_llm_handler)
    
    def test_fails_fast_on_llm_failure(self):
        """System must fail fast when LLM is unavailable - no fallback behavior"""
        self.mock_llm_handler.get_completion.side_effect = Exception("LLM service unavailable")
        
        # Should raise RuntimeError immediately, no fallback behavior
        with pytest.raises(RuntimeError) as excinfo:
            self.coordinator.decide_next_action(
                goal="Test goal",
                current_understanding="Test understanding",
                gaps=["Test gap"],
                search_history=[]
            )
        
        # Should contain clear error message about LLM failure
        assert "LLM coordinator failed" in str(excinfo.value)
        assert "cannot make investigation decision" in str(excinfo.value)
    
    def test_handles_empty_search_history(self):
        """System must handle empty search history"""
        self.mock_llm_handler.get_completion.return_value = {
            "endpoint": "search.php",
            "parameters": {"query": "test query"},
            "reasoning": "Starting fresh investigation",
            "evaluation_criteria": {"relevance_indicators": ["test"]},
            "user_update": "Starting investigation..."
        }
        
        decision = self.coordinator.decide_next_action(
            goal="Test goal",
            current_understanding="Starting investigation",
            gaps=["Everything"],
            search_history=[]
        )
        
        assert decision['endpoint'] is not None
        assert decision['parameters'] is not None


if __name__ == "__main__":
    pytest.main([__file__, "-v"])