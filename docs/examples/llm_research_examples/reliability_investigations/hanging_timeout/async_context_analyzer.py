#!/usr/bin/env python3
"""
Async Context Analyzer - Compare async contexts between working and hanging scenarios
"""
import sys
import asyncio
import threading
import traceback
import time
import psutil
import os
from pathlib import Path
sys.path.insert(0, '/home/brian/projects/autocoder4_cc')

class AsyncContextAnalyzer:
    def __init__(self):
        self.context_data = {}
        
    def capture_async_state(self, context_name: str):
        """Capture detailed async context state"""
        try:
            loop = asyncio.get_event_loop()
        except RuntimeError:
            loop = None
            
        state = {
            'timestamp': time.time(),
            'context_name': context_name,
            'thread_name': threading.current_thread().name,
            'thread_id': threading.get_ident(),
            'process_id': os.getpid(),
            'loop_exists': loop is not None,
            'loop_running': loop.is_running() if loop else False,
            'loop_closed': loop.is_closed() if loop else None,
            'loop_debug': loop.get_debug() if loop else None,
            'active_threads': threading.active_count(),
            'thread_names': [t.name for t in threading.enumerate()],
            'call_stack_depth': len(traceback.extract_stack()),
        }
        
        # Get pending tasks if loop exists
        if loop:
            try:
                tasks = asyncio.all_tasks(loop)
                state['task_count'] = len(tasks)
                state['task_states'] = [str(task) for task in tasks]
                state['pending_tasks'] = [str(task) for task in tasks if not task.done()]
            except Exception as e:
                state['task_error'] = str(e)
                
        # Resource usage
        process = psutil.Process()
        state['memory_mb'] = process.memory_info().rss / 1024 / 1024
        state['open_files'] = len(process.open_files())
        state['connections'] = len(process.connections())
        state['cpu_percent'] = process.cpu_percent()
        
        self.context_data[context_name] = state
        return state
        
    def log_state(self, state):
        """Log state in readable format"""
        print(f"\n📊 ASYNC CONTEXT: {state['context_name']}")
        print(f"   Thread: {state['thread_name']} (ID: {state['thread_id']})")
        print(f"   Event Loop: {'✅' if state['loop_exists'] else '❌'} Running: {'✅' if state['loop_running'] else '❌'}")
        print(f"   Tasks: {state.get('task_count', 0)} ({len(state.get('pending_tasks', []))} pending)")
        print(f"   Threads: {state['active_threads']} active")
        print(f"   Memory: {state['memory_mb']:.1f}MB, Files: {state['open_files']}, Connections: {state['connections']}")
        print(f"   Call Stack Depth: {state['call_stack_depth']}")
        
    def compare_contexts(self, context1: str, context2: str):
        """Compare two captured contexts"""
        if context1 not in self.context_data or context2 not in self.context_data:
            print(f"❌ Cannot compare - missing context data")
            return
            
        c1 = self.context_data[context1]
        c2 = self.context_data[context2]
        
        print(f"\n🔍 CONTEXT COMPARISON: {context1} vs {context2}")
        print("=" * 60)
        
        # Key differences
        differences = []
        
        if c1['loop_running'] != c2['loop_running']:
            differences.append(f"Event loop running: {c1['loop_running']} → {c2['loop_running']}")
            
        if c1.get('task_count', 0) != c2.get('task_count', 0):
            differences.append(f"Task count: {c1.get('task_count', 0)} → {c2.get('task_count', 0)}")
            
        if c1['active_threads'] != c2['active_threads']:
            differences.append(f"Active threads: {c1['active_threads']} → {c2['active_threads']}")
            
        if abs(c1['memory_mb'] - c2['memory_mb']) > 10:
            differences.append(f"Memory: {c1['memory_mb']:.1f}MB → {c2['memory_mb']:.1f}MB")
            
        if c1['open_files'] != c2['open_files']:
            differences.append(f"Open files: {c1['open_files']} → {c2['open_files']}")
            
        if c1['connections'] != c2['connections']:
            differences.append(f"Connections: {c1['connections']} → {c2['connections']}")
            
        if differences:
            print("🚨 KEY DIFFERENCES FOUND:")
            for diff in differences:
                print(f"   - {diff}")
        else:
            print("✅ NO SIGNIFICANT DIFFERENCES")
            
        # Show pending tasks differences
        p1 = set(c1.get('pending_tasks', []))
        p2 = set(c2.get('pending_tasks', []))
        
        if p1 != p2:
            print(f"\n📋 PENDING TASKS DIFFERENCES:")
            only_in_1 = p1 - p2
            only_in_2 = p2 - p1
            
            if only_in_1:
                print(f"   Only in {context1}:")
                for task in only_in_1:
                    print(f"     - {task}")
                    
            if only_in_2:
                print(f"   Only in {context2}:")
                for task in only_in_2:
                    print(f"     - {task}")

# Global analyzer instance
analyzer = AsyncContextAnalyzer()

