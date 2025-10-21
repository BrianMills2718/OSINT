"""Test suite for FindingEvaluator"""
import pytest
from twitterexplorer.finding_evaluator import FindingEvaluator, FindingAssessment

def test_evaluator_detects_specific_finding():
    """EVIDENCE: Evaluator must identify specific, actionable findings"""
    evaluator = FindingEvaluator()
    
    # Specific finding with date, names, and claims
    specific_result = {
        'text': 'Court documents from March 15, 2002 show Trump and Epstein attended a private party at Mar-a-Lago with 28 guests.',
        'source': 'twitter_search',
        'metadata': {}
    }
    
    assessment = evaluator.evaluate_finding(specific_result, "Trump Epstein relationship")
    
    assert assessment.is_significant == True
    assert assessment.specificity_score > 0.5
    assert assessment.relevance_score > 0.5
    assert 'dates' in assessment.entities
    assert 'March 15, 2002' in str(assessment.entities['dates'])
    assert 'names' in assessment.entities
    assert 'Trump' in assessment.entities['names']
    print(f"[OK] Specific finding detected: {assessment.reasoning}")

def test_evaluator_rejects_generic_content():
    """EVIDENCE: Evaluator must reject generic, unhelpful content"""
    evaluator = FindingEvaluator()
    
    # Generic, unhelpful result
    generic_result = {
        'text': 'Click here to read more about this topic. Subscribe for updates.',
        'source': 'twitter_search',
        'metadata': {}
    }
    
    assessment = evaluator.evaluate_finding(generic_result, "Trump Epstein relationship")
    
    assert assessment.is_significant == False
    assert assessment.specificity_score == 0.0
    assert "generic/unhelpful" in assessment.reasoning.lower()
    print(f"[OK] Generic content rejected: {assessment.reasoning}")

def test_evaluator_extracts_entities():
    """EVIDENCE: Evaluator must extract entities correctly"""
    evaluator = FindingEvaluator()
    
    result = {
        'text': 'On January 15, 2024, the investigation revealed $2.5 million in transactions. John Smith said "This is significant evidence".',
        'source': 'test',
        'metadata': {}
    }
    
    assessment = evaluator.evaluate_finding(result, "financial investigation")
    
    assert 'dates' in assessment.entities
    assert 'amounts' in assessment.entities
    assert '$2.5 million' in str(assessment.entities['amounts'])
    assert 'quotes' in assessment.entities
    assert 'names' in assessment.entities
    assert 'John Smith' in assessment.entities['names']
    print(f"[OK] Entities extracted: {list(assessment.entities.keys())}")

def test_evaluator_suggests_followup():
    """EVIDENCE: Evaluator should suggest follow-up for significant findings"""
    evaluator = FindingEvaluator()
    
    result = {
        'text': 'Documents dated July 4, 2002 mention multiple meetings between the parties.',
        'source': 'test',
        'metadata': {}
    }
    
    assessment = evaluator.evaluate_finding(result, "meeting investigation")
    
    assert assessment.is_significant == True
    assert assessment.suggested_followup is not None
    assert "July 4, 2002" in assessment.suggested_followup or "events around" in assessment.suggested_followup
    print(f"[OK] Follow-up suggested: {assessment.suggested_followup}")

if __name__ == "__main__":
    test_evaluator_detects_specific_finding()
    test_evaluator_rejects_generic_content()
    test_evaluator_extracts_entities()
    test_evaluator_suggests_followup()
    print("\n[SUCCESS] All FindingEvaluator tests passed!")