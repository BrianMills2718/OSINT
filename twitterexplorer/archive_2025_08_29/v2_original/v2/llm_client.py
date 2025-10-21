"""Fixed LiteLLM client using true structured output"""

import os
import json
from typing import Type, TypeVar, Optional
from pydantic import BaseModel
from litellm import completion
import litellm

T = TypeVar('T', bound=BaseModel)

class LLMClient:
    """LiteLLM client with true structured output support"""
    
    def __init__(self, model: Optional[str] = None):
        self.model = model or "gemini/gemini-2.0-flash-exp"
        
        # Load API key from secrets
        api_key = self._load_api_key()
        if api_key:
            os.environ['GEMINI_API_KEY'] = api_key
        
        # Enable JSON validation for better error messages
        litellm.enable_json_schema_validation = True
    
    def generate(self, prompt: str, response_model: Type[T], temperature: float = 0.7) -> T:
        """Generate structured output using response_format directly"""
        messages = [{"role": "user", "content": prompt}]
        
        try:
            # Use structured output directly (not JSON mode)
            response = completion(
                model=self.model,
                messages=messages,
                response_format=response_model,  # Pass model class directly
                temperature=temperature
            )
            
            # Parse response based on what Gemini returns
            content = response.choices[0].message.content
            
            if isinstance(content, dict):
                # Gemini returned a dict - instantiate the model
                return response_model(**content)
            elif isinstance(content, str):
                # Gemini returned JSON string - parse it
                try:
                    data = json.loads(content)
                    return response_model(**data)
                except json.JSONDecodeError:
                    # Sometimes Gemini returns the object as a string representation
                    # Try to extract JSON from the string
                    import re
                    json_match = re.search(r'\{.*\}', content, re.DOTALL)
                    if json_match:
                        data = json.loads(json_match.group())
                        return response_model(**data)
                    raise
            elif isinstance(content, response_model):
                # Already a Pydantic model instance
                return content
            else:
                raise ValueError(f"Unexpected response type: {type(content)}")
                
        except Exception as e:
            print(f"Structured output generation error: {e}")
            
            # Check if it's a schema issue
            if "params.properties" in str(e) or "should be non-empty" in str(e):
                print("Schema incompatibility detected - this should not happen with fixed models!")
                print(f"Model: {response_model.__name__}")
                print(f"Schema: {response_model.model_json_schema()}")
            
            # For production, we should fail fast rather than return defaults
            raise e
    
    def generate_with_fallback(self, prompt: str, response_model: Type[T], temperature: float = 0.7) -> T:
        """Generate with automatic fallback to JSON mode if structured output fails"""
        try:
            # Try structured output first
            return self.generate(prompt, response_model, temperature)
        except Exception as e:
            if "params.properties" in str(e) or "should be non-empty" in str(e):
                print(f"Falling back to JSON mode due to schema issue: {e}")
                return self._generate_with_json_mode(prompt, response_model, temperature)
            raise
    
    def _generate_with_json_mode(self, prompt: str, response_model: Type[T], temperature: float) -> T:
        """Fallback to JSON mode for incompatible schemas"""
        # Add schema to prompt for JSON mode
        schema_desc = f"\n\nReturn a valid JSON object matching this structure:\n{response_model.model_json_schema()}"
        messages = [{"role": "user", "content": prompt + schema_desc}]
        
        response = completion(
            model=self.model,
            messages=messages,
            response_format={"type": "json_object"},  # JSON mode
            temperature=temperature
        )
        
        content = response.choices[0].message.content
        if isinstance(content, str):
            data = json.loads(content)
            return response_model(**data)
        return response_model(**content)
    
    def _load_api_key(self) -> Optional[str]:
        """Load API key from secrets.toml"""
        try:
            import toml
            secrets_path = r'C:\Users\Brian\projects\twitterexplorer\twitterexplorer\.streamlit\secrets.toml'
            secrets = toml.load(secrets_path)
            return secrets.get('GEMINI_API_KEY')
        except:
            return os.getenv('GEMINI_API_KEY')