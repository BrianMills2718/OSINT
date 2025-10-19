#!/usr/bin/env python3
"""
Run All Timing Tests - Execute all timing tests and generate comprehensive report
"""

import os
import json
import time
from datetime import datetime
from typing import Dict, Any, List

# Import our test modules
import basic_timing_test
import component_generation_timing
import timeout_behavior_test

def run_comprehensive_timing_analysis():
    """Run all timing tests and generate comprehensive analysis"""
    
    print("🚀 COMPREHENSIVE GPT-5-MINI TIMING ANALYSIS")
    print("=" * 80)
    print(f"Starting comprehensive timing tests at {datetime.now()}")
    print()
    
    all_results = {}
    
    # 1. Basic Timing Tests
    print("1️⃣  Running Basic Timing Tests...")
    try:
        basic_results, basic_analysis = basic_timing_test.main()
        all_results["basic"] = {
            "results": basic_results,
            "analysis": basic_analysis,
            "status": "completed"
        }
        print("✅ Basic timing tests completed")
    except Exception as e:
        print(f"❌ Basic timing tests failed: {e}")
        all_results["basic"] = {"status": "failed", "error": str(e)}
    
    print("\n" + "-" * 40)
    time.sleep(5)  # Brief pause between test suites
    
    # 2. Component Generation Tests
    print("\n2️⃣  Running Component Generation Tests...")
    try:
        component_results, component_analysis = component_generation_timing.main()
        all_results["component"] = {
            "results": component_results,
            "analysis": component_analysis,
            "status": "completed"
        }
        print("✅ Component generation tests completed")
    except Exception as e:
        print(f"❌ Component generation tests failed: {e}")
        all_results["component"] = {"status": "failed", "error": str(e)}
    
    print("\n" + "-" * 40)
    time.sleep(5)  # Brief pause between test suites
    
    # 3. Timeout Behavior Tests
    print("\n3️⃣  Running Timeout Behavior Tests...")
    try:
        timeout_results, timeout_analysis = timeout_behavior_test.main()
        all_results["timeout"] = {
            "results": timeout_results,
            "analysis": timeout_analysis,
            "status": "completed"
        }
        print("✅ Timeout behavior tests completed")
    except Exception as e:
        print(f"❌ Timeout behavior tests failed: {e}")
        all_results["timeout"] = {"status": "failed", "error": str(e)}
    
    return all_results

def generate_comprehensive_analysis(all_results: Dict[str, Any]) -> Dict[str, Any]:
    """Generate comprehensive analysis across all test types"""
    
    comprehensive = {
        "test_metadata": {
            "timestamp": datetime.now().isoformat(),
            "model": "gpt-5-mini-2025-08-07",
            "test_suites": list(all_results.keys()),
            "completed_suites": [k for k, v in all_results.items() if v.get("status") == "completed"]
        },
        "summary": {},
        "recommendations": {},
        "raw_data": all_results
    }
    
    completed_tests = [k for k, v in all_results.items() if v.get("status") == "completed"]
    
    if not completed_tests:
        comprehensive["summary"]["error"] = "No tests completed successfully"
        return comprehensive
    
    # Collect all successful timings
    all_timings = []
    all_successful_tests = 0
    all_total_tests = 0
    
    for test_type in completed_tests:
        test_data = all_results[test_type]
        if "analysis" in test_data:
            analysis = test_data["analysis"]
            
            all_total_tests += analysis.get("total_tests", 0)
            all_successful_tests += analysis.get("successful_tests", 0)
            
            # Extract timing data
            if "timing_analysis" in analysis:
                timing = analysis["timing_analysis"]
                all_timings.extend([timing.get("min_duration", 0), timing.get("max_duration", 0)])
            elif "overall_timing" in analysis:
                timing = analysis["overall_timing"] 
                all_timings.extend([timing.get("min_duration", 0), timing.get("max_duration", 0)])
            elif "successful_timing" in analysis:
                timing = analysis["successful_timing"]
                all_timings.extend([timing.get("min_duration", 0), timing.get("max_duration", 0)])
    
    # Generate summary
    if all_timings:
        all_timings = [t for t in all_timings if t > 0]  # Remove zeros
        
        comprehensive["summary"] = {
            "total_tests_across_all_suites": all_total_tests,
            "successful_tests_across_all_suites": all_successful_tests,
            "overall_success_rate": all_successful_tests / all_total_tests if all_total_tests > 0 else 0,
            "timing_range": {
                "fastest_response": min(all_timings),
                "slowest_response": max(all_timings),
                "response_time_spread": max(all_timings) - min(all_timings)
            }
        }
    
    # Generate timeout recommendations
    recommendations = []
    
    # From basic tests
    if "basic" in completed_tests and "analysis" in all_results["basic"]:
        basic = all_results["basic"]["analysis"]
        if "timing_analysis" in basic:
            avg_basic = basic["timing_analysis"].get("average_duration", 0)
            max_basic = basic["timing_analysis"].get("max_duration", 0)
            recommendations.append(f"Basic tasks: avg {avg_basic:.1f}s, max {max_basic:.1f}s")
    
    # From component tests
    if "component" in completed_tests and "analysis" in all_results["component"]:
        component = all_results["component"]["analysis"]
        if "overall_timing" in component:
            avg_comp = component["overall_timing"].get("average_duration", 0)
            max_comp = component["overall_timing"].get("max_duration", 0)
            recommendations.append(f"Component generation: avg {avg_comp:.1f}s, max {max_comp:.1f}s")
    
    # From timeout tests
    if "timeout" in completed_tests and "analysis" in all_results["timeout"]:
        timeout = all_results["timeout"]["analysis"]
        timeout_rate = timeout.get("timeout_rate", 0)
        recommendations.append(f"Timeout rate at various limits: {timeout_rate:.1%}")
    
    # Generate final timeout recommendation
    if all_timings:
        max_observed = max(all_timings)
        avg_observed = sum(all_timings) / len(all_timings)
        
        # Conservative: 2x max observed, minimum 60s
        conservative_timeout = max(60, max_observed * 2)
        
        # Balanced: 1.5x max observed, minimum 45s  
        balanced_timeout = max(45, max_observed * 1.5)
        
        # Aggressive: 1.2x max observed, minimum 30s
        aggressive_timeout = max(30, max_observed * 1.2)
        
        comprehensive["recommendations"] = {
            "current_timeout": 60,
            "observed_performance": {
                "max_response_time": max_observed,
                "avg_response_time": avg_observed,
                "response_time_spread": max_observed - min(all_timings)
            },
            "timeout_options": {
                "conservative": {
                    "timeout_seconds": int(conservative_timeout),
                    "rationale": f"2x max observed ({max_observed:.1f}s), handles edge cases"
                },
                "balanced": {
                    "timeout_seconds": int(balanced_timeout),
                    "rationale": f"1.5x max observed ({max_observed:.1f}s), good reliability"
                },
                "aggressive": {
                    "timeout_seconds": int(aggressive_timeout),
                    "rationale": f"1.2x max observed ({max_observed:.1f}s), fail fast"
                }
            },
            "recommendation": "balanced",
            "details": recommendations
        }
    
    return comprehensive

