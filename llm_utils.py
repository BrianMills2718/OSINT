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

Features:
- Automatic API routing based on model
- Provider fallback support (try alternative models if primary fails)
- Configuration integration
- Cost tracking (LiteLLM built-in)
"""

import litellm
import asyncio
import json
from typing import List, Dict, Any, Optional
import logging
from datetime import datetime

# Import config (will use default if config.yaml doesn't exist)
try:
    from config_loader import config
    HAS_CONFIG = True
except Exception:
    HAS_CONFIG = False
    config = None

# Cost tracking storage
_cost_tracker = {
    "total_cost": 0.0,
    "calls": [],
    "by_model": {}
}


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
        # FIXED: Check response.output exists AND is not None
        if hasattr(response, 'output') and response.output:
            for item in response.output:
                # Look for the message type output
                if hasattr(item, 'type') and item.type == 'message':
                    if hasattr(item, 'content'):
                        texts = []
                        for content in item.content:
                            if hasattr(content, 'text'):
                                texts.append(content.text)
                        if texts:
                            return "\n".join(texts)

        # Fallback: return string representation
        return str(response)

    @classmethod
    async def acompletion(cls,
                          model: str,
                          messages: List[Dict[str, str]],
                          response_format: Optional[Dict] = None,
                          fallback: bool = True,
                          **kwargs) -> Any:
        """
        Unified async completion supporting both APIs with fallback.

        Automatically routes to responses() or completion() based on model.
        If primary model fails and fallback is enabled, tries fallback models.

        Args:
            model: Model name (e.g., "gpt-5-mini", "gpt-4o-mini")
            messages: List of message dicts
            response_format: Standard response format dict
            fallback: Enable fallback to alternative models (default: True)
            **kwargs: Additional parameters (max_tokens, temperature, etc.)

        Returns:
            Response object (format depends on API used)

        Raises:
            Exception: If all models (primary + fallbacks) fail
        """

        # Determine models to try
        models_to_try = [model]

        if fallback and HAS_CONFIG and config.fallback_enabled:
            models_to_try.extend(config.fallback_models)

        last_error = None

        # Try each model in sequence
        for attempt_model in models_to_try:
            try:
                return await cls._single_completion(
                    attempt_model, messages, response_format, **kwargs
                )
            except Exception as e:
                last_error = e
                if attempt_model != models_to_try[-1]:
                    logging.warning(
                        f"Model {attempt_model} failed: {e}. Trying fallback..."
                    )
                continue

        # All models failed
        raise Exception(
            f"All models failed. Last error from {models_to_try[-1]}: {last_error}"
        )

    @classmethod
    async def _single_completion(cls,
                                 model: str,
                                 messages: List[Dict[str, str]],
                                 response_format: Optional[Dict] = None,
                                 **kwargs) -> Any:
        """
        Execute a single completion attempt with the specified model.

        Internal method used by acompletion for retries/fallback.
        """

        if cls.is_responses_api_model(model):
            # Use responses() API for gpt-5-mini
            input_text = cls.convert_messages_to_input(messages)
            text_format = cls.convert_response_format(response_format)

            # IMPORTANT: DO NOT use max_output_tokens with gpt-5-mini!
            # gpt-5 uses reasoning tokens before output tokens.
            # If max_output_tokens is set, it can exhaust them on reasoning
            # and return empty output (while still billing you).
            # Let the model use as many tokens as it needs.
            kwargs_copy = kwargs.copy()
            kwargs_copy.pop('max_tokens', None)  # Remove if accidentally passed
            kwargs_copy.pop('max_output_tokens', None)  # Remove if accidentally passed

            # Wrap sync responses() in executor
            loop = asyncio.get_event_loop()
            response = await loop.run_in_executor(
                None,
                lambda: litellm.responses(
                    model=model,
                    input=input_text,
                    text=text_format,
                    **kwargs_copy
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
    start_time = datetime.now()
    response = await UnifiedLLM.acompletion(model, messages, **kwargs)

    # Calculate and track cost using LiteLLM's built-in function
    try:
        cost = litellm.completion_cost(completion_response=response)
        if cost > 0:
            _track_cost(model, cost, start_time)
    except Exception as e:
        # Cost tracking failed - log but don't fail the request
        logging.debug(f"Cost tracking failed: {e}")

    return response


# ============================================================================
# Cost Tracking Functions
# ============================================================================

def _track_cost(model: str, cost: float, timestamp: datetime):
    """Track cost of an LLM call."""
    global _cost_tracker

    _cost_tracker["total_cost"] += cost
    _cost_tracker["calls"].append({
        "model": model,
        "cost": cost,
        "timestamp": timestamp.isoformat()
    })

    if model not in _cost_tracker["by_model"]:
        _cost_tracker["by_model"][model] = {"cost": 0.0, "calls": 0}

    _cost_tracker["by_model"][model]["cost"] += cost
    _cost_tracker["by_model"][model]["calls"] += 1


def get_total_cost() -> float:
    """
    Get total cost of all LLM calls since program start.

    Returns:
        Total cost in USD
    """
    return _cost_tracker["total_cost"]


def get_cost_breakdown() -> Dict[str, Any]:
    """
    Get detailed cost breakdown by model.

    Returns:
        Dict with cost information:
        {
            "total_cost": 0.15,
            "by_model": {
                "gpt-5-mini": {"cost": 0.10, "calls": 5},
                "gpt-5-nano": {"cost": 0.05, "calls": 10}
            },
            "num_calls": 15
        }
    """
    return {
        "total_cost": _cost_tracker["total_cost"],
        "by_model": _cost_tracker["by_model"],
        "num_calls": len(_cost_tracker["calls"])
    }


def get_cost_summary() -> str:
    """
    Get human-readable cost summary.

    Returns:
        Formatted cost summary string
    """
    breakdown = get_cost_breakdown()

    lines = [
        "=" * 60,
        "LLM COST SUMMARY",
        "=" * 60,
        f"Total Cost: ${breakdown['total_cost']:.4f}",
        f"Total Calls: {breakdown['num_calls']}",
        "",
        "By Model:",
        "-" * 60
    ]

    for model, data in sorted(breakdown['by_model'].items()):
        avg_cost = data['cost'] / data['calls'] if data['calls'] > 0 else 0
        lines.append(
            f"  {model:30s} ${data['cost']:>8.4f}  ({data['calls']:>4d} calls, ${avg_cost:.4f}/call)"
        )

    lines.append("=" * 60)

    return "\n".join(lines)


def reset_cost_tracking():
    """Reset cost tracking (useful for per-query tracking)."""
    global _cost_tracker
    _cost_tracker = {
        "total_cost": 0.0,
        "calls": [],
        "by_model": {}
    }
