# Understanding gpt-5-mini with LiteLLM

## Overview

This directory contains examples and tests for using OpenAI's new gpt-5-mini model with LiteLLM. The key difference is that gpt-5-mini uses a new `responses()` API instead of the traditional `completion()` API.

## Key Differences: gpt-5-mini vs Traditional Models

### 1. API Method
- **Traditional models** (gpt-4, gpt-3.5-turbo): Use `litellm.completion()`
- **gpt-5-mini**: Uses `litellm.responses()`

### 2. Input Format
- **Traditional**: Pass messages array with roles (system, user, assistant)
- **gpt-5-mini**: Concatenates messages into a single `input` string

### 3. Token Limits
- **Traditional**: Uses `max_tokens` parameter
- **gpt-5-mini**: Uses `max_completion_tokens` parameter (our fix implemented this)

### 4. Response Format
- **Traditional**: Simple JSON with choices array
- **gpt-5-mini**: Complex nested structure with output items

### 5. Structured Output
- **Traditional**: Uses `response_format` parameter
- **gpt-5-mini**: Uses `text` parameter with JSON Schema format

## File Descriptions

### Core Working Examples

1. **litellm_gpt_5_mini.py** (WORKING)
   - Basic examples of all gpt-5-mini features
   - Shows freeform text, JSON schema, arrays, and enums
   - Includes helper function for response extraction

2. **test_final_working.py**
   - Production-ready unified wrapper
   - Automatically detects model type and uses correct API
   - Handles both traditional and gpt-5 models seamlessly
   - Ready for integration into UnifiedLLMProvider

### Testing and Debugging

3. **test_background_mode.py**
   - Tests background/async execution to solve timeout issues
   - Explores polling mechanisms for long-running requests
   - Provides recommendations for timeout handling

4. **test_exact_hanging_calls.py**
   - Identifies exact points where API calls hang
   - Useful for debugging timeout issues

5. **test_async_wrapper_comparison.py**
   - Compares async vs sync implementations
   - Performance testing

### API Testing

6. **test_unified_api.py**
   - Tests unified API approach
   - Shows how to handle both model types

7. **test_working_unified.py**
   - Working version of unified API
   - Includes error handling

8. **test_simple_api.py** / **test_api_debug.py**
   - Simple debugging scripts
   - Minimal test cases

## Key Implementation Details

### 1. Model Detection
```python
def is_responses_api_model(model: str) -> bool:
    # gpt-5-mini and future gpt-5 models use responses API
    return 'gpt-5' in model.lower()
```

### 2. Message Conversion
```python
def convert_messages_to_input(messages: List[Dict[str, str]]) -> str:
    # Concatenates messages into single input string
    parts = []
    for msg in messages:
        if msg['role'] == 'system':
            parts.append(f"System: {msg['content']}")
        elif msg['role'] == 'assistant':
            parts.append(f"Assistant: {msg['content']}")
        else:  # user
            parts.append(msg['content'])
    return "\n\n".join(parts)
```

### 3. Response Extraction
```python
def extract_responses_content(response) -> str:
    # Navigate complex response structure
    for item in response.output:
        if item.type == 'message':
            for content in item.content:
                if hasattr(content, 'text'):
                    return content.text
```

### 4. Structured Output with JSON Schema
```python
text_format = {
    "format": {
        "type": "json_schema",
        "name": "response",
        "schema": {
            "type": "object",
            "properties": {...},
            "required": [...],
            "additionalProperties": False
        },
        "strict": True
    }
}
```

## Integration Status

### What We Fixed in UnifiedLLMProvider:
1. ✅ Disabled responses() API usage (returned False)
2. ✅ Changed max_tokens to max_completion_tokens for gpt-5
3. ✅ Made gpt-5-mini use standard completion() API

### Current Implementation:
- gpt-5-mini now works with standard completion() API
- Takes ~100 seconds per component generation
- Successfully generates components with proper inheritance

## Performance Considerations

### Timeout Issues:
- gpt-5-mini responses take 80-100+ seconds
- Background mode explored but not needed with current fix
- Extended timeouts (300s) work reliably

### Recommendations:
1. For MVP: Keep current implementation with long timeouts
2. Post-MVP: Consider switching to faster models (gpt-4-turbo)
3. Alternative: Use native OpenAI client with background mode

## OpenAI Native Examples

The `openai_native/` directory contains:
- Direct OpenAI client examples
- Background mode documentation
- Structured output examples with strict schemas
- CFG (Context-Free Grammar) examples for constrained generation

## Summary

The gpt-5-mini examples show that while the model has a new API design, we successfully integrated it into our system by:
1. Making it use the standard completion() API
2. Handling the max_completion_tokens parameter difference
3. Accepting the longer response times for MVP

The examples in this directory serve as reference for the original intended API usage, though we're currently using a compatibility approach that works well for our needs.