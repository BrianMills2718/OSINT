#!/usr/bin/env python3
"""
Example of using Gemini 2.5 Flash-Lite with structured output via LiteLLM
"""
import litellm
import json
from pydantic import BaseModel
from typing import List

# Hardcode API key as requested
import os
os.environ['GEMINI_API_KEY'] = 'AIzaSyCwNW6kO6R0AewqsUgG9IgrDg6vCRFhhHw'

# Enable structured output validation
litellm.enable_json_schema_validation = True
litellm.set_verbose = True  # See raw requests

class Person(BaseModel):
    name: str
    age: int
    occupation: str

class PeopleList(BaseModel):
    people: List[Person]
    total_count: int

def example_with_pydantic():
    """Example using Pydantic models for structured output"""
    print("="*60)
    print("Gemini 2.5 Flash-Lite with Pydantic Structured Output")
    print("="*60)
    
    messages = [
        {
            "role": "system", 
            "content": "Extract person information from the text."
        },
        {
            "role": "user", 
            "content": "John is 30 years old and works as a software engineer. Sarah is 25 and is a doctor. Mike is 45 and teaches mathematics."
        }
    ]
    
    try:
        response = litellm.completion(
            model="gemini/gemini-2.5-flash-lite",  # Gemini 2.5 Flash-Lite
            messages=messages,
            response_format=PeopleList
        )
        
        print("✓ Response received:")
        print(json.dumps(json.loads(response.choices[0].message.content), indent=2))
        
    except Exception as e:
        print(f"✗ Error: {e}")

def example_with_json_schema():
    """Example using raw JSON schema for structured output"""
    print("\n" + "="*60)
    print("Gemini 2.5 Flash-Lite with JSON Schema")
    print("="*60)
    
    messages = [
        {
            "role": "system",
            "content": "Extract recipe information and return as structured JSON."
        },
        {
            "role": "user",
            "content": "Give me 3 simple cookie recipes with ingredients and steps."
        }
    ]
    
    response_schema = {
        "type": "object",
        "properties": {
            "recipes": {
                "type": "array",
                "items": {
                    "type": "object",
                    "properties": {
                        "name": {"type": "string"},
                        "ingredients": {
                            "type": "array",
                            "items": {"type": "string"}
                        },
                        "steps": {
                            "type": "array", 
                            "items": {"type": "string"}
                        },
                        "prep_time": {"type": "string"}
                    },
                    "required": ["name", "ingredients", "steps"],
                    "additionalProperties": False
                }
            },
            "total_recipes": {"type": "integer"}
        },
        "required": ["recipes", "total_recipes"],
        "additionalProperties": False
    }
    
    try:
        response = litellm.completion(
            model="gemini/gemini-2.5-flash-lite",
            messages=messages,
            response_format={
                "type": "json_object",
                "response_schema": response_schema
            }
        )
        
        print("✓ Response received:")
        result = json.loads(response.choices[0].message.content)
        print(json.dumps(result, indent=2))
        
        # Show summary
        print(f"\n✓ Found {result['total_recipes']} recipes:")
        for i, recipe in enumerate(result['recipes'], 1):
            print(f"  {i}. {recipe['name']} ({len(recipe['ingredients'])} ingredients)")
            
    except Exception as e:
        print(f"✗ Error: {e}")

def example_simple_json():
    """Simple JSON object example"""
    print("\n" + "="*60)
    print("Gemini 2.5 Flash-Lite with Simple JSON Output")
    print("="*60)
    
    messages = [
        {
            "role": "system",
            "content": "You are a helpful assistant designed to output JSON."
        },
        {
            "role": "user", 
            "content": "What are the benefits of using AI in healthcare? Return as JSON with categories and benefits."
        }
    ]
    
    try:
        response = litellm.completion(
            model="gemini/gemini-2.5-flash-lite",
            messages=messages,
            response_format={"type": "json_object"}
        )
        
        print("✓ Response received:")
        result = json.loads(response.choices[0].message.content)
        print(json.dumps(result, indent=2))
        
    except Exception as e:
        print(f"✗ Error: {e}")

def main():
    print("Testing Gemini 2.5 Flash-Lite with LiteLLM Structured Output")
    print(f"API Key: {os.environ['GEMINI_API_KEY'][:10]}...")
    
    # Run all examples
    example_with_pydantic()
    example_with_json_schema() 
    example_simple_json()
    
    print("\n" + "="*60)
    print("All examples completed!")
    print("="*60)

if __name__ == "__main__":
    main()