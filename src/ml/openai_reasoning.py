"""
Optional OpenAI-powered reasoning enhancer.
Uses the Responses API only when configured.
"""
from __future__ import annotations

import json

import requests

from config.settings import (
    OPENAI_API_KEY,
    OPENAI_ENHANCE_REASONING,
    OPENAI_MODEL,
    OPENAI_REASONING_EFFORT,
)
from src.api.logger import setup_logger

logger = setup_logger(__name__, "openai_reasoning.log")


def enhance_reasoning_with_openai(stock_payload):
    if not OPENAI_ENHANCE_REASONING or not OPENAI_API_KEY:
        return None

    try:
        response = requests.post(
            "https://api.openai.com/v1/responses",
            headers={
                "Authorization": f"Bearer {OPENAI_API_KEY}",
                "Content-Type": "application/json",
            },
            json={
                "model": OPENAI_MODEL,
                "reasoning": {"effort": OPENAI_REASONING_EFFORT},
                "input": [
                    {
                        "role": "system",
                        "content": (
                            "You are a stock-analysis explainer. Do not promise returns. "
                            "Explain why a stock ranks where it does using the provided signals."
                        ),
                    },
                    {
                        "role": "user",
                        "content": json.dumps(stock_payload),
                    },
                ],
            },
            timeout=20,
        )
        response.raise_for_status()
        payload = response.json()
        output_text = payload.get("output_text", "").strip()
        if output_text:
            return output_text
    except Exception as exc:
        logger.warning("OpenAI reasoning enhancement failed: %s", exc)
    return None
