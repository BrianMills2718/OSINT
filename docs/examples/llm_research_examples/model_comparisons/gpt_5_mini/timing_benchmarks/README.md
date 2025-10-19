# GPT-5-Mini Timing Tests

Isolated timing tests for GPT-5-mini responses to determine optimal timeout settings for AutoCoder4_CC.

## Test Structure

### 🔧 Test Files

- **`basic_timing_test.py`** - Simple prompts (math, basic code) to establish baseline performance
- **`component_generation_timing.py`** - Realistic AutoCoder component generation prompts  
- **`timeout_behavior_test.py`** - Test timeout boundaries with complex prompts
- **`run_all_tests.py`** - Execute all tests and generate comprehensive analysis

### 📊 Results Directory

- **`results/`** - JSON files with detailed timing data and analysis
- **`basic_timing_results_YYYYMMDD_HHMMSS.json`** - Basic test results
- **`component_timing_results_YYYYMMDD_HHMMSS.json`** - Component generation results  
- **`timeout_behavior_results_YYYYMMDD_HHMMSS.json`** - Timeout behavior results
- **`comprehensive_timing_analysis_YYYYMMDD_HHMMSS.json`** - Combined analysis

## Running Tests

### Individual Tests

```bash
# Basic timing (5-15 seconds expected)
python3 basic_timing_test.py

# Component generation (15-45 seconds expected)  
python3 component_generation_timing.py

# Timeout behavior (test 10s, 30s, 60s, 90s, 120s limits)
python3 timeout_behavior_test.py
```

### Comprehensive Analysis

```bash
# Run all tests and generate recommendations
python3 run_all_tests.py
```

## What Each Test Measures

### Basic Timing Test
- **Purpose**: Baseline performance for simple tasks
- **Sample prompts**: "What is 2+2?", "Write hello world", "List 3 colors"
- **Expected range**: 2-15 seconds
- **Use case**: Quick validation and simple operations

### Component Generation Test  
- **Purpose**: Realistic AutoCoder workload timing
- **Sample prompts**: Actual Smart Base Classes component generation prompts
- **Expected range**: 15-60 seconds
- **Use case**: Real-world component generation performance

### Timeout Behavior Test
- **Purpose**: Understand timeout boundaries and failure modes
- **Sample prompts**: Increasingly complex tasks from simple to impossible
- **Timeout ranges**: 10s, 30s, 60s, 90s, 120s
- **Use case**: Optimal timeout setting determination

## Key Metrics

### Response Time Analysis
- **Min/Max/Average/Median** response times
- **95th percentile** (if enough data)
- **Success rate** at different timeout levels
- **Complexity vs time** correlation

### Timeout Recommendations
- **Conservative**: 2x max observed time (handles edge cases)
- **Balanced**: 1.5x max observed time (good reliability) 
- **Aggressive**: 1.2x max observed time (fail fast)

### Code Generation Metrics
- **Lines of code** generated vs time
- **Response quality** vs generation time
- **Complexity classification** (Low/Medium/High)

## Integration with AutoCoder

### Current Settings
```python
# autocoder_cc/core/timeout_manager.py
llm_generation: 60.0  # Current timeout

# autocoder_cc/llm_providers/unified_llm_provider.py  
self.timeout = 60  # Current provider timeout
```

### Applying Results
1. Run comprehensive tests: `python3 run_all_tests.py`
2. Review timeout recommendations in output
3. Update `timeout_manager.py` with recommended values
4. Test with new settings in AutoCoder
5. Monitor production performance

## Expected Results

### Baseline Expectations
- **Simple tasks**: 2-10 seconds
- **Component generation**: 15-45 seconds  
- **Complex systems**: 30-90 seconds
- **Failure point**: 90-120+ seconds

### Success Criteria
- **90%+ success rate** at recommended timeout
- **Reasonable performance** for typical workloads
- **Clear failure modes** for complex requests
- **Data-driven timeout tuning**

## Troubleshooting

### Common Issues
- **API rate limits**: Add delays between requests
- **Authentication**: Ensure OPENAI_API_KEY is set
- **Model availability**: Verify gpt-5-mini-2025-08-07 access
- **Network timeouts**: Check internet connection

### Error Handling
- Tests continue if individual requests fail
- Comprehensive analysis handles partial failures  
- Results saved even if some tests timeout
- Clear error reporting and debugging info

## Analysis Output Example

```
📊 COMPREHENSIVE TIMING ANALYSIS REPORT
===============================================================================
Model: gpt-5-mini-2025-08-07
Total Tests: 22
Successful: 19
Success Rate: 86.4%
Response Time Range: 1.2s - 47.3s

🎯 TIMEOUT RECOMMENDATIONS:
Current Setting: 60s
Max Observed: 47.3s
Avg Observed: 18.7s

Options:
👉 Balanced: 71s - 1.5x max observed (47.3s), good reliability
   Conservative: 95s - 2x max observed (47.3s), handles edge cases  
   Aggressive: 57s - 1.2x max observed (47.3s), fail fast
```

## Next Steps

1. **Establish baseline**: Run tests to understand current performance
2. **Optimize settings**: Apply recommended timeout values  
3. **Monitor production**: Track real-world performance
4. **Iterate**: Re-run tests if performance changes
5. **Scale analysis**: Test with different models/configurations