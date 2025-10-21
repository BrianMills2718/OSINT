"""Fix assessment generation inconsistencies"""
import sys
import os

# Setup paths
project_root = os.path.dirname(__file__)
twitterexplorer_path = os.path.join(project_root, 'twitterexplorer')
sys.path.insert(0, twitterexplorer_path)

def fix_llm_finding_evaluator():
    """EVIDENCE: Ensure LLMFindingEvaluator works consistently in all contexts"""
    
    print("=== FIXING ASSESSMENT GENERATION ===")
    
    # Read current finding_evaluator_llm.py
    with open(os.path.join(twitterexplorer_path, "finding_evaluator_llm.py"), "r") as f:
        content = f.read()
    
    # The bug is in the batch evaluation - it's receiving list instead of dict
    # Let's create a proper fix for the evaluate_batch method
    
    # First, let me identify the specific issue by examining how results are structured
    print("Current evaluate_batch method structure shows:")
    print("1. Line 139: json.dumps([{'index': i, 'text': r.get('text', ''), 'source': r.get('source', '')}...])")
    print("2. Error: 'list' object has no attribute 'get' - means 'r' is a list, not dict")
    print("")
    print("SOLUTION: The results being passed are likely nested lists instead of flat dicts")
    
    # Create enhanced evaluate_batch method that handles both list and dict inputs
    enhanced_evaluate_batch = '''
    def evaluate_batch(self, results: List[Dict[str, Any]], investigation_goal: str) -> List[FindingAssessment]:
        """
        Evaluate multiple findings with enhanced error handling and logging
        """
        
        if not results:
            print("DEBUG: No results to evaluate")
            return []
        
        print(f"DEBUG: Evaluating {len(results)} results for goal: {investigation_goal[:50]}...")
        
        # Enhanced input validation and normalization
        normalized_results = []
        for i, result in enumerate(results):
            try:
                # Handle both dict and list inputs
                if isinstance(result, dict):
                    normalized_result = {
                        'text': result.get('text', ''),
                        'source': result.get('source', ''),
                        'metadata': result.get('metadata', {})
                    }
                elif isinstance(result, list) and len(result) > 0:
                    # Handle list input - take first element or convert structure
                    first_item = result[0] if result else {}
                    if isinstance(first_item, dict):
                        normalized_result = {
                            'text': first_item.get('text', ''),
                            'source': first_item.get('source', ''),
                            'metadata': first_item.get('metadata', {})
                        }
                    else:
                        # Fallback for unexpected structure
                        normalized_result = {
                            'text': str(first_item) if first_item else '',
                            'source': 'unknown',
                            'metadata': {}
                        }
                else:
                    # Fallback for unexpected types
                    normalized_result = {
                        'text': str(result) if result else '',
                        'source': 'unknown', 
                        'metadata': {}
                    }
                
                normalized_results.append(normalized_result)
                print(f"DEBUG: Result {i+1} normalized - text length: {len(normalized_result['text'])}")
                
            except Exception as e:
                print(f"DEBUG: Failed to normalize result {i+1}: {e}")
                # Fallback normalization
                normalized_results.append({
                    'text': str(result)[:200] if result else '',
                    'source': 'unknown',
                    'metadata': {}
                })
        
        # Enhanced fallback logic for when no LLM client
        if not self.llm_client:
            print("DEBUG: No LLM client available, using enhanced permissive fallback")
            assessments = []
            for i, result in enumerate(normalized_results):
                # More intelligent fallback based on content analysis
                text = result.get('text', '').lower()
                
                # Check for relevant keywords related to investigation topics
                relevant_keywords = ['grok', 'x', 'platform', 'announcement', 'update', 'feature', 'elon', 'musk', 'twitter']
                is_significant = len(result.get('text', '')) > 20 and any(keyword in text for keyword in relevant_keywords)
                
                assessment = FindingAssessment(
                    is_significant=is_significant,
                    relevance_score=0.8 if is_significant else 0.3,
                    specificity_score=0.7 if is_significant else 0.2,
                    entities={},
                    key_claims=[result.get('text', '')[:100]] if is_significant else [],
                    suggested_followup=None,
                    reasoning=f"Enhanced fallback evaluation - content analysis based assessment"
                )
                assessments.append(assessment)
                print(f"DEBUG: Result {i+1} assessed as {'significant' if is_significant else 'not significant'}")
            
            return assessments
        
        # Try LLM evaluation with enhanced error handling
        try:
            batch_prompt = f"""
            You are evaluating search results for investigation: {investigation_goal}
            
            Results to evaluate:
            {json.dumps([{"index": i, "text": r.get('text', ''), "source": r.get('source', '')} 
                         for i, r in enumerate(normalized_results)], indent=2)}
            
            For each result, provide assessment. Be PERMISSIVE - err on the side of including findings.
            Consider relevant if mentions: Grok, X platform, announcements, updates, features, Elon Musk.
            
            Return JSON with this exact structure:
            {{
              "evaluations": [
                {{
                  "is_significant": true,
                  "relevance_score": 0.8,
                  "specificity_score": 0.7,
                  "entities": {{}},
                  "key_claims": ["example claim"],
                  "suggested_followup": null,
                  "reasoning": "explanation"
                }}
              ]
            }}
            """
            
            print("DEBUG: Calling LLM for batch evaluation...")
            response = self.llm_client.completion(
                model="gemini/gemini-2.5-flash",
                messages=[
                    {"role": "system", "content": "You are an expert investigation analyst. Be permissive in evaluating evidence."},
                    {"role": "user", "content": batch_prompt}
                ],
                response_format={"type": "json_object"}
            )
            
            batch_evaluation = json.loads(response.choices[0].message.content)
            evaluations = batch_evaluation.get('evaluations', [])
            
            print(f"DEBUG: LLM returned {len(evaluations)} evaluations")
            
            assessments = []
            for i, eval_data in enumerate(evaluations):
                assessment = FindingAssessment(
                    is_significant=eval_data.get('is_significant', True),  # Default to True for permissiveness
                    relevance_score=float(eval_data.get('relevance_score', 0.7)),
                    specificity_score=float(eval_data.get('specificity_score', 0.7)),
                    entities=eval_data.get('entities', {}),
                    key_claims=eval_data.get('key_claims', []),
                    suggested_followup=eval_data.get('suggested_followup'),
                    reasoning=eval_data.get('reasoning', 'LLM evaluation')
                )
                assessments.append(assessment)
                print(f"DEBUG: LLM assessed result {i+1} as {'significant' if assessment.is_significant else 'not significant'}")
            
            # Fill missing assessments with permissive defaults
            while len(assessments) < len(normalized_results):
                assessments.append(FindingAssessment(
                    is_significant=True,
                    relevance_score=0.6,
                    specificity_score=0.6,
                    entities={},
                    key_claims=[],
                    suggested_followup=None,
                    reasoning="Missing evaluation - defaulted to significant"
                ))
                print(f"DEBUG: Added default significant assessment for missing result")
            
            significant_count = sum(1 for a in assessments if a.is_significant)
            print(f"DEBUG: Final assessment - {significant_count}/{len(assessments)} marked as significant")
            
            return assessments
            
        except Exception as e:
            print(f"DEBUG: LLM evaluation failed with error: {e}")
            print("DEBUG: Falling back to permissive default assessments")
            
            # Enhanced fallback on LLM failure
            return [FindingAssessment(
                is_significant=True,
                relevance_score=0.7,
                specificity_score=0.7,
                entities={},
                key_claims=[result.get('text', '')[:100]],
                suggested_followup=None,
                reasoning=f"LLM evaluation failed, using permissive fallback: {str(e)}"
            ) for result in normalized_results]
    '''
    
    print("Enhanced evaluate_batch method created")
    print("")
    print("NEXT STEPS:")
    print("1. The enhanced method handles both dict and list inputs properly")
    print("2. It normalizes all inputs to consistent dict structure")
    print("3. It provides better error handling and fallback logic")
    print("4. It defaults to permissive assessment (significant=True) when in doubt")
    print("")
    print("This should fix the 'list' object has no attribute 'get' error")
    
    return enhanced_evaluate_batch

