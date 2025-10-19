#!/usr/bin/env python3
"""
Component Generation Timing Test - Realistic AutoCoder component generation prompts
Tests GPT-5-mini response times for actual component generation tasks
"""

import os
import time
import json
import statistics
from datetime import datetime
from dotenv import load_dotenv
import litellm
from typing import List, Dict, Any

# Load environment variables
load_dotenv()

MODEL = "gpt-5-mini-2025-08-07"

def get_text(resp):
    """Extract text from responses() API response"""
    texts = []
    for item in resp.output:
        if hasattr(item, "content"):
            for c in item.content:
                if hasattr(c, "text"):
                    texts.append(c.text)
    return "\n".join(texts)

def time_component_generation(prompt: str, description: str, expected_complexity: str) -> Dict[str, Any]:
    """Time a component generation request"""
    print(f"Testing: {description} ({expected_complexity})")
    print(f"Prompt length: {len(prompt)} chars")
    
    start_time = time.time()
    
    try:
        response = litellm.responses(
            model=MODEL,
            input=prompt,
            text={"format": {"type": "text"}},
        )
        
        end_time = time.time()
        duration = end_time - start_time
        content = get_text(response)
        
        # Count lines of code (rough estimate)
        code_lines = len([line for line in content.split('\n') if line.strip() and not line.strip().startswith('#')])
        
        result = {
            "description": description,
            "expected_complexity": expected_complexity,
            "prompt_length": len(prompt),
            "duration_seconds": duration,
            "success": True,
            "response_length": len(content),
            "estimated_code_lines": code_lines,
            "response_preview": content[:300] + "..." if len(content) > 300 else content,
            "timestamp": datetime.now().isoformat()
        }
        
        print(f"✅ Success in {duration:.2f}s - Generated: {len(content)} chars, ~{code_lines} lines")
        return result
        
    except Exception as e:
        end_time = time.time()
        duration = end_time - start_time
        
        result = {
            "description": description,
            "expected_complexity": expected_complexity,
            "prompt_length": len(prompt),
            "duration_seconds": duration,
            "success": False,
            "error": str(e),
            "timestamp": datetime.now().isoformat()
        }
        
        print(f"❌ Failed in {duration:.2f}s - Error: {e}")
        return result

