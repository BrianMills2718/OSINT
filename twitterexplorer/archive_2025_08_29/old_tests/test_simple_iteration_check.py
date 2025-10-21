"""Simple check of iteration behavior"""
import sys
import os

current_dir = os.path.dirname(os.path.abspath(__file__))
twitterexplorer_path = os.path.join(current_dir, 'twitterexplorer')
sys.path.insert(0, twitterexplorer_path)

from investigation_engine import InvestigationEngine, InvestigationConfig

print("=== SIMPLE ITERATION CHECK ===\n")

api_key = "d72bcd77e2msh76c7e6cf37f0b89p1c51bcjsnaad0f6b01e4f"
engine = InvestigationEngine(api_key)

# Test 1: Small max_searches (should stop after 1 round)
print("Test 1: max_searches=2")
config1 = InvestigationConfig(max_searches=2, pages_per_search=1)
result1 = engine.conduct_investigation("test1", config1)
print(f"  Searches: {result1.search_count}, Rounds: {result1.round_count if hasattr(result1, 'round_count') else len(getattr(result1, 'rounds', []))}")

# Test 2: Larger max_searches (should allow multiple rounds)  
print("\nTest 2: max_searches=10")
config2 = InvestigationConfig(max_searches=10, pages_per_search=1)
result2 = engine.conduct_investigation("test2", config2)
print(f"  Searches: {result2.search_count}, Rounds: {result2.round_count if hasattr(result2, 'round_count') else len(getattr(result2, 'rounds', []))}")

# Test 3: Very large max_searches
print("\nTest 3: max_searches=20")
config3 = InvestigationConfig(max_searches=20, pages_per_search=1)
result3 = engine.conduct_investigation("test3", config3)
print(f"  Searches: {result3.search_count}, Rounds: {result3.round_count if hasattr(result3, 'round_count') else len(getattr(result3, 'rounds', []))}")

print("\nCONCLUSION:")
if result2.search_count <= 3:
    print("  PROBLEM: System stops after first round regardless of max_searches")
elif result2.search_count > result1.search_count:
    print("  WORKING: System continues based on max_searches")
else:
    print("  UNCLEAR: Need more investigation")