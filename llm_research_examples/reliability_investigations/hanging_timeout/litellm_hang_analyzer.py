#!/usr/bin/env python3
"""
LiteLLM Hang Analyzer - Investigate why LiteLLM hangs in system context but not isolated context
"""
import sys
import asyncio
import time
import signal
import threading
import aiohttp
import logging
sys.path.insert(0, '/home/brian/projects/autocoder4_cc')

# Set up detailed logging
logging.basicConfig(level=logging.DEBUG)
litellm_logger = logging.getLogger('litellm')
litellm_logger.setLevel(logging.DEBUG)

class LiteLLMHangAnalyzer:
    def __init__(self):
        self.results = {}
        
    async def test_isolated_litellm_call(self):
        """Test LiteLLM call in complete isolation"""
        print("🧪 TESTING ISOLATED LITELLM CALL")
        
        try:
            from dotenv import load_dotenv
            load_dotenv('/home/brian/projects/autocoder4_cc/.env')
            
            import litellm
            
            # Minimal LiteLLM call
            start_time = time.time()
            
            response = await asyncio.wait_for(
                litellm.acompletion(
                    model="gemini/gemini-2.5-flash",
                    messages=[{"role": "user", "content": "Say 'test' and nothing else"}],
                    max_tokens=5,
                    temperature=0.0
                ),
                timeout=15
            )
            
            duration = time.time() - start_time
            content = response.choices[0].message.content
            
            self.results['isolated_litellm'] = {
                'success': True,
                'duration': duration,
                'content': content[:50]
            }
            
            print(f"✅ Isolated LiteLLM call succeeded in {duration:.1f}s: {content}")
            return True
            
        except Exception as e:
            duration = time.time() - start_time
            self.results['isolated_litellm'] = {
                'success': False,
                'duration': duration,
                'error': str(e)
            }
            print(f"❌ Isolated LiteLLM call failed: {e}")
            return False
            
    async def test_unified_provider_litellm_call(self):
        """Test LiteLLM call through UnifiedLLMProvider"""
        print("\n🧪 TESTING LITELLM THROUGH UNIFIED PROVIDER")
        
        try:
            from dotenv import load_dotenv
            load_dotenv('/home/brian/projects/autocoder4_cc/.env')
            
            from autocoder_cc.llm_providers.unified_llm_provider import UnifiedLLMProvider
            from autocoder_cc.llm_providers.base_provider import LLMRequest
            
            provider = UnifiedLLMProvider({'enable_fallback': False})
            
            request = LLMRequest(
                system_prompt="You are a helpful assistant.",
                user_prompt="Say 'unified test' and nothing else.",
                max_tokens=5,
                temperature=0.0
            )
            
            start_time = time.time()
            
            response = await asyncio.wait_for(
                provider.generate(request),
                timeout=15
            )
            
            duration = time.time() - start_time
            
            self.results['unified_provider'] = {
                'success': True,
                'duration': duration,
                'content': response.content[:50]
            }
            
            print(f"✅ Unified provider call succeeded in {duration:.1f}s: {response.content}")
            return True
            
        except Exception as e:
            duration = time.time() - start_time
            self.results['unified_provider'] = {
                'success': False,
                'duration': duration,
                'error': str(e)
            }
            print(f"❌ Unified provider call failed: {e}")
            return False
            
    async def test_system_context_litellm_call(self):
        """Test LiteLLM call within system generation context (expected to hang)"""
        print("\n🧪 TESTING LITELLM IN SYSTEM CONTEXT")
        
        try:
            from dotenv import load_dotenv
            load_dotenv('/home/brian/projects/autocoder4_cc/.env')
            
            # Set up the same context as system generation
            from autocoder_cc.blueprint_language.natural_language_to_blueprint import NaturalLanguageToPydanticTranslator
            from autocoder_cc.blueprint_language.healing_integration import SystemGenerator
            from pathlib import Path
            
            # Initialize all the same components
            translator = NaturalLanguageToPydanticTranslator()
            blueprint_yaml = translator.generate_full_blueprint("Simple test system")
            generator = SystemGenerator(Path("/tmp/litellm_hang_test"), skip_deployment=True)
            
            # Now try the LiteLLM call in this context
            import litellm
            
            start_time = time.time()
            
            # Monitor async state during call
            loop = asyncio.get_event_loop()
            tasks_before = len(asyncio.all_tasks(loop))
            
            print(f"📊 Context before LiteLLM call:")
            print(f"   Active tasks: {tasks_before}")
            print(f"   Active threads: {threading.active_count()}")
            
            response = await asyncio.wait_for(
                litellm.acompletion(
                    model="gemini/gemini-2.5-flash",
                    messages=[{"role": "user", "content": "Say 'system context test' and nothing else"}],
                    max_tokens=5,
                    temperature=0.0
                ),
                timeout=20
            )
            
            duration = time.time() - start_time
            
            self.results['system_context'] = {
                'success': True,
                'duration': duration,
                'content': response.choices[0].message.content[:50]
            }
            
            print(f"✅ System context call succeeded in {duration:.1f}s: {response.choices[0].message.content}")
            return True
            
        except asyncio.TimeoutError:
            duration = time.time() - start_time
            
            # Capture state during hang
            tasks_during = len(asyncio.all_tasks(loop))
            threads_during = threading.active_count()
            
            self.results['system_context'] = {
                'success': False,
                'duration': duration,
                'error': 'TIMEOUT - HUNG',
                'tasks_during': tasks_during,
                'threads_during': threads_during
            }
            
            print(f"⏰ System context call HUNG after {duration:.1f}s")
            print(f"📊 Context during hang:")
            print(f"   Active tasks: {tasks_during}")
            print(f"   Active threads: {threads_during}")
            return False
            
        except Exception as e:
            duration = time.time() - start_time
            
            self.results['system_context'] = {
                'success': False,
                'duration': duration,
                'error': str(e)
            }
            print(f"❌ System context call failed: {e}")
            return False
            
    async def test_event_loop_pollution(self):
        """Test if event loop pollution is causing the hang"""
        print("\n🧪 TESTING EVENT LOOP POLLUTION")
        
        try:
            # Create clean event loop for comparison
            loop = asyncio.get_event_loop()
            
            print(f"📊 Initial loop state:")
            print(f"   Running: {loop.is_running()}")
            print(f"   Debug: {loop.get_debug()}")
            print(f"   Tasks: {len(asyncio.all_tasks(loop))}")
            
            # Try to identify what's polluting the event loop
            tasks = list(asyncio.all_tasks(loop))
            for i, task in enumerate(tasks):
                print(f"   Task {i+1}: {task}")
                
            # Test if we can create a new event loop
            import concurrent.futures
            
            def test_in_new_loop():
                import asyncio
                import litellm
                
                async def clean_litellm_call():
                    response = await litellm.acompletion(
                        model="gemini/gemini-2.5-flash",
                        messages=[{"role": "user", "content": "Say 'clean loop test'"}],
                        max_tokens=5,
                        temperature=0.0
                    )
                    return response.choices[0].message.content
                    
                return asyncio.run(clean_litellm_call())
                
            # Run in thread pool with new event loop
            with concurrent.futures.ThreadPoolExecutor() as executor:
                future = executor.submit(test_in_new_loop)
                result = future.result(timeout=15)
                
            self.results['clean_loop'] = {
                'success': True,
                'content': result
            }
            
            print(f"✅ Clean loop test succeeded: {result}")
            return True
            
        except Exception as e:
            self.results['clean_loop'] = {
                'success': False,
                'error': str(e)
            }
            print(f"❌ Clean loop test failed: {e}")
            return False
            
    def analyze_results(self):
        """Analyze test results to identify root cause"""
        print("\n" + "=" * 60)
        print("🔍 LITELLM HANG ANALYSIS RESULTS")
        print("=" * 60)
        
        for test_name, result in self.results.items():
            status = "✅" if result['success'] else "❌"
            duration = result.get('duration', 0)
            print(f"{status} {test_name}: {duration:.1f}s")
            
            if not result['success']:
                print(f"    Error: {result.get('error', 'Unknown')}")
            else:
                content = result.get('content', '')
                print(f"    Response: {content}")
                
        # Analysis
        print(f"\n🎯 ROOT CAUSE ANALYSIS:")
        
        isolated_works = self.results.get('isolated_litellm', {}).get('success', False)
        unified_works = self.results.get('unified_provider', {}).get('success', False)
        system_works = self.results.get('system_context', {}).get('success', False)
        clean_works = self.results.get('clean_loop', {}).get('success', False)
        
        if isolated_works and unified_works and not system_works:
            print("🎯 CONFIRMED: System generation context causes LiteLLM to hang")
            print("   - LiteLLM works in isolation")
            print("   - UnifiedLLMProvider works")
            print("   - System context breaks LiteLLM")
            
            if clean_works:
                print("   - Clean event loop works")
                print("   - CONCLUSION: Event loop pollution in system generation")
            else:
                print("   - Clean event loop also fails")
                print("   - CONCLUSION: Threading or resource conflict")
                
        elif not isolated_works:
            print("🎯 CONFIRMED: LiteLLM infrastructure issue")
            print("   - LiteLLM fails even in isolation")
            print("   - CONCLUSION: API key, network, or LiteLLM bug")
            
        else:
            print("🤔 INCONCLUSIVE: Unexpected test pattern")
            
        return self.results

async def run_litellm_hang_analysis():
    """Run complete LiteLLM hang analysis"""
    analyzer = LiteLLMHangAnalyzer()
    
    print("🔍 LITELLM HANG ANALYSIS")
    print("=" * 60)
    
    # Run all tests
    await analyzer.test_isolated_litellm_call()
    await analyzer.test_unified_provider_litellm_call()
    await analyzer.test_system_context_litellm_call()
    await analyzer.test_event_loop_pollution()
    
    # Analyze results
    results = analyzer.analyze_results()
    
    # Save results
    import json
    output_file = "/home/brian/projects/autocoder4_cc/api_hang_timeout/litellm_hang_results.json"
    with open(output_file, 'w') as f:
        json.dump(results, f, indent=2)
    
    print(f"\n📊 Results saved: {output_file}")

if __name__ == "__main__":
    asyncio.run(run_litellm_hang_analysis())