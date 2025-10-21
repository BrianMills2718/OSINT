# LiteLLM Structured Output Configuration Fix

## Problems Identified

1. **Incorrect Structured Output Implementation**
   - Was manually appending schema to prompt as text
   - Was using `response_format = {"type": "json_object"}` only
   - Was trying to parse JSON manually from string response

2. **Not Using Native LiteLLM Structured Output**
   - Should use `response_schema` field in `response_format`
   - LiteLLM handles schema injection internally

3. **Missing Client-Side Validation**
   - Should enable `litellm.enable_json_schema_validation = True`

## Fixes Applied

### 1. Fixed llm_client.py (lines 82-91)

**Before (WRONG):**
```python
if response_format:
    # Use LiteLLM's native JSON object response format
    completion_params["response_format"] = {"type": "json_object"}
    
    # Add schema guidance to the prompt (like universal_llm.py does)
    if completion_params["messages"] and len(completion_params["messages"]) > 0:
        last_message = completion_params["messages"][-1]
        if last_message.get("role") == "user":
            schema_str = response_format.model_json_schema()
            last_message["content"] = f"{last_message['content']}\n\nRespond with valid JSON matching this schema: {schema_str}"
```

**After (CORRECT):**
```python
if response_format:
    # Use LiteLLM's native structured output with Pydantic schema
    # This is the PROPER way - pass the schema directly to response_format
    completion_params["response_format"] = {
        "type": "json_object",
        "response_schema": response_format.model_json_schema()
    }
    
    # NO manual prompt modification needed - LiteLLM handles this internally!
```

### 2. Enabled Client-Side Validation (lines 15-20)

**Added:**
```python
import litellm
from litellm import completion
# Enable client-side JSON schema validation for better compatibility
litellm.enable_json_schema_validation = True
```

### 3. Verified No max_tokens Constraints

Confirmed that `max_tokens` is only used for context management, not output limiting:
- `graph_aware_llm_coordinator.py`: Only for context window management (50,000 tokens)
- `state_manager.py`: Only for history management (800,000 tokens)
- No `max_tokens` parameter passed to completion calls

## Benefits

1. **Proper Native Structured Output**: LiteLLM handles schema injection and validation internally
2. **Better Reliability**: Client-side validation catches schema mismatches
3. **No Token Limits**: Gemini's 1M token limit is not artificially constrained
4. **Cleaner Code**: No manual prompt manipulation needed

## Testing Required

To test with a real API key:
1. Add valid `GEMINI_API_KEY` to `.env` file
2. Run `python test_structured_output_fix.py`
3. Verify structured output parsing works consistently

## Expected Impact

This should resolve the intermittent "LLM returned no parsed structured output" errors by:
- Using the proper LiteLLM API for structured output
- Enabling validation to catch issues early
- Letting LiteLLM handle schema injection internally
- Not artificially limiting output size

## Notes

- Gemini 2.5 has native structured output support
- Some older Gemini models may have limited structured output capability
- The `response_schema` field is the correct way to pass Pydantic schemas
- Client-side validation helps with compatibility across different model versions