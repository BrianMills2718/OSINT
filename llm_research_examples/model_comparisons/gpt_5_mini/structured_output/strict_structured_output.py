#WORKING CORRECTLY
import os
from dotenv import load_dotenv
from openai import OpenAI
from pydantic import BaseModel

# ------------------------------------------------------------------
# Setup
# ------------------------------------------------------------------
load_dotenv()
client = OpenAI(api_key=os.getenv("OPENAI_API_KEY"))

# Example 3. JSON Schema + strict
# ------------------------------------------------------------------
class Concept(BaseModel):
    term: str
    definition: str
    difficulty: int   # e.g. 1=easy, 5=hard

resp_schema = client.responses.create(
    model="gpt-5-mini",
    input="Give me the concept 'recursion' in JSON according to the schema. Respond in JSON only.",
    text={
        "format": {
            "type": "json_schema",
            "name": "concept_schema",
            "schema": {  # ✅ correct location
                "type": "object",
                "properties": {
                    "term": {"type": "string"},
                    "definition": {"type": "string"},
                    "difficulty": {"type": "integer", "minimum": 1, "maximum": 5}
                },
                "required": ["term", "definition", "difficulty"],
                "additionalProperties": False
            },
            "strict": True
        }
    }
)

print("="*80)
print("3) JSON Schema + strict")
print("="*80)
print(resp_schema.output_text)

# Validate against Pydantic
validated = Concept.model_validate_json(resp_schema.output_text)
print("✅ Validated via Pydantic:", validated.model_dump())