def get_realistic_component_prompts() -> List[tuple]:
    """Get realistic component generation prompts used by AutoCoder"""
    
    return [
        # Simple Store Component
        ("""You are a Python expert generating high-quality, production-ready code.

Generate a Store component that inherits from SmartTransformer with the following requirements:

**Component Details:**
- Name: TodoStore
- Type: Store
- Base Class: SmartTransformer
- Method: transform

**Implementation Requirements:**
1. Inherit from SmartTransformer (from autocoder_cc.components.smart_bases import SmartTransformer)
2. Implement the transform(self, data: Dict[str, Any]) method
3. Store todos in a dictionary with CRUD operations
4. Include proper error handling and logging
5. Add input validation for all operations

**Required Methods:**
- transform(): Main entry point that routes operations
- create_todo(todo_data): Create new todo
- get_todo(todo_id): Retrieve todo by ID
- update_todo(todo_id, updates): Update existing todo
- delete_todo(todo_id): Delete todo
- list_todos(): Get all todos

Generate ONLY the Python code with proper imports.""", 
         "Simple Store Component", "Low"),

        # API Endpoint Component
        ("""You are a Python expert generating high-quality, production-ready code.

Generate an APIEndpoint component that inherits from SmartSource with the following requirements:

**Component Details:**
- Name: TodoAPIEndpoint  
- Type: APIEndpoint
- Base Class: SmartSource
- Method: generate

**Implementation Requirements:**
1. Inherit from SmartSource (from autocoder_cc.components.smart_bases import SmartSource)
2. Implement the generate(self) method
3. Create FastAPI endpoints for TODO CRUD operations
4. Include proper request/response models with Pydantic
5. Add comprehensive error handling and status codes
6. Include OpenAPI documentation

**Required Endpoints:**
- POST /todos - Create todo
- GET /todos/{id} - Get todo by ID
- PUT /todos/{id} - Update todo
- DELETE /todos/{id} - Delete todo
- GET /todos - List all todos

Generate ONLY the Python code with proper imports.""",
         "API Endpoint Component", "Medium"),

        # Complex Controller Component
        ("""You are a Python expert generating high-quality, production-ready code.

Generate a Controller component that inherits from SmartSplitter with the following requirements:

**Component Details:**
- Name: OrderProcessingController
- Type: Controller  
- Base Class: SmartSplitter
- Method: split

**Implementation Requirements:**
1. Inherit from SmartSplitter (from autocoder_cc.components.smart_bases import SmartSplitter)
2. Implement the split(self, data: Dict[str, Any]) method
3. Process e-commerce orders with complex business logic
4. Route to different processors based on order type and value
5. Include fraud detection, inventory validation, and payment processing
6. Add comprehensive logging and metrics
7. Implement retry logic and error recovery

**Business Logic:**
- High-value orders (>$1000): Route to manual review
- International orders: Route to customs processor  
- Gift orders: Route to gift wrapper
- Subscription orders: Route to subscription manager
- Standard orders: Route to fulfillment
- Failed orders: Route to error handler

Generate ONLY the Python code with proper imports.""",
         "Complex Controller Component", "High"),

        # Data Transformer Component
        ("""You are a Python expert generating high-quality, production-ready code.

Generate a Transformer component that inherits from SmartTransformer with the following requirements:

**Component Details:**
- Name: UserDataTransformer
- Type: Transformer
- Base Class: SmartTransformer  
- Method: transform

**Implementation Requirements:**
1. Inherit from SmartTransformer (from autocoder_cc.components.smart_bases import SmartTransformer)
2. Implement the transform(self, data: Dict[str, Any]) method
3. Transform user data between different formats (JSON, XML, CSV)
4. Include data validation and sanitization
5. Add schema transformation capabilities
6. Implement field mapping and data enrichment
7. Include comprehensive error handling

**Transformation Features:**
- Format conversion (JSON ↔ XML ↔ CSV)
- Field renaming and restructuring
- Data type conversion and validation
- PII data masking and encryption
- Data enrichment from external sources
- Schema validation and transformation

Generate ONLY the Python code with proper imports.""",
         "Data Transformer Component", "Medium"),

        # Message Queue Consumer
        ("""You are a Python expert generating high-quality, production-ready code.

Generate a message consumer component that inherits from SmartSink with the following requirements:

**Component Details:**
- Name: NotificationConsumer
- Type: Consumer
- Base Class: SmartSink
- Method: consume

**Implementation Requirements:**
1. Inherit from SmartSink (from autocoder_cc.components.smart_bases import SmartSink)
2. Implement the consume(self, data: Dict[str, Any]) method
3. Process notification messages from RabbitMQ
4. Support multiple notification types (email, SMS, push, webhook)
5. Include retry logic with exponential backoff
6. Add dead letter queue handling
7. Implement rate limiting and batch processing

**Features:**
- Multi-channel notification delivery
- Template-based message formatting
- Delivery confirmation tracking
- Failure handling and retry logic
- Performance monitoring and metrics
- Configuration-driven notification rules

Generate ONLY the Python code with proper imports.""",
         "Message Consumer Component", "Medium"),

        # Simple Filter Component  
        ("""You are a Python expert generating high-quality, production-ready code.

Generate a Filter component that inherits from SmartTransformer with the following requirements:

**Component Details:**
- Name: AgeFilter
- Type: Filter
- Base Class: SmartTransformer
- Method: transform

**Implementation Requirements:**
1. Inherit from SmartTransformer (from autocoder_cc.components.smart_bases import SmartTransformer)
2. Implement the transform(self, data: Dict[str, Any]) method
3. Filter users based on age criteria
4. Support configurable age ranges
5. Include input validation

**Filter Logic:**
- Accept users within specified age range
- Reject users outside age range
- Handle missing or invalid age data
- Log filtering decisions

Generate ONLY the Python code with proper imports.""",
         "Simple Filter Component", "Low"),

        # Event Aggregator
        ("""You are a Python expert generating high-quality, production-ready code.

Generate an Aggregator component that inherits from SmartMerger with the following requirements:

**Component Details:**
- Name: EventAggregator
- Type: Aggregator
- Base Class: SmartMerger
- Method: merge

**Implementation Requirements:**
1. Inherit from SmartMerger (from autocoder_cc.components.smart_bases import SmartMerger)
2. Implement the merge(self, data_list: List[Dict[str, Any]]) method
3. Aggregate events from multiple sources
4. Calculate metrics and statistics
5. Generate summary reports
6. Include time-window aggregation
7. Add configurable aggregation rules

**Aggregation Features:**
- Event counting and grouping
- Statistical calculations (avg, min, max, sum)
- Time-based windowing
- Custom aggregation functions
- Real-time and batch processing
- Report generation

Generate ONLY the Python code with proper imports.""",
         "Event Aggregator Component", "High")
    ]

