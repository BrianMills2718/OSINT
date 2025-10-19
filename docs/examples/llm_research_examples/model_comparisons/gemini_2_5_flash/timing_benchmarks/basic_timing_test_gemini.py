#!/usr/bin/env python3
"""
Basic Timing Test - Gemini 2.5 Flash-Lite with LiteLLM
Tests basic Gemini 2.5 Flash-Lite response times for simple tasks
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
load_dotenv("/home/brian/projects/autocoder4_cc/.env")

# Hardcode API key for now as requested
os.environ['GEMINI_API_KEY'] = 'AIzaSyCwNW6kO6R0AewqsUgG9IgrDg6vCRFhhHw'

MODEL = "gemini/gemini-2.5-flash-lite"

def time_single_request(prompt: str, description: str) -> Dict[str, Any]:
    """Time a single request and return results"""
    print(f"Testing: {description}")
    print(f"Prompt: {prompt[:100]}...")
    
    start_time = time.time()
    
    try:
        response = litellm.completion(
            model=MODEL,
            messages=[{"role": "user", "content": prompt}]
        )
        
        end_time = time.time()
        duration = end_time - start_time
        content = response.choices[0].message.content
        
        result = {
            "description": description,
            "prompt": prompt,
            "duration_seconds": duration,
            "success": True,
            "response_length": len(content),
            "response_preview": content[:200] + "..." if len(content) > 200 else content,
            "timestamp": datetime.now().isoformat()
        }
        
        print(f"✅ Success in {duration:.2f}s - Response: {len(content)} chars")
        return result
        
    except Exception as e:
        end_time = time.time()
        duration = end_time - start_time
        
        result = {
            "description": description,
            "prompt": prompt,
            "duration_seconds": duration,
            "success": False,
            "error": str(e),
            "timestamp": datetime.now().isoformat()
        }
        
        print(f"❌ Failed in {duration:.2f}s - Error: {e}")
        return result

def run_basic_timing_tests() -> List[Dict[str, Any]]:
    """Run basic timing tests"""
    
    test_cases = [
        ("What is 2+2?", "Simple math"),
        ("Write a hello world function in Python.", "Basic code generation"),
        ("Explain what a variable is in programming in one sentence.", "Simple explanation"),
        ("List 3 colors.", "Simple list"),
        ("Write a function that adds two numbers.", "Basic function"),
        ("What is the capital of France?", "Factual question"),
        ("Count from 1 to 5.", "Simple counting"),
        ("Write 'Hello World' in a code comment.", "Minimal code"),
        ("True or false: Python is a programming language.", "Yes/no question"),
        ("Write one line of Python that prints 'test'.", "One-liner code")
    ]
    
    print("=" * 80)
    print("🚀 BASIC TIMING TESTS - GEMINI 2.5 FLASH-LITE")
    print("=" * 80)
    print(f"Model: {MODEL}")
    print(f"Test cases: {len(test_cases)}")
    print()
    
    results = []
    
    for i, (prompt, description) in enumerate(test_cases, 1):
        print(f"\n[{i}/{len(test_cases)}] ", end="")
        result = time_single_request(prompt, description)
        results.append(result)
        
        # Small delay between requests
        time.sleep(1)
    
    return results

def analyze_results(results: List[Dict[str, Any]]) -> Dict[str, Any]:
    """Analyze timing results"""
    
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
    
    durations = [r["duration_seconds"] for r in successful_results]
    response_lengths = [r["response_length"] for r in successful_results]
    
    analysis = {
        "total_tests": len(results),
        "successful_tests": len(successful_results),
        "failed_tests": len(failed_results),
        "success_rate": len(successful_results) / len(results),
        
        "timing_analysis": {
            "min_duration": min(durations),
            "max_duration": max(durations),
            "average_duration": statistics.mean(durations),
            "median_duration": statistics.median(durations),
        },
        
        "response_analysis": {
            "min_length": min(response_lengths),
            "max_length": max(response_lengths),
            "average_length": statistics.mean(response_lengths),
        },
        
        "test_timestamp": datetime.now().isoformat(),
        "model": MODEL
    }
    
    # Add 95th percentile if we have enough data
    if len(durations) >= 20:
        durations_sorted = sorted(durations)
        percentile_95_index = int(0.95 * len(durations_sorted))
        analysis["timing_analysis"]["p95_duration"] = durations_sorted[percentile_95_index]
    
    return analysis

def print_analysis(analysis: Dict[str, Any]):
    """Print timing analysis results"""
    
    print("\n" + "=" * 80)
    print("📊 BASIC TIMING ANALYSIS - GEMINI 2.5 FLASH-LITE")
    print("=" * 80)
    
    print(f"Total Tests: {analysis['total_tests']}")
    print(f"Successful: {analysis['successful_tests']}")
    print(f"Failed: {analysis['failed_tests']}")
    print(f"Success Rate: {analysis['success_rate']:.1%}")
    
    if "timing_analysis" in analysis:
        timing = analysis["timing_analysis"]
        print(f"\n⏱️  TIMING RESULTS:")
        print(f"  Min:     {timing['min_duration']:.2f}s")
        print(f"  Max:     {timing['max_duration']:.2f}s")
        print(f"  Average: {timing['average_duration']:.2f}s")
        print(f"  Median:  {timing['median_duration']:.2f}s")
        
        if "p95_duration" in timing:
            print(f"  95th %:  {timing['p95_duration']:.2f}s")
        
        response = analysis["response_analysis"]
        print(f"\n📝 RESPONSE LENGTHS:")
        print(f"  Min:     {response['min_length']} chars")
        print(f"  Max:     {response['max_length']} chars")
        print(f"  Average: {response['average_length']:.0f} chars")
    
    print(f"\n🎯 TIMEOUT RECOMMENDATIONS:")
    if "timing_analysis" in analysis:
        avg = analysis["timing_analysis"]["average_duration"]
        max_dur = analysis["timing_analysis"]["max_duration"]
        
        conservative = max(30, max_dur * 2)
        aggressive = max(15, avg * 3)
        
        print(f"  Conservative: {conservative:.0f}s (2x max observed)")
        print(f"  Aggressive:   {aggressive:.0f}s (3x average)")
        print(f"  Current:      60s")
        
        if max_dur > 30:
            print(f"  ⚠️  WARNING: Max duration ({max_dur:.1f}s) > 30s")
        if avg > 10:
            print(f"  ⚠️  WARNING: Average duration ({avg:.1f}s) > 10s")

def save_results(results: List[Dict[str, Any]], analysis: Dict[str, Any], filename: str):
    """Save results to JSON file"""
    
    output = {
        "test_metadata": {
            "test_type": "basic_timing_gemini",
            "model": MODEL,
            "timestamp": datetime.now().isoformat(),
            "total_tests": len(results)
        },
        "analysis": analysis,
        "raw_results": results
    }
    
    filepath = f"/home/brian/projects/autocoder4_cc/gpt_5_mini_examples/litellm/gemini_timing_tests/results/{filename}"
    
    with open(filepath, 'w') as f:
        json.dump(output, f, indent=2)
    
    print(f"\n💾 Results saved to: {filepath}")

def main():
    """Run basic timing tests"""
    
    print("Starting Gemini 2.5 Flash-Lite basic timing tests...")
    
    # Run tests
    results = run_basic_timing_tests()
    
    # Analyze results
    analysis = analyze_results(results)
    
    # Print analysis
    print_analysis(analysis)
    
    # Save results
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    filename = f"basic_timing_results_gemini_{timestamp}.json"
    save_results(results, analysis, filename)
    
    print("\n✅ Gemini 2.5 Flash-Lite basic timing tests completed!")
    
    return results, analysis

if __name__ == "__main__":
    main()