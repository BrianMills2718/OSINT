import os
import json
from typing import Type, TypeVar, Optional
from pydantic import BaseModel
from litellm import completion
import litellm

T = TypeVar('T', bound=BaseModel)

class LLMClient:
    """LiteLLM client with structured output support"""
    
    def __init__(self, model: Optional[str] = None):
        self.model = model or "gemini/gemini-2.0-flash-exp"
        
        # Load API key from secrets
        api_key = self._load_api_key()
        if api_key:
            os.environ['GEMINI_API_KEY'] = api_key
        
        # Enable JSON validation
        litellm.enable_json_schema_validation = True
    
    def generate(self, prompt: str, response_model: Type[T], temperature: float = 0.7) -> T:
        """Generate structured output"""
        # Add schema description to prompt for better results
        schema_desc = f"\n\nReturn a valid JSON object matching this structure:\n{response_model.model_json_schema()}"
        messages = [{"role": "user", "content": prompt + schema_desc}]
        
        try:
            # Use JSON mode for Gemini (structured output has issues with nested objects)
            response = completion(
                model=self.model,
                messages=messages,
                response_format={"type": "json_object"},
                temperature=temperature
            )
            
            # Parse response
            content = response.choices[0].message.content
            if isinstance(content, str):
                data = json.loads(content)
                return response_model(**data)
            return response_model(**content)
            
        except Exception as e:
            print(f"LLM generation error: {e}")
            # Return model with default values on failure
            if response_model.__name__ == "StrategyOutput":
                from v2.models import EndpointPlan
                return response_model(
                    reasoning="Error generating strategy",
                    endpoints=[EndpointPlan(
                        endpoint="search.php",
                        params={"query": "test"},
                        expected_value="test"
                    )],
                    user_update="Using fallback strategy due to error"
                )
            raise e
    
    def _load_api_key(self) -> Optional[str]:
        """Load API key from secrets.toml"""
        try:
            import toml
            secrets_path = r'C:\Users\Brian\projects\twitterexplorer\twitterexplorer\.streamlit\secrets.toml'
            secrets = toml.load(secrets_path)
            return secrets.get('GEMINI_API_KEY')
        except:
            return os.getenv('GEMINI_API_KEY')