def print_comprehensive_report(comprehensive: Dict[str, Any]):
    """Print comprehensive analysis report"""
    
    print("\n" + "=" * 80)
    print("📋 COMPREHENSIVE TIMING ANALYSIS REPORT")
    print("=" * 80)
    
    metadata = comprehensive["test_metadata"]
    print(f"Model: {metadata['model']}")
    print(f"Timestamp: {metadata['timestamp']}")
    print(f"Test Suites: {', '.join(metadata['test_suites'])}")
    print(f"Completed: {', '.join(metadata['completed_suites'])}")
    
    if "summary" in comprehensive and "total_tests_across_all_suites" in comprehensive["summary"]:
        summary = comprehensive["summary"]
        print(f"\n📊 OVERALL SUMMARY:")
        print(f"  Total Tests: {summary['total_tests_across_all_suites']}")
        print(f"  Successful: {summary['successful_tests_across_all_suites']}")
        print(f"  Success Rate: {summary['overall_success_rate']:.1%}")
        
        if "timing_range" in summary:
            timing = summary["timing_range"]
            print(f"  Response Time Range: {timing['fastest_response']:.2f}s - {timing['slowest_response']:.2f}s")
            print(f"  Time Spread: {timing['response_time_spread']:.2f}s")
    
    if "recommendations" in comprehensive:
        rec = comprehensive["recommendations"]
        print(f"\n🎯 TIMEOUT RECOMMENDATIONS:")
        print(f"  Current Setting: {rec['current_timeout']}s")
        
        if "observed_performance" in rec:
            obs = rec["observed_performance"]
            print(f"  Max Observed: {obs['max_response_time']:.2f}s")
            print(f"  Avg Observed: {obs['avg_response_time']:.2f}s")
        
        if "timeout_options" in rec:
            options = rec["timeout_options"]
            print(f"\n  Options:")
            for option_name, option_data in options.items():
                marker = "👉" if option_name == rec.get("recommendation") else "  "
                print(f"  {marker} {option_name.title()}: {option_data['timeout_seconds']}s - {option_data['rationale']}")
        
        if "details" in rec:
            print(f"\n  Details:")
            for detail in rec["details"]:
                print(f"    • {detail}")
    
    # Status check
    failed_tests = [k for k, v in comprehensive["raw_data"].items() if v.get("status") == "failed"]
    if failed_tests:
        print(f"\n⚠️  FAILED TEST SUITES: {', '.join(failed_tests)}")
        for test in failed_tests:
            error = comprehensive["raw_data"][test].get("error", "Unknown error")
            print(f"    {test}: {error}")

def save_comprehensive_results(comprehensive: Dict[str, Any], filename: str):
    """Save comprehensive results to JSON file"""
    
    filepath = f"/home/brian/projects/autocoder4_cc/gpt_5_mini_examples/litellm/timing_tests/results/{filename}"
    
    with open(filepath, 'w') as f:
        json.dump(comprehensive, f, indent=2)
    
    print(f"\n💾 Comprehensive results saved to: {filepath}")

def main():
    """Run comprehensive timing analysis"""
    
    print("Starting comprehensive timing analysis...")
    
    # Run all tests
    all_results = run_comprehensive_timing_analysis()
    
    # Generate comprehensive analysis
    comprehensive = generate_comprehensive_analysis(all_results)
    
    # Print report
    print_comprehensive_report(comprehensive)
    
    # Save results
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    filename = f"comprehensive_timing_analysis_{timestamp}.json"
    save_comprehensive_results(comprehensive, filename)
    
    print("\n🎉 Comprehensive timing analysis completed!")
    print("\nNext steps:")
    print("1. Review the timeout recommendations above")
    print("2. Update timeout_manager.py with recommended values")  
    print("3. Test with the new timeout settings")
    print("4. Monitor production performance")
    
    return comprehensive

if __name__ == "__main__":
    main()