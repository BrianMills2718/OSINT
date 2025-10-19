# Gemini Structured Output with LiteLLM

This example demonstrates using Gemini 2.0 Flash with structured output via LiteLLM.

## Files

- `gemini_flash_lite_structured.py` - Main example with 3 approaches:
  1. **Pydantic Models** - Type-safe structured output using Pydantic BaseModel
  2. **JSON Schema** - Raw JSON schema for complex structured data
  3. **Simple JSON** - Basic JSON object output

- `list_models.py` - Helper to test which Gemini models are available

## Setup

```bash
pip install litellm pydantic
```

## Usage

```bash
python3 gemini_flash_lite_structured.py
```

## Key Features Demonstrated

✅ **Pydantic Integration** - Type-safe models with automatic validation  
✅ **Complex JSON Schemas** - Nested objects, arrays, required fields  
✅ **Simple JSON Output** - Basic structured responses  
✅ **Error Handling** - Robust error handling and debugging  
✅ **API Key Management** - Environment variable configuration  

## Working Model

- `gemini/gemini-2.0-flash-exp` - Successfully tested and working

## Output Examples

The example successfully generates:
- Person extraction with age, occupation validation
- Recipe data with ingredients, steps, prep time
- Healthcare AI benefits categorized by domain

All responses are properly structured JSON that validates against the defined schemas.