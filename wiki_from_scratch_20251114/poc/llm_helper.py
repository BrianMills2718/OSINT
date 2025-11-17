"""
Minimal LLM utility for Phase 1 entity extraction.
Standalone version - no dependencies on parent sam_gov project.
"""

import os
from typing import Any, Dict, List, Optional

import litellm


async def acompletion(
    model: str,
    messages: List[Dict[str, str]],
    response_format: Optional[Dict[str, Any]] = None,
    **kwargs
) -> Any:
    """
    Call LLM with async completion.

    Args:
        model: Model name (e.g., "gpt-5-mini")
        messages: List of message dicts with role and content
        response_format: Optional response format (e.g., JSON schema)
        **kwargs: Additional arguments for litellm

    Returns:
        LiteLLM completion response
    """
    # Remove max_tokens/max_output_tokens for gpt-5 models (breaks reasoning)
    if 'max_tokens' in kwargs:
        del kwargs['max_tokens']
    if 'max_output_tokens' in kwargs:
        del kwargs['max_output_tokens']

    # Call litellm
    response = await litellm.acompletion(
        model=model,
        messages=messages,
        response_format=response_format,
        **kwargs
    )

    return response
