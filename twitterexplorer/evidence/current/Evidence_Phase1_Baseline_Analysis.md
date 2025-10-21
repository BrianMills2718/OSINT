# Evidence: Phase 1 - Current CLI Behavior Baseline Analysis

## Executive Summary
Analysis of current TwitterExplorer CLI investigation system identifying 4 critical issues that must be resolved before Streamlit integration.

## Raw Evidence Source
**File**: `C:\Users\Brian\projects\twitterexplorer\temp1.txt`  
**CLI Command**: `python cli_test.py "does joe rogan propagate disinformation"`
**Execution Time**: 06:36:20 → 06:46:09 (9 minutes 49 seconds)
**Total Searches**: 15 searches, 574 results  
**Final Satisfaction**: 0.35

## Issue #1: Streamlit Import Contamination 
**Evidence Lines**: 43-46 in temp1.txt
```
2025-09-09 06:37:05.450 
  Warning: to view this Streamlit app on a browser, run it with the following
  command:

    streamlit run cli_test.py [ARGUMENTS]
```

**Analysis**: 
- CLI execution unexpectedly imports Streamlit modules
- Performance impact: Unknown (needs measurement)
- Deployment risk: CLI depends on UI framework

**Root Cause Hypothesis**: One of the investigation engine components imports Streamlit

## Issue #2: "Untitled" Insight Generation
**Evidence Lines**: 494-495 in temp1.txt
```
Generated Insights:
  1. Majority of claims are false or unverifiable, indicating a pattern of disseminating potentially misleading information (confidence: 0.7)
  2. Untitled (confidence: N/A)
  3. Untitled (confidence: N/A)
```

**Analysis**:
- 2 out of 3 insights generated without proper titles or confidence scores
- Investigation quality degraded: 66% failure rate for insight generation
- Bridge integration working (12 insights created from first insight, 12 from second)

**Root Cause Hypothesis**: Insight synthesis pipeline not properly parsing LLM structured output

## Issue #3: Placeholder API Parameters
**Evidence Lines**: 285, 293 in temp1.txt
```
Line 285: Call tweet_thread.php (With Params: {'id': 'REPLACE_WITH_TWEET_ID_FROM_TIMELINE'})
Line 293: Call latest_replies.php (With Params: {'id': 'REPLACE_WITH_TWEET_ID_FROM_TIMELINE'})
```

**Analysis**:
- LLM coordinator generating invalid placeholder parameters
- API calls failing with placeholder values instead of real data
- Investigation completeness compromised

**Root Cause Hypothesis**: LLM coordinator prompts not properly instructing parameter resolution

## Issue #4: Missing Model Provider CLI Parameter
**Evidence Lines**: 15, 17 in temp1.txt
```
Line 15: LiteLLM completion() model= gpt-5-mini; provider = openai
Line 17: LiteLLM completion() model= gpt-5-mini; provider = openai
```

**Analysis**:
- CLI hardcoded to use OpenAI provider (likely gpt-4o-mini misreported as gpt-5-mini)
- No command-line parameter to switch to Gemini
- Streamlit integration will require provider switching capability

**Root Cause Hypothesis**: InvestigationConfig doesn't expose model_provider parameter

## Positive Findings - Architecture Working Correctly

### ✅ Bridge Integration Functioning
**Evidence Lines**: 158-167
```
Line 158: Bridge notification: Insight created
Line 159: Bridge calling detect_emergent_questions with 1 insights  
Line 167: Bridge integration: Created 12 emergent questions, 12 SPAWNS edges
```

### ✅ Multi-Round Intelligence Working  
**Evidence Lines**: 358-367
```
Line 358: Bridge calling detect_emergent_questions with 6 insights
Line 367: Bridge integration: Created 12 emergent questions, 12 SPAWNS edges
```

### ✅ Graph State Properly Populated
**Evidence Lines**: 488-490
```
Graph State:
  DataPoints: 2
  Insights: 12
  Emergent Questions: 24
```

### ✅ Sophisticated Search Strategy
**Evidence Lines**: 40-41
```
Endpoint diversity score: 0.82
Endpoints used: ['search.php', 'timeline.php', 'followers.php', 'affilates.php']
```

## Performance Baseline Metrics
- **Total Execution Time**: 9 minutes 49 seconds
- **LLM API Calls**: ~20 calls to OpenAI (estimated from logs)
- **Twitter API Calls**: 15 searches across 8 different endpoints
- **Graph Export**: Successfully generated HTML and JSON files
- **Session Logging**: Complete session logged to structured files

## Files Generated During Investigation
```
investigation_graph_0c9d81d7-65cb-4848-a72c-5ec5c841c20e.json
investigation_graph_0c9d81d7-65cb-4848-a72c-5ec5c841c20e.html
logs/sessions/2025-09-09/0c9d81d7-65cb-4848-a72c-5ec5c841c20e.jsonl
logs/sessions/2025-09-09/0c9d81d7-65cb-4848-a72c-5ec5c841c20e_summary.json
```

## Test Requirements Definition

Based on this baseline analysis, the following tests must be created:

### Test #1: Import Isolation
```python
def test_cli_has_no_streamlit_imports():
    """CLI execution should produce no Streamlit-related output"""
    # Should pass: No Streamlit warnings in CLI output
```

### Test #2: Insight Quality  
```python
def test_all_insights_have_titles_and_confidence():
    """All generated insights must have meaningful titles and numeric confidence"""
    # Should pass: 0 insights with "Untitled" or "N/A" confidence
```

### Test #3: Parameter Validity
```python
def test_no_placeholder_api_parameters():
    """All API parameters must be concrete values, no placeholders"""
    # Should pass: 0 API calls with "REPLACE_WITH_" parameters
```

### Test #4: Provider Configuration
```python
def test_cli_accepts_provider_parameter():
    """CLI must accept --provider flag and use specified model provider"""
    # Should pass: CLI with --provider gemini uses Gemini models
```

## Next Phase Requirements
1. Create failing tests that capture each issue
2. Implement fixes to make tests pass
3. Validate no regression in architectural integration
4. Measure performance impact of fixes (<5% degradation acceptable)

## Evidence Validation
- ✅ Raw CLI output captured in temp1.txt
- ✅ Issues identified with specific line number references
- ✅ Positive architectural behavior documented
- ✅ Performance baseline established
- ✅ Clear test requirements defined