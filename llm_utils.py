#!/usr/bin/env python3
"""
Unified LLM API wrapper for handling both gpt-5-mini and other models.

gpt-5-mini uses litellm.responses() API with different parameters:
- input (str) instead of messages (list)
- text (dict) instead of response_format (dict)
- Different response structure

Other models use litellm.completion() API:
- messages (list)
- response_format (dict)
- Standard response structure
"""

import litellm
import asyncio
import json
from typing import List, Dict, Any, Optional


class UnifiedLLM:
    """
    Unified wrapper for LiteLLM supporting both gpt-5-mini and other models.

    Usage:
        # Async completion
        response = await UnifiedLLM.acompletion(
            model="gpt-5-mini",
            messages=[{"role": "user", "content": "Hello"}]
        )

        # Async JSON completion
        response = await UnifiedLLM.acompletion(
            model="gpt-5-mini",
            messages=[{"role": "user", "content": "Generate JSON"}],
            response_format={
                "type": "json_schema",
                "json_schema": {
                    "strict": True,
                    "name": "schema_name",
                    "schema": {...}
                }
            }
        )
    """

    @staticmethod
    def is_responses_api_model(model: str) -> bool:
        """Check if model requires responses() API instead of completion()."""
        return 'gpt-5' in model.lower()

    @staticmethod
    def convert_messages_to_input(messages: List[Dict[str, str]]) -> str:
        """
        Convert messages array to input string for responses() API.

        Args:
            messages: List of message dicts with 'role' and 'content'

        Returns:
            Formatted input string
        """
        parts = []
        for msg in messages:
            role = msg.get('role', 'user')
            content = msg.get('content', '')

            if role == 'system':
                parts.append(f"System: {content}")
            elif role == 'assistant':
                parts.append(f"Assistant: {content}")
            else:
                parts.append(f"User: {content}")

        return "\n\n".join(parts)

    @staticmethod
    def convert_response_format(response_format: Optional[Dict]) -> Dict:
        """
        Convert completion() response_format to responses() text format.

        Args:
            response_format: Standard response_format dict

        Returns:
            text dict for responses() API
        """
        if not response_format:
            return {"format": {"type": "text"}}

        # Handle json_object format
        if response_format.get("type") == "json_object":
            return {"format": {"type": "text"}}  # Will return JSON naturally

        # Handle json_schema format
        if response_format.get("type") == "json_schema":
            json_schema = response_format.get("json_schema", {})
            return {
                "format": {
                    "type": "json_schema",
                    "name": json_schema.get("name", "response_schema"),
                    "schema": json_schema.get("schema", {}),
                    "strict": json_schema.get("strict", True)
                }
            }

        # Default to text
        return {"format": {"type": "text"}}

    @staticmethod
    def extract_responses_content(response) -> str:
        """
        Extract text from responses() API response.

        Args:
            response: Response from litellm.responses()

        Returns:
            Extracted text content
        """
        texts = []

        if hasattr(response, 'output'):
            for item in response.output:
                if hasattr(item, 'content'):
                    for c in item.content:
                        if hasattr(c, 'text'):
                            texts.append(c.text)
                elif hasattr(item, 'type') and item.type == 'message':
                    for c in item.content:
                        if hasattr(c, 'text'):
                            texts.append(c.text)

        return "\n".join(texts) if texts else str(response)

    @classmethod
    async def acompletion(cls,
                          model: str,
                          messages: List[Dict[str, str]],
                          response_format: Optional[Dict] = None,
                          **kwargs) -> Any:
        """
        Unified async completion supporting both APIs.

        Automatically routes to responses() or completion() based on model.

        Args:
            model: Model name (e.g., "gpt-5-mini", "gpt-4o-mini")
            messages: List of message dicts
            response_format: Standard response format dict
            **kwargs: Additional parameters (max_tokens, temperature, etc.)

        Returns:
            Response object (format depends on API used)
        """

        if cls.is_responses_api_model(model):
            # Use responses() API for gpt-5-mini
            input_text = cls.convert_messages_to_input(messages)
            text_format = cls.convert_response_format(response_format)

            # Convert max_tokens to max_output_tokens for responses() API
            if 'max_tokens' in kwargs:
                kwargs['max_output_tokens'] = kwargs.pop('max_tokens')

            # Wrap sync responses() in executor
            loop = asyncio.get_event_loop()
            response = await loop.run_in_executor(
                None,
                lambda: litellm.responses(
                    model=model,
                    input=input_text,
                    text=text_format,
                    **kwargs
                )
            )

            # Create a response object that looks like completion() response
            class ResponseWrapper:
                def __init__(self, content):
                    self.choices = [type('obj', (object,), {
                        'message': type('obj', (object,), {
                            'content': content
                        })()
                    })()]

            content = cls.extract_responses_content(response)
            return ResponseWrapper(content)

        else:
            # Use completion() API for other models
            return await litellm.acompletion(
                model=model,
                messages=messages,
                response_format=response_format,
                **kwargs
            )


# Convenience function matching litellm.acompletion signature
async def acompletion(model: str, messages: List[Dict[str, str]], **kwargs) -> Any:
    """
    Drop-in replacement for litellm.acompletion that supports gpt-5-mini.

    Args:
        model: Model name
        messages: List of message dicts
        **kwargs: Additional parameters

    Returns:
        Response object
    """
    return await UnifiedLLM.acompletion(model, messages, **kwargs)
