#!/usr/bin/env python3
"""
Fix Implementation - Apply the fix for empty Gemini responses
"""
import sys
sys.path.insert(0, '/home/brian/projects/autocoder4_cc')

def test_fix_validation():
    """Test that the fix resolves the hanging issue"""
    import asyncio
    
    async def test_system_generation_with_fix():
        """Test system generation after applying fix"""
        print("🧪 TESTING SYSTEM GENERATION WITH FIX")
        
        try:
            from dotenv import load_dotenv
            load_dotenv('/home/brian/projects/autocoder4_cc/.env')
            
            from autocoder_cc.blueprint_language.natural_language_to_blueprint import generate_system_from_description_async
            
            # Test with timeout - should complete now
            import time
            start_time = time.time()
            
            result = await asyncio.wait_for(
                generate_system_from_description_async(
                    "Simple test system with source and sink",
                    output_dir="/tmp/fix_validation_test",
                    skip_deployment=True
                ),
                timeout=120  # Give it 2 minutes
            )
            
            duration = time.time() - start_time
            
            print(f"✅ System generation completed in {duration:.1f}s")
            print(f"   Generated system at: {result}")
            
            # Verify the system was actually created
            from pathlib import Path
            system_path = Path(result)
            if system_path.exists():
                files = list(system_path.rglob("*.py"))
                print(f"   Generated {len(files)} Python files")
                
                # Check if main.py exists
                main_py = system_path / "main.py"
                if main_py.exists():
                    print(f"   ✅ main.py exists ({main_py.stat().st_size} bytes)")
                else:
                    print(f"   ❌ main.py missing")
                    
                return True
            else:
                print(f"   ❌ System directory not created")
                return False
                
        except asyncio.TimeoutError:
            print(f"❌ System generation still times out after fix")
            return False
        except Exception as e:
            print(f"❌ System generation failed: {e}")
            import traceback
            traceback.print_exc()
            return False
    
    return asyncio.run(test_system_generation_with_fix())

if __name__ == "__main__":
    print("🔧 TESTING FIX EFFECTIVENESS")
    print("=" * 60)
    
    success = test_fix_validation()
    
    if success:
        print("\n🎯 FIX SUCCESSFUL!")
        print("   System generation is now working")
    else:
        print("\n❌ FIX INCOMPLETE")
        print("   Additional investigation needed")
        
    exit(0 if success else 1)