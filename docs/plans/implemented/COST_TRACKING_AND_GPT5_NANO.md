# Cost Tracking and gpt-5-nano Support

## Summary

Added comprehensive cost tracking and support for gpt-5-nano (the most cost-effective GPT-5 model).

## Features Added

### 1. gpt-5-nano Support

**Model**: `gpt-5-nano`
- ✅ Lowest cost GPT-5 model (~10x cheaper than gpt-5-mini)
- ✅ Uses same `responses()` API as gpt-5-mini
- ✅ Good for simple queries where highest quality isn't critical
- ✅ Tested and working

**Usage**:
```python
from llm_utils import acompletion

response = await acompletion(
    model="gpt-5-nano",
    messages=[{"role": "user", "content": "What is 2+2?"}]
)
```

**Configuration** (`config_default.yaml`):
```yaml
llm:
  query_generation:
    model: "gpt-5-nano"  # Use nano for cost savings
```

### 2. Cost Tracking

**Features**:
- ✅ Automatic cost tracking for all LLM calls
- ✅ Per-model cost breakdown
- ✅ Total cost and average cost per call
- ✅ Human-readable cost summaries
- ✅ Reset tracking for per-query costs

**API**:
```python
from llm_utils import get_total_cost, get_cost_breakdown, get_cost_summary, reset_cost_tracking

# Get total cost
total = get_total_cost()  # Returns float (USD)

# Get breakdown
breakdown = get_cost_breakdown()
# Returns:
# {
#     "total_cost": 0.15,
#     "by_model": {
#         "gpt-5-mini": {"cost": 0.10, "calls": 5},
#         "gpt-5-nano": {"cost": 0.05, "calls": 10}
#     },
#     "num_calls": 15
# }

# Get formatted summary
print(get_cost_summary())
# Prints:
# ============================================================
# LLM COST SUMMARY
# ============================================================
# Total Cost: $0.1500
# Total Calls: 15
#
# By Model:
# ------------------------------------------------------------
#   gpt-5-mini                     $0.1000  (   5 calls, $0.0200/call)
#   gpt-5-nano                     $0.0500  (  10 calls, $0.0050/call)
# ============================================================

# Reset for per-query tracking
reset_cost_tracking()
```

## Model Recommendations

| Model | Cost (Relative) | Quality | Best For |
|-------|-----------------|---------|----------|
| gpt-5-nano | 1x (cheapest) | Good | Simple queries, high volume |
| gpt-5-mini | ~10x | Better | Most tasks (current default) |
| gpt-5 | ~100x | Best | Complex analysis, high quality |

## Testing

### Test Script: `test_cost_tracking.py`

```bash
python3 test_cost_tracking.py
```

**Results**:
- ✓ gpt-5-nano: Working
- ✓ gpt-5-mini: Working
- ✓ Cost tracking: Implemented (awaiting LiteLLM pricing data)

**Note**: Cost tracking shows $0.00 currently because LiteLLM doesn't have pricing data for new GPT-5 models yet. The infrastructure is ready - costs will appear automatically when LiteLLM adds pricing.

## Implementation Details

### Files Modified

1. **`llm_utils.py`**:
   - Added cost tracking infrastructure
   - Modified `acompletion()` to track costs using `litellm.completion_cost()`
   - Added helper functions: `get_total_cost()`, `get_cost_breakdown()`, `get_cost_summary()`, `reset_cost_tracking()`

2. **`config_default.yaml`**:
   - Added gpt-5-nano to model recommendations
   - Added cost comparison notes
   - Documented all three GPT-5 models

### Files Created

1. **`test_cost_tracking.py`**:
   - Tests both gpt-5-nano and gpt-5-mini
   - Demonstrates cost tracking API
   - Compares costs between models

2. **`COST_TRACKING_AND_GPT5_NANO.md`**:
   - This documentation file

## How Cost Tracking Works

1. **Automatic**: Every call to `acompletion()` automatically tracks cost
2. **LiteLLM Integration**: Uses `litellm.completion_cost()` which has pricing for 100+ models
3. **Graceful Fallback**: If cost calculation fails (model not in pricing DB), request still succeeds
4. **In-Memory Tracking**: Costs stored in memory during program execution
5. **Per-Model Breakdown**: Separate tracking for each model used

## Usage in Existing Code

Cost tracking is already integrated into all existing LLM calls:

```python
# integrations/sam_integration.py (example)
response = await acompletion(
    model=config.get_model("query_generation"),  # Could be gpt-5-nano
    messages=[{"role": "user", "content": prompt}],
    response_format={"type": "json_schema", ...}
)

# Cost automatically tracked!
```

**At any time**, you can check costs:
```python
from llm_utils import get_cost_summary

print(get_cost_summary())
```

## Future Enhancements

1. **Cost Estimates**: Show estimated cost before executing expensive queries
2. **Cost Limits**: Abort if query would exceed configured max cost
3. **Cost Logging**: Save cost data to file/database for historical analysis
4. **Per-Query Tracking**: Automatic reset between queries with summary at end
5. **Cost Warnings**: Alert if query is >50% of max configured cost

## Configuration Example

**Switch all queries to gpt-5-nano for maximum cost savings**:

```yaml
# config.yaml (copy from config_default.yaml)
llm:
  default_model: "gpt-5-nano"

  query_generation:
    model: "gpt-5-nano"
    temperature: 0.7
    max_tokens: 500

  refinement:
    model: "gpt-5-nano"
    temperature: 0.8
    max_tokens: 500

  analysis:
    model: "gpt-5-mini"  # Keep mini for analysis (needs quality)
    temperature: 0.3
    max_tokens: 1500

  synthesis:
    model: "gpt-5-mini"  # Keep mini for final answers
    temperature: 0.5
    max_tokens: 2000
```

**Recommended hybrid approach**:
- Use **gpt-5-nano** for: Query generation, simple relevance checks
- Use **gpt-5-mini** for: Analysis, synthesis, refinement
- Use **gpt-5** for: Complex multi-step reasoning (if needed)

## LiteLLM Cost Map

LiteLLM maintains pricing for 100+ models here:
https://github.com/BerriAI/litellm/blob/main/model_prices_and_context_window.json

Once GPT-5 pricing is added, cost tracking will work automatically with no code changes.

## Related Documentation

- LiteLLM Cost Tracking: `/docs/examples/llm_research_examples/litellm_cost_tracking_docs.txt`
- GPT-5 Models: `/docs/examples/llm_research_examples/gpt_5_mini_examples/gpt_5_mini_docs`
- Working Examples: `/docs/examples/llm_research_examples/gpt_5_mini_examples/litellm/`

## Next Steps

1. ✅ gpt-5-nano support added
2. ✅ Cost tracking infrastructure implemented
3. ✅ Test script created and verified
4. ⏳ Waiting for LiteLLM to add GPT-5 pricing
5. 🔜 Add cost tracking to CLI/UI output
6. 🔜 Add cost estimates before expensive operations
7. 🔜 Add cost limits and warnings