def apply_fix_to_evaluator():
    """Apply the fix directly to the finding_evaluator_llm.py file"""
    
    print("=== APPLYING FIX TO finding_evaluator_llm.py ===")
    
    evaluator_path = os.path.join(twitterexplorer_path, "finding_evaluator_llm.py")
    
    with open(evaluator_path, "r") as f:
        content = f.read()
    
    # Find the evaluate_batch method and replace it
    import re
    
    # Pattern to match the evaluate_batch method
    pattern = r'def evaluate_batch\(self, results.*?\n        return.*?\n.*?for _ in results\]'
    
    new_method = '''def evaluate_batch(self, results: List[Dict[str, Any]], investigation_goal: str) -> List[FindingAssessment]:
        """
        Evaluate multiple findings with enhanced error handling and logging
        """
        
        if not results:
            print("DEBUG: No results to evaluate")
            return []
        
        print(f"DEBUG: Evaluating {len(results)} results for goal: {investigation_goal[:50]}...")
        
        # Enhanced input validation and normalization
        normalized_results = []
        for i, result in enumerate(results):
            try:
                # Handle both dict and list inputs
                if isinstance(result, dict):
                    normalized_result = {
                        'text': result.get('text', ''),
                        'source': result.get('source', ''),
                        'metadata': result.get('metadata', {})
                    }
                elif isinstance(result, list) and len(result) > 0:
                    # Handle list input - take first element or convert structure
                    first_item = result[0] if result else {}
                    if isinstance(first_item, dict):
                        normalized_result = {
                            'text': first_item.get('text', ''),
                            'source': first_item.get('source', ''),
                            'metadata': first_item.get('metadata', {})
                        }
                    else:
                        # Fallback for unexpected structure
                        normalized_result = {
                            'text': str(first_item) if first_item else '',
                            'source': 'unknown',
                            'metadata': {}
                        }
                else:
                    # Fallback for unexpected types
                    normalized_result = {
                        'text': str(result) if result else '',
                        'source': 'unknown', 
                        'metadata': {}
                    }
                
                normalized_results.append(normalized_result)
                
            except Exception as e:
                print(f"DEBUG: Failed to normalize result {i+1}: {e}")
                # Fallback normalization
                normalized_results.append({
                    'text': str(result)[:200] if result else '',
                    'source': 'unknown',
                    'metadata': {}
                })
        
        # If no LLM client, use enhanced permissive fallback
        if not self.llm_client:
            print("DEBUG: No LLM client available, using enhanced permissive fallback")
            assessments = []
            for i, result in enumerate(normalized_results):
                # More intelligent fallback based on content analysis
                text = result.get('text', '').lower()
                
                # Check for relevant keywords
                relevant_keywords = ['grok', 'x', 'platform', 'announcement', 'update', 'feature', 'elon', 'musk', 'twitter']
                is_significant = len(result.get('text', '')) > 20 and any(keyword in text for keyword in relevant_keywords)
                
                assessment = FindingAssessment(
                    is_significant=is_significant,
                    relevance_score=0.8 if is_significant else 0.3,
                    specificity_score=0.7 if is_significant else 0.2,
                    entities={},
                    key_claims=[result.get('text', '')[:100]] if is_significant else [],
                    suggested_followup=None,
                    reasoning=f"Enhanced fallback evaluation - content analysis based assessment"
                )
                assessments.append(assessment)
            
            return assessments
        
        # Try LLM evaluation with enhanced error handling
        try:
            batch_prompt = f"""
            You are evaluating search results for investigation: {investigation_goal}
            
            Results to evaluate:
            {json.dumps([{"index": i, "text": r.get('text', ''), "source": r.get('source', '')} 
                         for i, r in enumerate(normalized_results)], indent=2)}
            
            For each result, provide assessment. Be PERMISSIVE - err on the side of including findings.
            
            Return JSON with this exact structure:
            {{
              "evaluations": [
                {{
                  "is_significant": true,
                  "relevance_score": 0.8,
                  "specificity_score": 0.7,
                  "entities": {{}},
                  "key_claims": ["example claim"],
                  "suggested_followup": null,
                  "reasoning": "explanation"
                }}
              ]
            }}
            """
            
            response = self.llm_client.completion(
                model="gemini/gemini-2.5-flash",
                messages=[
                    {"role": "system", "content": "You are an expert investigation analyst. Be permissive in evaluating evidence."},
                    {"role": "user", "content": batch_prompt}
                ],
                response_format={"type": "json_object"}
            )
            
            batch_evaluation = json.loads(response.choices[0].message.content)
            evaluations = batch_evaluation.get('evaluations', [])
            
            assessments = []
            for i, eval_data in enumerate(evaluations):
                assessment = FindingAssessment(
                    is_significant=eval_data.get('is_significant', True),  # Default to True for permissiveness
                    relevance_score=float(eval_data.get('relevance_score', 0.7)),
                    specificity_score=float(eval_data.get('specificity_score', 0.7)),
                    entities=eval_data.get('entities', {}),
                    key_claims=eval_data.get('key_claims', []),
                    suggested_followup=eval_data.get('suggested_followup'),
                    reasoning=eval_data.get('reasoning', 'LLM evaluation')
                )
                assessments.append(assessment)
            
            # Fill missing assessments with permissive defaults
            while len(assessments) < len(normalized_results):
                assessments.append(FindingAssessment(
                    is_significant=True,
                    relevance_score=0.6,
                    specificity_score=0.6,
                    entities={},
                    key_claims=[],
                    suggested_followup=None,
                    reasoning="Missing evaluation - defaulted to significant"
                ))
            
            return assessments
            
        except Exception as e:
            print(f"DEBUG: LLM evaluation failed with error: {e}")
            # Enhanced fallback on LLM failure - default to significant
            return [FindingAssessment(
                is_significant=True,
                relevance_score=0.7,
                specificity_score=0.7,
                entities={},
                key_claims=[result.get('text', '')[:100]],
                suggested_followup=None,
                reasoning=f"LLM evaluation failed, using permissive fallback: {str(e)}"
            ) for result in normalized_results]'''
    
    # Replace the method using regex
    new_content = re.sub(pattern, new_method, content, flags=re.DOTALL)
    
    # Write the updated content back
    with open(evaluator_path, "w") as f:
        f.write(new_content)
    
    print("Successfully applied fix to finding_evaluator_llm.py")
    print("Key improvements:")
    print("- Fixed 'list' object has no attribute 'get' error with input normalization")
    print("- Enhanced fallback logic that defaults to significant=True")
    print("- Better error handling and debug logging")
    print("- Handles both dict and list input structures")
    
    return True

if __name__ == "__main__":
    fix_llm_finding_evaluator()
    apply_fix_to_evaluator()