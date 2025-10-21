# Universal LLM Kit 🚀

Drop this folder into any project for instant access to all major LLM providers with automatic optimization, fallbacks, and smart routing.

## 🎯 What This Gives You

- ✅ **All Major Providers**: OpenAI, Anthropic, Google, OpenRouter, etc.
- ✅ **Code Execution**: Native Gemini code execution support
- ✅ **Function Calling**: Unified interface across all providers
- ✅ **Structured Output**: JSON mode with Pydantic support
- ✅ **Smart Routing**: Cost-based, latency-based automatic model selection
- ✅ **Auto Fallbacks**: Provider fails → automatically tries next provider
- ✅ **Model Constraints**: Handles o1 models, token limits automatically
- ✅ **Maximum Tokens**: Auto-configured per model for optimal output

## 🚀 Quick Setup

1. **Copy this folder** to your project
2. **Install requirements**: `pip install -r requirements.txt`
3. **Setup API keys**: Copy `.env.template` to `.env` and add your keys
4. **Start using**: Import and go!

```python
from universal_llm import chat, code, reason

# Universal chat - auto-selects best model
response = chat("Explain quantum computing")

# Code execution with Gemini
result = code("Calculate fibonacci numbers")

# Complex reasoning with o1 models
solution = reason("Solve this complex math problem...")
```

## 📁 Files

- `universal_llm.py` - Main universal interface
- `demo.py` - Complete demonstration of all features
- `quick_examples.py` - Copy-paste examples for your code
- `.env.template` - API keys template
- `requirements.txt` - Dependencies

## 🔑 API Keys Setup

Copy `.env.template` to `.env` and fill in your keys:

```bash
# Required: At least one of these
OPENAI_API_KEY=your_key_here
ANTHROPIC_API_KEY=your_key_here  
GEMINI_API_KEY=your_key_here

# Optional: Additional providers
OPENROUTER_API_KEY=your_key_here
GROQ_API_KEY=your_key_here
```

## 💻 Usage Examples

### Basic Chat
```python
from universal_llm import chat

response = chat("Write a Python function to reverse a string")
print(response)
```

### Code Execution
```python
from universal_llm import code

# Uses Gemini's native code execution
result = code("Create a bar chart of sales data: Q1=100, Q2=150, Q3=200")
print(result)
```

### Complex Reasoning
```python
from universal_llm import reason

# Uses o1 models for deep reasoning
solution = reason("Analyze the economic implications of AI automation")
print(solution)
```

### Structured Output
```python
from universal_llm import structured
from pydantic import BaseModel

class Product(BaseModel):
    name: str
    price: float
    category: str

result = structured("Create a product for an online store", Product)
print(result)  # Valid JSON matching schema
```

### Model Comparison
```python
from universal_llm import compare

results = compare("Write a haiku about coding", ["smart", "fast", "code"])
for model, response in results.items():
    print(f"{model}: {response}")
```

### Advanced Usage
```python
from universal_llm import UniversalLLM

llm = UniversalLLM()

# Function calling
tools = [{"type": "function", "function": {...}}]
response = llm.function_call("What's the weather?", tools)

# Custom parameters
response = llm.chat("Hello", model_type="smart", temperature=0.7)
```

## 🔄 Automatic Features

### Smart Routing
- **Cost-based**: Automatically uses cheapest model that meets requirements
- **Latency-based**: Routes to fastest responding models
- **Capability-based**: Selects models with required features (code, tools, etc.)

### Automatic Fallbacks
- Primary model fails → tries backup models
- Provider outage → switches to different provider
- Context limit exceeded → uses model with larger context window

### Model Constraints
- o1 models: Automatically removes temperature/tools (not supported)
- Token limits: Auto-configures maximum tokens per model
- Feature detection: Only uses models that support requested features

## 🎯 Model Types

- **`smart`**: Best general-purpose model (GPT-4o, Claude-3.5-Sonnet, Gemini-2.0-Flash)
- **`fast`**: Quick responses (GPT-4o-mini, Claude-3.5-Haiku)
- **`code`**: Code execution enabled (Gemini-2.5-Flash with codeExecution)
- **`reasoning`**: Deep thinking (o1-preview, o1-mini)
- **`thinking`**: Step-by-step reasoning (Gemini-2.0-Flash-Thinking)

## 🚨 Error Handling

The kit includes robust error handling:
- Provider failures → automatic fallback
- API key missing → clear error message
- Rate limits → automatic retry with backoff
- Invalid requests → graceful degradation

## 📊 Cost Optimization

- Uses cheapest available model by default
- Automatically routes expensive requests to capable models only
- Tracks usage and costs (via LiteLLM)
- Provides cost estimates before calls

## 🔧 Customization

Extend the kit for your needs:

```python
# Add custom models
llm = UniversalLLM()
llm.router.model_list.append({
    "model_name": "custom",
    "litellm_params": {"model": "your-custom-model"}
})

# Change routing strategy
llm.router.routing_strategy = "latency-based"  # or "least-busy"
```

## 🎉 Run Demo

```bash
python demo.py
```

This runs all capabilities:
- Basic chat
- Code execution  
- Complex reasoning
- Function calling
- Structured output
- Model comparison
- Advanced features

Perfect for testing your setup and seeing all features in action!

## 🤖 Multi-Agent Consensus System

**NEW**: Advanced consensus system that runs problems through multiple LLMs to find convergence and track opinion dynamics.

### Consensus Features
- ✅ **Multi-Model Analysis**: Run problems through 3+ different LLMs
- ✅ **Convergence Tracking**: Monitor how opinions converge over rounds
- ✅ **Opinion Dynamics**: Track which models influence others
- ✅ **Intelligent Judging**: Claude Sonnet judges similarity and convergence
- ✅ **Configurable**: Customize models, rounds, thresholds
- ✅ **Analysis Tools**: Detailed reports and visualizations

### Quick Consensus Example
```python
from consensus_system import MultiAgentConsensus, ConsensusConfig

config = ConsensusConfig(
    participating_models=["gemini/gemini-2.5-flash", "gpt-4o-mini", "deepseek/deepseek-reasoner"],
    judge_model="claude-3-5-sonnet-20241022",
    max_rounds=5,
    convergence_threshold=0.8
)

consensus = MultiAgentConsensus(config)
result = consensus.run_consensus("What's the best sorting algorithm for 1M integers?")

print(f"Converged: {result['metadata']['converged']}")
print(f"Final positions: {result['final_positions']}")
```

### Consensus System Files
- `consensus_system.py` - Main consensus engine
- `consensus_demo.py` - Multiple demonstration scenarios  
- `consensus_analyzer.py` - Analysis and visualization tools
- `test_consensus.py` - Quick connectivity and functionality tests

### Run Consensus Tests
```bash
# Test system connectivity
python test_consensus.py

# Run technical problem demo
python consensus_demo.py technical

# Run all demo scenarios
python consensus_demo.py all

# Analyze results
python consensus_analyzer.py consensus_result_technical.json
```

---

**Drop this folder into any project and you'll never worry about LLM provider differences again!** 🚀