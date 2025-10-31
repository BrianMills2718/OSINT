# Gemini 2.5 Flash-Lite Timing Tests

This directory contains timing tests for Gemini 2.5 Flash-Lite to compare performance against GPT-5-mini.

## Files

- `basic_timing_test_gemini.py` - Basic response time tests for simple prompts
- `component_generation_timing_gemini.py` - Component generation timing tests  
- `run_all_tests_gemini.py` - Runs all tests and compares with GPT-5-mini results
- `results/` - JSON results files with detailed timing data

## Usage

### Run Individual Tests
```bash
# Basic timing tests
python3 basic_timing_test_gemini.py

# Component generation tests  
python3 component_generation_timing_gemini.py
```

### Run Full Test Suite with Comparison
```bash
python3 run_all_tests_gemini.py
```

## Test Categories

### Basic Timing Tests
- Simple math problems
- Basic code generation
- Factual questions
- One-liner responses

### Component Generation Tests  
- Simple Store Component (Low complexity)
- API Endpoint Component (Medium complexity)
- Complex Controller Component (High complexity)
- Data Transformer Component (Medium complexity)
- Message Consumer Component (Medium complexity)
- Simple Filter Component (Low complexity)
- Event Aggregator Component (High complexity)

## Comparison Metrics

The tests compare:
- **Average response time** - Mean duration across all tests
- **Maximum response time** - Worst-case performance
- **Success rate** - Percentage of successful completions
- **Code generation quality** - Lines of code produced
- **Speedup factor** - How much faster Gemini is vs GPT-5-mini

## Model Configuration

- **Model**: `gemini/gemini-2.5-flash-lite` 
- **API**: LiteLLM with Google AI Studio
- **API Key**: Hardcoded for testing (will be moved to environment variables)

## Results Analysis

Results include:
- Raw timing data for each test
- Statistical analysis (min, max, average, median)
- Performance recommendations for timeout values
- Side-by-side comparison with GPT-5-mini results
- Speedup calculations and performance insights