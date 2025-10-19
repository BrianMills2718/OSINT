# Clean GPT-5-mini with LiteLLM Examples

This directory contains clean, focused examples for using OpenAI's gpt-5-mini model with LiteLLM.

## Essential Files

### Core Example
- **`litellm_gpt_5_mini.py`** - Primary working example showing:
  - Basic text generation
  - JSON schema with strict validation
  - Array handling and enum constraints
  - Proper response extraction

### Production Integration
- **`test_final_working.py`** - Production-ready unified wrapper:
  - Automatic API detection (responses vs completion)
  - Parameter conversion and error handling
  - Ready for UnifiedLLMProvider integration

### Debugging & Performance
- **`test_background_mode.py`** - Background execution and timeout handling
- **`test_exact_hanging_calls.py`** - AutoCoder-specific debugging with real prompts
- **`test_async_wrapper_comparison.py`** - Statistical performance analysis

### Documentation
- **`UNDERSTANDING.md`** - Comprehensive guide to gpt-5-mini API differences

## Quick Start

```bash
# Basic example
python3 litellm_gpt_5_mini.py

# Production wrapper test
python3 test_final_working.py

# Debug timeout issues
python3 test_background_mode.py
```

## Key API Differences

- **Traditional models**: Use `litellm.completion()`
- **gpt-5-mini**: Uses `litellm.responses()`
- **Response times**: 22-89 seconds for component generation (tested)
- **Token parameter**: `max_completion_tokens` instead of `max_tokens`

## ⏱️ **Performance Data (October 2025)**

**Comprehensive timing tests conducted** - see `timing_tests/` and `TIMING_CONCLUSIONS.md`:

| Task Type | Time Range | Average | Use Case |
|-----------|------------|---------|----------|
| Simple tasks | 1.6-16.6s | 4.7s | Basic validation |
| **Component generation** | **22.4-89.0s** | **54.6s** | **Real AutoCoder workload** |
| Complex systems | 91.1-101.3s | 96.2s | Edge cases |

**Key Finding**: AutoCoder's 60s timeout was insufficient - increased to 150s based on test data.

## Archive

Redundant files moved to `archive/` folder to maintain clean examples.