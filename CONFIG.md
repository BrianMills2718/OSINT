# Configuration System Documentation

## Overview

The AI Research System uses a centralized configuration system that makes all parameters configurable without touching code. This leverages **LiteLLM's provider flexibility**, allowing you to switch between OpenAI, Anthropic, Google, local models, and 100+ other providers just by changing model names.

## Quick Start

1. **Use defaults** (no setup needed):
   ```bash
   # System uses config_default.yaml automatically
   python test_intelligent_research.py
   ```

2. **Customize settings**:
   ```bash
   # Copy default config
   cp config_default.yaml config.yaml

   # Edit config.yaml with your preferences
   nano config.yaml
   ```

3. **Override with environment variables**:
   ```bash
   export RESEARCH_LLM_MODEL="claude-3-5-sonnet-20241022"
   export RESEARCH_MAX_CONCURRENT=20
   ```

## Configuration File

### Location
- **Default**: `config_default.yaml` (shipped with system, don't edit)
- **User**: `config.yaml` (your custom settings, overrides defaults)

### File Structure

```yaml
llm:
  default_model: "gpt-5-mini"      # Default for all operations

  query_generation:                # Database query generation
    model: "gpt-5-mini"
    temperature: 0.7
    max_tokens: 500

  refinement:                      # Query refinement
    model: "gpt-5-mini"
    temperature: 0.8
    max_tokens: 500

  analysis:                        # Result analysis
    model: "gpt-5-mini"
    temperature: 0.3
    max_tokens: 1500

  synthesis:                       # Final answer synthesis
    model: "gpt-5-mini"
    temperature: 0.5
    max_tokens: 2000

  code_generation:                 # Adaptive code generation
    model: "gpt-5-mini"
    temperature: 0.2
    max_tokens: 1000

execution:
  max_concurrent: 10               # Parallel API calls
  max_refinements: 2               # Query refinement iterations
  default_result_limit: 10         # Results per database
  enable_adaptive_analysis: true   # Ditto-style code generation
  enable_auto_refinement: true     # Auto-refine poor queries

timeouts:
  api_request: 30                  # External API timeouts (seconds)
  llm_request: 60                  # LLM API timeouts
  code_execution: 30               # Generated code timeout
  total_search: 300                # Total search timeout (5 min)

databases:
  sam:
    enabled: true
    timeout: 30
    default_date_range_days: 60

  usajobs:
    enabled: true
    timeout: 20
    results_per_page: 100

  dvids:
    enabled: true
    timeout: 20
    default_date_range_days: 90

  clearancejobs:
    enabled: true
    requires_puppeteer: true
    timeout: 45

provider_fallback:
  enabled: false                   # Auto-retry with different providers
  fallback_models:
    - "gpt-4o-mini"
    - "claude-3-5-sonnet-20241022"
    - "gemini/gemini-2.0-flash-exp"

cost_management:
  max_cost_per_query: 0.50        # USD limit per query
  track_costs: true
  warn_on_expensive_queries: true

logging:
  level: "INFO"                   # DEBUG, INFO, WARNING, ERROR
  log_llm_calls: true
  log_api_calls: true
  log_file: "research.log"
  log_to_stdout: true
```

## Switching Providers

### OpenAI (default)
```yaml
llm:
  default_model: "gpt-5-mini"           # Latest/best
  # OR
  default_model: "gpt-4o"               # More capable
  # OR
  default_model: "gpt-4o-mini"          # Cheaper
```

### Anthropic (Claude)
```yaml
llm:
  default_model: "claude-3-5-sonnet-20241022"  # Latest Sonnet
  # OR
  default_model: "claude-3-opus-20240229"      # Most capable
  # OR
  default_model: "claude-3-haiku-20240307"     # Fastest/cheapest
```

### Google (Gemini)
```yaml
llm:
  default_model: "gemini/gemini-2.0-flash-exp"   # Latest experimental
  # OR
  default_model: "gemini/gemini-1.5-pro"         # Stable pro
```

### Local Models (Ollama)
```yaml
llm:
  default_model: "ollama/llama3"        # Llama 3
  # OR
  default_model: "ollama/mistral"       # Mistral
  # OR
  default_model: "ollama/codellama"     # Code-focused
```

### Mix & Match
You can use different providers for different operations:

```yaml
llm:
  query_generation:
    model: "gpt-5-mini"                      # Fast queries with OpenAI

  analysis:
    model: "claude-3-5-sonnet-20241022"      # Deep analysis with Claude

  code_generation:
    model: "ollama/codellama"                # Local code generation
```

## Environment Variables

Override any setting via environment variables:

```bash
# Change default model
export RESEARCH_LLM_MODEL="claude-3-opus-20240229"

# Increase concurrency
export RESEARCH_MAX_CONCURRENT=20

# Increase refinement iterations
export RESEARCH_MAX_REFINEMENTS=3

# Increase timeout
export RESEARCH_TIMEOUT=600  # 10 minutes
```

## Fallback Configuration

Enable automatic fallback to alternative providers if primary fails:

```yaml
provider_fallback:
  enabled: true
  fallback_models:
    - "gpt-4o-mini"                     # Try this first
    - "claude-3-5-sonnet-20241022"      # Then this
    - "gemini/gemini-2.0-flash-exp"     # Then this
```

This provides resilience - if OpenAI is down, automatically try Anthropic, then Google.

## Cost Management

### Set Limits
```yaml
cost_management:
  max_cost_per_query: 0.50              # Abort if query exceeds $0.50
  track_costs: true                     # Log all costs
  warn_on_expensive_queries: true       # Warn at 50% of max
```

### Monitor Costs
Costs are logged in `research.log` and tracked via LiteLLM's built-in cost tracking.

## Database Configuration

### Enable/Disable Databases
```yaml
databases:
  sam:
    enabled: false      # Disable SAM.gov searches
```

### Per-Database Timeouts
```yaml
databases:
  sam:
    timeout: 60         # SAM.gov can be slow, increase timeout

  clearancejobs:
    timeout: 90         # Puppeteer needs more time
```

### Date Ranges
```yaml
databases:
  sam:
    default_date_range_days: 90        # Look back 90 days by default

  dvids:
    default_date_range_days: 180       # 6 months for military media
```

## Performance Tuning

### High Throughput
```yaml
execution:
  max_concurrent: 20                    # More parallel requests
  max_refinements: 1                    # Fewer iterations

timeouts:
  total_search: 600                     # Allow more time
```

### High Quality
```yaml
execution:
  max_concurrent: 5                     # Fewer parallel (more careful)
  max_refinements: 3                    # More iterations

llm:
  query_generation:
    model: "gpt-4o"                     # Better model
    temperature: 0.3                    # More deterministic
```

### Cost Optimization
```yaml
llm:
  default_model: "ollama/llama3"        # Free local model

execution:
  enable_adaptive_analysis: false       # Disable code generation
  max_refinements: 1                    # Fewer LLM calls
```

## Code Usage

### Accessing Configuration
```python
from config_loader import config

# Get model for operation
model = config.get_model("query_generation")

# Get model with params
params = config.get_model_params("analysis")
# Returns: {"model": "gpt-5-mini", "temperature": 0.3, "max_tokens": 1500}

# Get timeout
timeout = config.get_timeout("api_request")

# Get database config
db_config = config.get_database_config("sam")

# Check if database enabled
if config.is_database_enabled("sam"):
    # Use SAM.gov

# Get execution params
max_concurrent = config.max_concurrent
max_refinements = config.max_refinements
```

### Overriding in Code
```python
# Use config defaults
executor = AgenticExecutor()

# Override specific values
executor = AgenticExecutor(max_concurrent=20, max_refinements=1)
```

## Examples

### Example 1: Development (Fast & Cheap)
```yaml
llm:
  default_model: "ollama/llama3"        # Free local model

execution:
  max_concurrent: 3
  max_refinements: 1
  enable_adaptive_analysis: false

logging:
  level: "DEBUG"                        # Verbose logging
```

### Example 2: Production (Accurate & Reliable)
```yaml
llm:
  default_model: "gpt-5-mini"

provider_fallback:
  enabled: true                         # Auto-retry on failure
  fallback_models:
    - "gpt-4o-mini"
    - "claude-3-5-sonnet-20241022"

execution:
  max_concurrent: 10
  max_refinements: 2
  enable_adaptive_analysis: true

cost_management:
  max_cost_per_query: 1.00             # Higher limit for production

logging:
  level: "INFO"
  log_file: "production.log"
```

### Example 3: Research (Maximum Quality)
```yaml
llm:
  query_generation:
    model: "gpt-4o"                     # Best model
    temperature: 0.5

  analysis:
    model: "claude-3-opus-20240229"     # Claude for analysis
    temperature: 0.2

  synthesis:
    model: "gpt-4o"
    temperature: 0.6

execution:
  max_concurrent: 5                     # Careful, not fast
  max_refinements: 3                    # Multiple iterations

timeouts:
  total_search: 900                     # 15 minutes
```

## Troubleshooting

### Config not loading
```python
from config_loader import config
print(config.get_raw_config())          # Debug: see loaded config
```

### Model not supported
Check LiteLLM docs: https://docs.litellm.ai/docs/providers

### Fallback not working
```yaml
provider_fallback:
  enabled: true                         # Must be true!
```

### Costs too high
```yaml
llm:
  default_model: "gpt-4o-mini"         # Switch to cheaper model

cost_management:
  max_cost_per_query: 0.10              # Lower limit
```

## See Also

- `config_default.yaml` - Default configuration
- `llm_utils.py` - LLM wrapper with fallback support
- LiteLLM Docs: https://docs.litellm.ai/