def run_component_timing_tests() -> List[Dict[str, Any]]:
    """Run component generation timing tests"""
    
    prompts = get_realistic_component_prompts()
    
    print("=" * 80)
    print("🔧 COMPONENT GENERATION TIMING TESTS - GPT-5-MINI")  
    print("=" * 80)
    print(f"Model: {MODEL}")
    print(f"Test cases: {len(prompts)}")
    print()
    
    results = []
    
    for i, (prompt, description, complexity) in enumerate(prompts, 1):
        print(f"\n[{i}/{len(prompts)}] ", end="")
        result = time_component_generation(prompt, description, complexity)
        results.append(result)
        
        # Longer delay between complex requests
        time.sleep(2)
    
    return results

def analyze_component_results(results: List[Dict[str, Any]]) -> Dict[str, Any]:
    """Analyze component generation timing results"""
    
    successful_results = [r for r in results if r["success"]]
    failed_results = [r for r in results if not r["success"]]
    
    if not successful_results:
        return {
            "total_tests": len(results),
            "successful_tests": 0,
            "failed_tests": len(failed_results),
            "success_rate": 0.0,
            "error": "No successful tests to analyze"
        }
    
    # Group by complexity
    by_complexity = {}
    for result in successful_results:
        complexity = result["expected_complexity"]
        if complexity not in by_complexity:
            by_complexity[complexity] = []
        by_complexity[complexity].append(result)
    
    durations = [r["duration_seconds"] for r in successful_results]
    code_lines = [r["estimated_code_lines"] for r in successful_results]
    
    analysis = {
        "total_tests": len(results),
        "successful_tests": len(successful_results),
        "failed_tests": len(failed_results),
        "success_rate": len(successful_results) / len(results),
        
        "overall_timing": {
            "min_duration": min(durations),
            "max_duration": max(durations),
            "average_duration": statistics.mean(durations),
            "median_duration": statistics.median(durations),
        },
        
        "code_generation": {
            "min_lines": min(code_lines),
            "max_lines": max(code_lines),
            "average_lines": statistics.mean(code_lines),
        },
        
        "by_complexity": {},
        
        "test_timestamp": datetime.now().isoformat(),
        "model": MODEL
    }
    
    # Analyze by complexity
    for complexity, complexity_results in by_complexity.items():
        complexity_durations = [r["duration_seconds"] for r in complexity_results]
        complexity_lines = [r["estimated_code_lines"] for r in complexity_results]
        
        analysis["by_complexity"][complexity] = {
            "count": len(complexity_results),
            "avg_duration": statistics.mean(complexity_durations),
            "max_duration": max(complexity_durations),
            "avg_lines": statistics.mean(complexity_lines),
        }
    
    return analysis

