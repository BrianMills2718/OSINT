"""
Quick Examples - Copy these patterns into your projects
"""

from universal_llm import chat, code, reason, structured, compare

# Example 1: Simple chat
def example_chat():
    response = chat("Explain machine learning in simple terms")
    print(response)

# Example 2: Code execution
def example_code():
    result = code("Create a function to calculate compound interest")
    print(result)

# Example 3: Complex reasoning  
def example_reasoning():
    problem = "A train leaves NYC at 2pm going 60mph. Another leaves Boston at 3pm going 80mph. They're 200 miles apart. When do they meet?"
    solution = reason(problem)
    print(solution)

# Example 4: JSON output
def example_json():
    prompt = "List the top 3 programming languages with their main uses"
    json_response = structured(prompt)
    print(json_response)

# Example 5: Compare models
def example_compare():
    results = compare("Write a creative story opening", ["smart", "fast"])
    for model, response in results.items():
        print(f"{model}: {response[:100]}...")

# Example 6: Error handling
def example_with_fallbacks():
    try:
        # This will automatically fallback if primary model fails
        response = chat("Hello world")
        print(f"Success: {response}")
    except Exception as e:
        print(f"All models failed: {e}")

if __name__ == "__main__":
    print("🚀 Quick Examples")
    print("Run individual functions to test each capability")
    
    # Uncomment to test:
    # example_chat()
    # example_code() 
    # example_reasoning()
    # example_json()
    # example_compare()
    # example_with_fallbacks()