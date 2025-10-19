#WORKING
# litellm_gpt5mini_demo_fixed.py
import os
from dotenv import load_dotenv
import litellm
from pydantic import BaseModel
from typing import List

load_dotenv()
MODEL = "gpt-5-mini"

# Helper extractor
def get_text(resp):
    texts = []
    for item in resp.output:
        if hasattr(item, "content"):
            for c in item.content:
                if hasattr(c, "text"):
                    texts.append(c.text)
    return "\n".join(texts)

# ------------------------------------------------------------------
# 1) Freeform SQL
# ------------------------------------------------------------------
print("="*80)
print("1) Freeform — SQL (LiteLLM)")
print("="*80)
resp_sql = litellm.responses(
    model=MODEL,
    input="Write a SQL query that selects all users older than 30.",
    text={"format": {"type": "text"}},
)
print(get_text(resp_sql))

# ------------------------------------------------------------------
# 1b) Freeform Python
# ------------------------------------------------------------------
print("="*80)
print("1b) Freeform — Python (LiteLLM)")
print("="*80)
resp_py = litellm.responses(
    model=MODEL,
    input="Write a Python function to compute factorial safely.",
    text={"format": {"type": "text"}},
)
print(get_text(resp_py))

# ------------------------------------------------------------------
# 2) Strict JSON Schema — Simple Object
# ------------------------------------------------------------------
print("="*80)
print("2) Strict JSON Schema — Simple Object")
print("="*80)

class Concept(BaseModel):
    term: str
    definition: str
    difficulty: int

resp_obj = litellm.responses(
    model=MODEL,
    input="Give me the concept 'recursion' in JSON according to the schema.",
    text={
        "format": {
            "type": "json_schema",
            "name": "concept_schema",
            "schema": {
                "type": "object",
                "properties": {
                    "term": {"type": "string"},
                    "definition": {"type": "string"},
                    "difficulty": {"type": "integer", "minimum": 1, "maximum": 5},
                },
                "required": ["term", "definition", "difficulty"],
                "additionalProperties": False,
            },
            "strict": True,
        }
    },
)

json_str = get_text(resp_obj)
print(json_str)
print("✅", Concept.model_validate_json(json_str).model_dump())

# ------------------------------------------------------------------
# 3) Strict JSON Schema — Array of Objects
# ------------------------------------------------------------------
print("="*80)
print("3) Strict JSON Schema — Array of Objects")
print("="*80)

class Product(BaseModel):
    name: str
    price: float
    in_stock: bool

class Catalog(BaseModel):
    products: List[Product]

resp_catalog = litellm.responses(
    model=MODEL,
    input="Give me a catalog of 3 fictional products in JSON according to the schema.",
    text={
        "format": {
            "type": "json_schema",
            "name": "catalog_schema",
            "schema": {
                "type": "object",
                "properties": {
                    "products": {
                        "type": "array",
                        "items": {
                            "type": "object",
                            "properties": {
                                "name": {"type": "string"},
                                "price": {"type": "number"},
                                "in_stock": {"type": "boolean"},
                            },
                            "required": ["name", "price", "in_stock"],
                            "additionalProperties": False,
                        },
                    }
                },
                "required": ["products"],
                "additionalProperties": False,
            },
            "strict": True,
        }
    },
)

json_str = get_text(resp_catalog)
print(json_str)
print("✅", Catalog.model_validate_json(json_str).model_dump())

# ------------------------------------------------------------------
# 4) Strict JSON Schema — Enum
# ------------------------------------------------------------------
print("="*80)
print("4) Strict JSON Schema — Enum")
print("="*80)

class Task(BaseModel):
    title: str
    difficulty: str

resp_enum = litellm.responses(
    model=MODEL,
    input="Give me one example task in JSON according to the schema.",
    text={
        "format": {
            "type": "json_schema",
            "name": "task_schema",
            "schema": {
                "type": "object",
                "properties": {
                    "title": {"type": "string"},
                    "difficulty": {"type": "string", "enum": ["easy", "medium", "hard"]},
                },
                "required": ["title", "difficulty"],
                "additionalProperties": False,
            },
            "strict": True,
        }
    },
)

json_str = get_text(resp_enum)
print(json_str)
print("✅", Task.model_validate_json(json_str).model_dump())