def print_component_analysis(analysis: Dict[str, Any]):
    """Print component timing analysis results"""
    
    print("\n" + "=" * 80)
    print("📊 COMPONENT GENERATION ANALYSIS")
    print("=" * 80)
    
    print(f"Total Tests: {analysis['total_tests']}")
    print(f"Successful: {analysis['successful_tests']}")
    print(f"Failed: {analysis['failed_tests']}")
    print(f"Success Rate: {analysis['success_rate']:.1%}")
    
    if "overall_timing" in analysis:
        timing = analysis["overall_timing"]
        print(f"\n⏱️  OVERALL TIMING:")
        print(f"  Min:     {timing['min_duration']:.2f}s")
        print(f"  Max:     {timing['max_duration']:.2f}s")
        print(f"  Average: {timing['average_duration']:.2f}s")
        print(f"  Median:  {timing['median_duration']:.2f}s")
        
        code = analysis["code_generation"]
        print(f"\n💻 CODE GENERATION:")
        print(f"  Min lines:     {code['min_lines']}")
        print(f"  Max lines:     {code['max_lines']}")
        print(f"  Average lines: {code['average_lines']:.0f}")
        
        # Timing by complexity
        if "by_complexity" in analysis:
            print(f"\n📈 BY COMPLEXITY:")
            for complexity in ["Low", "Medium", "High"]:
                if complexity in analysis["by_complexity"]:
                    data = analysis["by_complexity"][complexity]
                    print(f"  {complexity:6}: {data['avg_duration']:5.1f}s avg, {data['max_duration']:5.1f}s max, ~{data['avg_lines']:3.0f} lines")
    
    print(f"\n🎯 COMPONENT TIMEOUT RECOMMENDATIONS:")
    if "overall_timing" in analysis:
        avg = analysis["overall_timing"]["average_duration"]
        max_dur = analysis["overall_timing"]["max_duration"]
        
        conservative = max(60, max_dur * 1.5)
        balanced = max(45, avg * 2)
        aggressive = max(30, avg * 1.5)
        
        print(f"  Conservative: {conservative:.0f}s (1.5x max observed)")
        print(f"  Balanced:     {balanced:.0f}s (2x average)")  
        print(f"  Aggressive:   {aggressive:.0f}s (1.5x average)")
        print(f"  Current:      60s")
        
        if max_dur > 60:
            print(f"  ⚠️  WARNING: Max duration ({max_dur:.1f}s) > current timeout (60s)")
        if avg > 30:
            print(f"  ⚠️  WARNING: Average duration ({avg:.1f}s) > 30s")

def save_component_results(results: List[Dict[str, Any]], analysis: Dict[str, Any], filename: str):
    """Save component results to JSON file"""
    
    output = {
        "test_metadata": {
            "test_type": "component_generation_timing",
            "model": MODEL,
            "timestamp": datetime.now().isoformat(),
            "total_tests": len(results)
        },
        "analysis": analysis,
        "raw_results": results
    }
    
    filepath = f"/home/brian/projects/autocoder4_cc/gpt_5_mini_examples/litellm/timing_tests/results/{filename}"
    
    with open(filepath, 'w') as f:
        json.dump(output, f, indent=2)
    
    print(f"\n💾 Results saved to: {filepath}")

def main():
    """Run component generation timing tests"""
    
    print("Starting component generation timing tests...")
    
    # Run tests
    results = run_component_timing_tests()
    
    # Analyze results
    analysis = analyze_component_results(results)
    
    # Print analysis
    print_component_analysis(analysis)
    
    # Save results
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    filename = f"component_timing_results_{timestamp}.json"
    save_component_results(results, analysis, filename)
    
    print("\n✅ Component generation timing tests completed!")
    
    return results, analysis

if __name__ == "__main__":
    main()