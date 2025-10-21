"""
Universal LLM Kit - Complete Demo
Demonstrates all capabilities: chat, code execution, function calling, structured output, model comparison
"""

from universal_llm import UniversalLLM, chat, code, reason, structured, compare
from pydantic import BaseModel
from typing import List
import json
import os

def demo_basic_chat():
    """Demo 1: Basic chat with automatic provider selection"""
    print("🗣️  DEMO 1: Basic Chat")
    print("=" * 50)
    
    # Simple chat - automatically picks best available model
    response = chat("Explain quantum computing in one sentence")
    print(f"Response: {response}\n")

def demo_code_execution():
    """Demo 2: Code execution with Gemini"""
    print("💻 DEMO 2: Code Execution")  
    print("=" * 50)
    
    # Code execution - uses Gemini's native code execution
    prompts = [
        "Calculate the first 10 fibonacci numbers",
        "Create a bar chart showing monthly sales: Jan=100, Feb=150, Mar=200, Apr=175",
        "Find all prime numbers between 1 and 50"
    ]
    
    for prompt in prompts:
        print(f"Prompt: {prompt}")
        try:
            response = code(prompt)
            print(f"Response: {response[:200]}...")
        except Exception as e:
            print(f"Error: {e}")
        print()

def demo_reasoning():
    """Demo 3: Complex reasoning with o1 models"""
    print("🧠 DEMO 3: Complex Reasoning")
    print("=" * 50)
    
    reasoning_prompt = """
    A company has 3 factories. Factory A produces 100 units/day, Factory B produces 150 units/day, 
    Factory C produces 200 units/day. If demand increases by 25% and they need to meet it by 
    increasing production proportionally across all factories, how many additional workers are 
    needed if each worker produces 10 units/day?
    """
    
    response = reason(reasoning_prompt)
    print(f"O1 Reasoning: {response}\n")

def demo_function_calling():
    """Demo 4: Function calling"""
    print("🔧 DEMO 4: Function Calling")
    print("=" * 50)
    
    # Define functions the LLM can call
    tools = [
        {
            "type": "function",
            "function": {
                "name": "get_weather",
                "description": "Get current weather for a location",
                "parameters": {
                    "type": "object",
                    "properties": {
                        "location": {"type": "string", "description": "City name"},
                        "unit": {"type": "string", "enum": ["celsius", "fahrenheit"]}
                    },
                    "required": ["location"]
                }
            }
        }
    ]
    
    llm = UniversalLLM()
    try:
        response = llm.function_call("What's the weather in San Francisco?", tools)
        print(f"Function call response: {response.choices[0].message}")
    except Exception as e:
        print(f"Function calling error: {e}")
    print()

def demo_structured_output():
    """Demo 5: Structured output with Pydantic"""
    print("📋 DEMO 5: Structured Output")
    print("=" * 50)
    
    # Define a Pydantic model for structured output
    class PersonInfo(BaseModel):
        name: str
        age: int
        occupation: str
        skills: List[str]
    
    prompt = "Create a profile for a fictional software engineer named Alex"
    
    try:
        response = structured(prompt, PersonInfo)
        print(f"Structured JSON: {response}")
        
        # Parse the JSON to verify structure
        parsed = json.loads(response)
        print(f"Parsed name: {parsed.get('name')}")
        print(f"Parsed skills: {parsed.get('skills')}")
    except Exception as e:
        print(f"Structured output error: {e}")
    print()

def demo_model_comparison():
    """Demo 6: Compare responses across models"""
    print("⚖️  DEMO 6: Model Comparison")
    print("=" * 50)
    
    prompt = "Write a haiku about artificial intelligence"
    
    results = compare(prompt, ["smart", "fast", "code"])
    
    for model, response in results.items():
        print(f"{model.upper()} Model:")
        print(f"  {response}")
        print()

def demo_advanced_features():
    """Demo 7: Advanced features and error handling"""
    print("🚀 DEMO 7: Advanced Features")
    print("=" * 50)
    
    llm = UniversalLLM()
    
    # Show available models
    print("Available models:")
    for model in llm.router.model_list:
        model_name = model["litellm_params"]["model"]
        print(f"  - {model['model_name']}: {model_name}")
    print()
    
    # Test fallback behavior
    print("Testing fallback behavior...")
    try:
        # This should automatically fallback if one provider fails
        response = llm.chat("Hello world", model_type="smart") 
        print(f"Fallback test successful: {response[:50]}...")
    except Exception as e:
        print(f"Fallback test error: {e}")
    print()

def main():
    """Run all demos"""
    print("🌟 Universal LLM Kit - Complete Demo")
    print("=" * 60)
    print()
    
    # Check if any API keys are set
    api_keys = ["OPENAI_API_KEY", "ANTHROPIC_API_KEY", "GEMINI_API_KEY", "OPENROUTER_API_KEY"]
    available_keys = [key for key in api_keys if os.getenv(key)]
    
    if not available_keys:
        print("❌ No API keys found! Please set up your .env file first.")
        print("Copy .env.template to .env and add your API keys.")
        return
    
    print(f"✅ Found API keys: {', '.join(available_keys)}")
    print()
    
    # Run all demos
    try:
        demo_basic_chat()
        demo_code_execution()
        demo_reasoning()
        demo_function_calling()
        demo_structured_output()
        demo_model_comparison()
        demo_advanced_features()
        
        print("🎉 All demos completed!")
        
    except Exception as e:
        print(f"Demo error: {e}")
        print("Make sure you have valid API keys in your .env file")

if __name__ == "__main__":
    main()