async def test_working_llm_call():
    """Test working LLM call context"""
    print("🧪 TESTING WORKING LLM CALL")
    
    # Capture before
    state_before = analyzer.capture_async_state("working_before")
    analyzer.log_state(state_before)
    
    try:
        from dotenv import load_dotenv
        load_dotenv('/home/brian/projects/autocoder4_cc/.env')
        
        from autocoder_cc.blueprint_language.llm_component_generator import LLMComponentGenerator
        
        generator = LLMComponentGenerator()
        
        # Capture during initialization
        state_init = analyzer.capture_async_state("working_init")
        analyzer.log_state(state_init)
        
        # Test component generation
        start_time = time.time()
        result = await generator.generate_component_implementation_enhanced(
            component_type="Source",
            component_name="test_working_source",
            component_description="Test working source",
            component_config={},
            class_name="TestWorkingSource",
            system_context={"test": "context"},
            blueprint={"test": "blueprint"}
        )
        duration = time.time() - start_time
        
        # Capture after
        state_after = analyzer.capture_async_state("working_after")
        analyzer.log_state(state_after)
        
        print(f"✅ Working LLM call completed in {duration:.1f}s")
        print(f"   Generated {len(result)} characters")
        
        return True
        
    except Exception as e:
        state_error = analyzer.capture_async_state("working_error")
        analyzer.log_state(state_error)
        print(f"❌ Working LLM call failed: {e}")
        return False

async def test_hanging_system_generation():
    """Test hanging system generation context"""
    print("\n🧪 TESTING HANGING SYSTEM GENERATION")
    
    # Capture before
    state_before = analyzer.capture_async_state("hanging_before")
    analyzer.log_state(state_before)
    
    try:
        from dotenv import load_dotenv
        load_dotenv('/home/brian/projects/autocoder4_cc/.env')
        
        from autocoder_cc.blueprint_language.natural_language_to_blueprint import NaturalLanguageToPydanticTranslator
        from autocoder_cc.blueprint_language.healing_integration import SystemGenerator
        from pathlib import Path
        
        translator = NaturalLanguageToPydanticTranslator()
        blueprint_yaml = translator.generate_full_blueprint("Simple test system with source and sink")
        
        generator = SystemGenerator(Path("/tmp/hang_context_test"), skip_deployment=True)
        
        # Capture before system generation
        state_before_gen = analyzer.capture_async_state("hanging_before_generation")
        analyzer.log_state(state_before_gen)
        
        # This should hang - we'll timeout after 20 seconds
        start_time = time.time()
        try:
            result = await asyncio.wait_for(
                generator.generate_system_from_yaml(blueprint_yaml),
                timeout=20
            )
            duration = time.time() - start_time
            
            state_after = analyzer.capture_async_state("hanging_completed")
            analyzer.log_state(state_after)
            
            print(f"✅ System generation completed in {duration:.1f}s (unexpected!)")
            return True
            
        except asyncio.TimeoutError:
            duration = time.time() - start_time
            
            # Capture during hang
            state_hang = analyzer.capture_async_state("hanging_during")
            analyzer.log_state(state_hang)
            
            print(f"⏰ System generation HUNG after {duration:.1f}s (expected)")
            return False
            
    except Exception as e:
        state_error = analyzer.capture_async_state("hanging_error")
        analyzer.log_state(state_error)
        print(f"❌ System generation setup failed: {e}")
        return False

async def run_context_analysis():
    """Run complete async context analysis"""
    print("🔍 ASYNC CONTEXT ANALYSIS")
    print("=" * 60)
    
    # Test working scenario
    working_success = await test_working_llm_call()
    
    # Test hanging scenario  
    hanging_success = await test_hanging_system_generation()
    
    # Compare contexts
    print("\n" + "=" * 60)
    print("📊 CONTEXT ANALYSIS RESULTS")
    print("=" * 60)
    
    # Compare key transition points
    if "working_before" in analyzer.context_data and "hanging_before" in analyzer.context_data:
        analyzer.compare_contexts("working_before", "hanging_before")
        
    if "working_init" in analyzer.context_data and "hanging_before_generation" in analyzer.context_data:
        analyzer.compare_contexts("working_init", "hanging_before_generation")
        
    if "working_after" in analyzer.context_data and "hanging_during" in analyzer.context_data:
        analyzer.compare_contexts("working_after", "hanging_during")
        
    # Summary
    print(f"\n🎯 ANALYSIS SUMMARY:")
    print(f"   Working LLM Call: {'✅' if working_success else '❌'}")
    print(f"   System Generation: {'✅' if hanging_success else '❌'}")
    print(f"   Context Data Points: {len(analyzer.context_data)}")
    
    # Save detailed data
    import json
    output_file = "/home/brian/projects/autocoder4_cc/api_hang_timeout/async_context_data.json"
    with open(output_file, 'w') as f:
        # Convert to JSON-serializable format
        json_data = {}
        for key, value in analyzer.context_data.items():
            json_data[key] = {}
            for k, v in value.items():
                if isinstance(v, (str, int, float, bool, list)):
                    json_data[key][k] = v
                else:
                    json_data[key][k] = str(v)
        json.dump(json_data, f, indent=2)
    
    print(f"   Detailed data saved: {output_file}")

if __name__ == "__main__":
    asyncio.run(run_context_analysis())