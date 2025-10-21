"""Quick verification that we're using structured output, not JSON mode"""

from llm_client import LLMClient
from models import EndpointPlan
import inspect

# Check the actual source code
client = LLMClient()
source = inspect.getsource(client.generate)

print("=" * 60)
print("STRUCTURED OUTPUT VERIFICATION")
print("=" * 60)

# Look for key indicators
if "response_format=response_model" in source:
    print("[SUCCESS] Found: response_format=response_model")
else:
    print("[FAIL] NOT FOUND: response_format=response_model")

if '"type": "json_object"' in source:
    print("[WARNING] Found JSON mode (should only be in fallback)")
    
# Check if it's in the main method or just fallback
lines = source.split('\n')
for i, line in enumerate(lines):
    if "response_format" in line:
        print(f"Line {i}: {line.strip()}")

print("\n" + "=" * 60)
print("ACTUAL TEST WITH GEMINI API")
print("=" * 60)

try:
    # Test with a simple model
    result = client.generate(
        "Generate an endpoint plan for searching 'test query'",
        EndpointPlan
    )
    print(f"[SUCCESS] Structured output works!")
    print(f"   Type returned: {type(result)}")
    print(f"   Endpoint: {result.endpoint}")
    print(f"   Query: {result.query}")
    print(f"   Params dict: {result.to_params_dict()}")
except Exception as e:
    print(f"[FAIL] Error: {e}")
    if "params.properties" in str(e):
        print("   This is the schema compatibility error!")

print("=" * 60)