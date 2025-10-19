#!/usr/bin/env python3
"""
Run All Timing Tests - Gemini 2.5 Flash-Lite
Runs all timing tests and generates comprehensive comparison analysis
"""

import os
import json
import statistics
from datetime import datetime
from typing import Dict, Any, List

# Import the test modules
from basic_timing_test_gemini import main as run_basic_tests
from component_generation_timing_gemini import main as run_component_tests

def compare_with_gpt5_results() -> Dict[str, Any]:
    """Compare Gemini results with existing GPT-5-mini results"""
    
    print("=" * 80)
    print("📊 GEMINI VS GPT-5-MINI COMPARISON")
    print("=" * 80)
    
    # Look for latest GPT-5-mini results
    gpt5_results_dir = "/home/brian/projects/autocoder4_cc/gpt_5_mini_examples/litellm/timing_tests/results"
    gemini_results_dir = "/home/brian/projects/autocoder4_cc/gpt_5_mini_examples/litellm/gemini_timing_tests/results"
    
    try:
        # Get latest GPT-5-mini files
        gpt5_files = [f for f in os.listdir(gpt5_results_dir) if f.endswith('.json')]
        gpt5_basic = [f for f in gpt5_files if 'basic_timing' in f]
        gpt5_component = [f for f in gpt5_files if 'component_timing' in f]
        
        # Get latest Gemini files
        gemini_files = [f for f in os.listdir(gemini_results_dir) if f.endswith('.json')]
        gemini_basic = [f for f in gemini_files if 'basic_timing' in f]
        gemini_component = [f for f in gemini_files if 'component_timing' in f]
        
        comparison = {
            "timestamp": datetime.now().isoformat(),
            "gpt5_files_found": len(gpt5_files),
            "gemini_files_found": len(gemini_files),
            "basic_comparison": None,
            "component_comparison": None
        }
        
        # Compare basic timing
        if gpt5_basic and gemini_basic:
            gpt5_basic_file = sorted(gpt5_basic)[-1]  # Latest
            gemini_basic_file = sorted(gemini_basic)[-1]  # Latest
            
            with open(f"{gpt5_results_dir}/{gpt5_basic_file}") as f:
                gpt5_data = json.load(f)
            with open(f"{gemini_results_dir}/{gemini_basic_file}") as f:
                gemini_data = json.load(f)
            
            if "analysis" in gpt5_data and "analysis" in gemini_data:
                gpt5_timing = gpt5_data["analysis"].get("timing_analysis", {})
                gemini_timing = gemini_data["analysis"].get("timing_analysis", {})
                
                comparison["basic_comparison"] = {
                    "gpt5_avg": gpt5_timing.get("average_duration", 0),
                    "gemini_avg": gemini_timing.get("average_duration", 0),
                    "gpt5_max": gpt5_timing.get("max_duration", 0),
                    "gemini_max": gemini_timing.get("max_duration", 0),
                    "gemini_speedup": (gpt5_timing.get("average_duration", 1) / 
                                     gemini_timing.get("average_duration", 1)) if gemini_timing.get("average_duration", 0) > 0 else 0
                }
        
        # Compare component timing
        if gpt5_component and gemini_component:
            gpt5_component_file = sorted(gpt5_component)[-1]  # Latest
            gemini_component_file = sorted(gemini_component)[-1]  # Latest
            
            with open(f"{gpt5_results_dir}/{gpt5_component_file}") as f:
                gpt5_data = json.load(f)
            with open(f"{gemini_results_dir}/{gemini_component_file}") as f:
                gemini_data = json.load(f)
            
            if "analysis" in gpt5_data and "analysis" in gemini_data:
                gpt5_timing = gpt5_data["analysis"].get("overall_timing", {})
                gemini_timing = gemini_data["analysis"].get("overall_timing", {})
                
                comparison["component_comparison"] = {
                    "gpt5_avg": gpt5_timing.get("average_duration", 0),
                    "gemini_avg": gemini_timing.get("average_duration", 0),
                    "gpt5_max": gpt5_timing.get("max_duration", 0),
                    "gemini_max": gemini_timing.get("max_duration", 0),
                    "gemini_speedup": (gpt5_timing.get("average_duration", 1) / 
                                     gemini_timing.get("average_duration", 1)) if gemini_timing.get("average_duration", 0) > 0 else 0
                }
        
        return comparison
        
    except Exception as e:
        print(f"⚠️  Could not load comparison data: {e}")
        return {"error": str(e), "timestamp": datetime.now().isoformat()}

