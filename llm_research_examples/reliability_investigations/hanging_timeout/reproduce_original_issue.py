#!/usr/bin/env python3
"""
Reproduce Original Issue - Try to recreate the hanging behavior
"""
import sys
import time
import subprocess
import asyncio
from pathlib import Path
sys.path.insert(0, '/home/brian/projects/autocoder4_cc')

def test_cli_hanging():
    """Test if CLI hangs with the exact same conditions you experienced"""
    
    print("🔍 REPRODUCING ORIGINAL HANGING ISSUE")
    print("=" * 60)
    
    # Test multiple scenarios to see which one hangs
    test_cases = [
        {
            "name": "Simple System Generation",
            "cmd": ["python3", "autocoder_cc/cli/v2/main.py", "system", "Simple test system", "-o", "/tmp/hang_repro_1"],
            "timeout": 30
        },
        {
            "name": "Todo API System",
            "cmd": ["python3", "autocoder_cc/cli/v2/main.py", "system", "Todo API system", "-o", "/tmp/hang_repro_2"], 
            "timeout": 30
        },
        {
            "name": "Complex Multi-Component",
            "cmd": ["python3", "autocoder_cc/cli/v2/main.py", "system", "Data processing pipeline with source, transformer, and sink", "-o", "/tmp/hang_repro_3"],
            "timeout": 45
        },
        {
            "name": "Single Component Generation",
            "cmd": ["python3", "autocoder_cc/cli/v2/main.py", "generate", "Source", "-o", "/tmp/hang_repro_4"],
            "timeout": 30
        }
    ]
    
    results = []
    
    for test_case in test_cases:
        print(f"\n🧪 Testing: {test_case['name']}")
        print(f"   Command: {' '.join(test_case['cmd'])}")
        print(f"   Timeout: {test_case['timeout']}s")
        
        start_time = time.time()
        
        try:
            result = subprocess.run(
                test_case['cmd'],
                cwd='/home/brian/projects/autocoder4_cc',
                capture_output=True,
                text=True,
                timeout=test_case['timeout']
            )
            
            duration = time.time() - start_time
            
            if result.returncode == 0:
                print(f"   ✅ COMPLETED in {duration:.1f}s")
                # Check if output was actually created
                output_dir = test_case['cmd'][-1]
                if Path(output_dir).exists():
                    files = list(Path(output_dir).rglob("*.py"))
                    print(f"   📁 Generated {len(files)} files")
                else:
                    print(f"   ⚠️ No output directory created")
                
                results.append({
                    "test": test_case['name'],
                    "status": "SUCCESS",
                    "duration": duration,
                    "returncode": result.returncode
                })
            else:
                print(f"   ❌ FAILED in {duration:.1f}s (exit code: {result.returncode})")
                print(f"   Error output: {result.stderr[:200]}...")
                
                results.append({
                    "test": test_case['name'], 
                    "status": "FAILED",
                    "duration": duration,
                    "returncode": result.returncode,
                    "error": result.stderr[:200]
                })
                
        except subprocess.TimeoutExpired:
            duration = time.time() - start_time
            print(f"   ⏰ HUNG/TIMEOUT after {duration:.1f}s")
            
            results.append({
                "test": test_case['name'],
                "status": "HUNG",
                "duration": duration,
                "timeout": test_case['timeout']
            })
            
        except Exception as e:
            duration = time.time() - start_time
            print(f"   💥 ERROR: {e}")
            
            results.append({
                "test": test_case['name'],
                "status": "ERROR", 
                "duration": duration,
                "error": str(e)
            })
    
    # Summary
    print("\n" + "=" * 60)
    print("🎯 REPRODUCTION TEST RESULTS")
    print("=" * 60)
    
    hung_tests = [r for r in results if r["status"] == "HUNG"]
    failed_tests = [r for r in results if r["status"] == "FAILED"]
    success_tests = [r for r in results if r["status"] == "SUCCESS"]
    
    print(f"✅ Successful: {len(success_tests)}")
    print(f"❌ Failed: {len(failed_tests)}")
    print(f"⏰ Hung: {len(hung_tests)}")
    
    if hung_tests:
        print(f"\n🚨 HANGING REPRODUCED:")
        for test in hung_tests:
            print(f"   - {test['test']}: hung after {test['duration']:.1f}s")
        return True
    else:
        print(f"\n🤔 NO HANGING REPRODUCED - all tests completed or failed quickly")
        return False

if __name__ == "__main__":
    hanging_reproduced = test_cli_hanging()
    
    if hanging_reproduced:
        print("\n🎯 NEXT STEP: Investigate the hanging tests with detailed monitoring")
    else:
        print("\n🎯 NEXT STEP: Compare with your original conditions to understand the difference")
        
    exit(0 if hanging_reproduced else 1)