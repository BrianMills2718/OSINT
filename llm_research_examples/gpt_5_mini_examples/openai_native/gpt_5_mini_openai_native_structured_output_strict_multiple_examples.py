#WORKING CORRECTLY
import os
from dotenv import load_dotenv
from openai import OpenAI
from pydantic import BaseModel
from typing import List

# ------------------------------------------------------------------
# Setup
# ------------------------------------------------------------------
load_dotenv()
client = OpenAI(api_key=os.getenv("OPENAI_API_KEY"))

# ------------------------------------------------------------------
# 1) Simple Object
# ------------------------------------------------------------------
class Concept(BaseModel):
    term: str
    definition: str
    difficulty: int   # e.g. 1=easy, 5=hard

resp1 = client.responses.create(
    model="gpt-5-mini",
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
print("1) Simple Object")
print("="*80)
print(resp1.output_text)
print("✅", Concept.model_validate_json(resp1.output_text).model_dump())


# ------------------------------------------------------------------
# 2) Array of Objects
# ------------------------------------------------------------------
class Product(BaseModel):
    name: str
    price: float
    in_stock: bool

class Catalog(BaseModel):
    products: List[Product]

resp2 = client.responses.create(
    model="gpt-5-mini",
    input="Give me a catalog of 3 fictional products as JSON according to the schema.",
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
                                "in_stock": {"type": "boolean"}
                            },
                            "required": ["name", "price", "in_stock"],
                            "additionalProperties": False
                        }
                    }
                },
                "required": ["products"],
                "additionalProperties": False
            },
            "strict": True
        }
    }
)
print("="*80)
print("2) Array of Objects")
print("="*80)
print(resp2.output_text)
print("✅", Catalog.model_validate_json(resp2.output_text).model_dump())


# ------------------------------------------------------------------
# 3) Nested Objects
# ------------------------------------------------------------------
class Address(BaseModel):
    street: str
    city: str
    zip: str

class Person(BaseModel):
    name: str
    age: int
    address: Address

resp3 = client.responses.create(
    model="gpt-5-mini",
    input="Give me a fictional person with an address in JSON according to the schema.",
    text={
        "format": {
            "type": "json_schema",
            "name": "person_schema",
            "schema": {
                "type": "object",
                "properties": {
                    "name": {"type": "string"},
                    "age": {"type": "integer"},
                    "address": {
                        "type": "object",
                        "properties": {
                            "street": {"type": "string"},
                            "city": {"type": "string"},
                            "zip": {"type": "string"}
                        },
                        "required": ["street", "city", "zip"],
                        "additionalProperties": False
                    }
                },
                "required": ["name", "age", "address"],
                "additionalProperties": False
            },
            "strict": True
        }
    }
)
print("="*80)
print("3) Nested Objects")
print("="*80)
print(resp3.output_text)
print("✅", Person.model_validate_json(resp3.output_text).model_dump())


# ------------------------------------------------------------------
# 4) Enum Field
# ------------------------------------------------------------------
class Task(BaseModel):
    title: str
    difficulty: str  # must be one of "easy", "medium", "hard"

resp4 = client.responses.create(
    model="gpt-5-mini",
    input="Give me one example task in JSON according to the schema.",
    text={
        "format": {
            "type": "json_schema",
            "name": "task_schema",
            "schema": {
                "type": "object",
                "properties": {
                    "title": {"type": "string"},
                    "difficulty": {"type": "string", "enum": ["easy", "medium", "hard"]}
                },
                "required": ["title", "difficulty"],
                "additionalProperties": False
            },
            "strict": True
        }
    }
)
print("="*80)
print("4) Enum Field")
print("="*80)
print(resp4.output_text)
print("✅", Task.model_validate_json(resp4.output_text).model_dump())
