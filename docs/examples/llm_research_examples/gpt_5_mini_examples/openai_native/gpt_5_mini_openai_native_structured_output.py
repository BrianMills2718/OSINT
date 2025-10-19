#WORKING CORRECTLY
import os
import json
from dotenv import load_dotenv
from openai import OpenAI

# ------------------------------------------------------------------
# Setup
# ------------------------------------------------------------------
load_dotenv()
client = OpenAI(api_key=os.getenv("OPENAI_API_KEY"))

# ------------------------------------------------------------------
# Example 1. Plain Text
# ------------------------------------------------------------------
resp_text = client.responses.create(
    model="gpt-5-mini",
    input="Explain recursion in one sentence.",
    text={"format": {"type": "text"}}   # ✅ enforce plain text
)

print("="*80)
print("1) Plain text")
print("="*80)
print(resp_text.output_text)


# ------------------------------------------------------------------
# Example 2. JSON Object
# ------------------------------------------------------------------
resp_json = client.responses.create(
    model="gpt-5-mini",
    input="Return a JSON object with two fields: 'term' and 'definition' for recursion. Respond in JSON only.",
    text={"format": {"type": "json_object"}}   # ✅ structured JSON
)

print("="*80)
print("2) JSON Object (structured output)")
print("="*80)
print(resp_json.output_text)

parsed = json.loads(resp_json.output_text)
print("Parsed keys:", list(parsed.keys()))