def print_comparison(comparison: Dict[str, Any]):
    """Print timing comparison results"""
    
    if "error" in comparison:
        print(f"❌ Comparison failed: {comparison['error']}")
        return
    
    print(f"GPT-5-mini files found: {comparison['gpt5_files_found']}")
    print(f"Gemini files found: {comparison['gemini_files_found']}")
    
    # Basic timing comparison
    if comparison["basic_comparison"]:
        basic = comparison["basic_comparison"]
        print(f"\n📈 BASIC TIMING COMPARISON:")
        print(f"  GPT-5-mini average:  {basic['gpt5_avg']:.2f}s")
        print(f"  Gemini average:      {basic['gemini_avg']:.2f}s")
        print(f"  Speedup:             {basic['gemini_speedup']:.1f}x")
        print(f"  GPT-5-mini max:      {basic['gpt5_max']:.2f}s")
        print(f"  Gemini max:          {basic['gemini_max']:.2f}s")
    
    # Component timing comparison
    if comparison["component_comparison"]:
        comp = comparison["component_comparison"]
        print(f"\n🔧 COMPONENT TIMING COMPARISON:")
        print(f"  GPT-5-mini average:  {comp['gpt5_avg']:.2f}s")
        print(f"  Gemini average:      {comp['gemini_avg']:.2f}s")
        print(f"  Speedup:             {comp['gemini_speedup']:.1f}x")
        print(f"  GPT-5-mini max:      {comp['gpt5_max']:.2f}s")
        print(f"  Gemini max:          {comp['gemini_max']:.2f}s")
    
    # Overall recommendation
    if comparison["basic_comparison"] and comparison["component_comparison"]:
        basic_speedup = comparison["basic_comparison"]["gemini_speedup"]
        comp_speedup = comparison["component_comparison"]["gemini_speedup"]
        avg_speedup = (basic_speedup + comp_speedup) / 2
        
        print(f"\n🎯 OVERALL PERFORMANCE:")
        print(f"  Average speedup: {avg_speedup:.1f}x")
        
        if avg_speedup > 1.5:
            print(f"  🚀 Gemini 2.5 Flash-Lite is significantly faster!")
        elif avg_speedup > 1.1:
            print(f"  ✅ Gemini 2.5 Flash-Lite is faster")
        elif avg_speedup > 0.9:
            print(f"  ⚖️  Performance is similar")
        else:
            print(f"  🐌 GPT-5-mini is faster")

def save_comprehensive_results(basic_results, basic_analysis, component_results, component_analysis, comparison):
    """Save comprehensive test results"""
    
    output = {
        "test_metadata": {
            "test_suite": "comprehensive_timing_gemini",
            "model": "gemini/gemini-2.5-flash-lite",
            "timestamp": datetime.now().isoformat(),
            "total_basic_tests": len(basic_results),
            "total_component_tests": len(component_results)
        },
        "basic_timing": {
            "analysis": basic_analysis,
            "results": basic_results
        },
        "component_timing": {
            "analysis": component_analysis,
            "results": component_results
        },
        "comparison_with_gpt5": comparison
    }
    
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    filename = f"comprehensive_timing_analysis_gemini_{timestamp}.json"
    filepath = f"/home/brian/projects/autocoder4_cc/gpt_5_mini_examples/litellm/gemini_timing_tests/results/{filename}"
    
    with open(filepath, 'w') as f:
        json.dump(output, f, indent=2)
    
    print(f"\n💾 Comprehensive results saved to: {filepath}")

def main():
    """Run all timing tests and generate comprehensive analysis"""
    
    print("🚀 STARTING COMPREHENSIVE GEMINI 2.5 FLASH-LITE TIMING TESTS")
    print("=" * 80)
    
    # Run basic timing tests
    print("\n1️⃣  Running basic timing tests...")
    basic_results, basic_analysis = run_basic_tests()
    
    print("\n" + "=" * 80)
    
    # Run component generation tests
    print("\n2️⃣  Running component generation tests...")
    component_results, component_analysis = run_component_tests()
    
    print("\n" + "=" * 80)
    
    # Generate comparison with GPT-5-mini
    print("\n3️⃣  Comparing with GPT-5-mini results...")
    comparison = compare_with_gpt5_results()
    print_comparison(comparison)
    
    # Save comprehensive results
    save_comprehensive_results(
        basic_results, basic_analysis,
        component_results, component_analysis,
        comparison
    )
    
    print("\n" + "=" * 80)
    print("✅ ALL GEMINI 2.5 FLASH-LITE TIMING TESTS COMPLETED!")
    print("=" * 80)
    
    return {
        "basic": (basic_results, basic_analysis),
        "component": (component_results, component_analysis),
        "comparison": comparison
    }

if __name__ == "__main__":
    main()