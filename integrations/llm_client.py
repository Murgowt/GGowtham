"""Thin OpenAI client for JSON-mode completions."""

from __future__ import annotations

import json
import logging

import httpx

from config import settings

logger = logging.getLogger(__name__)

OPENAI_CHAT_URL = "https://api.openai.com/v1/chat/completions"


class LLMUnavailableError(Exception):
    """LLM not configured — callers should use mock fixtures."""


def is_llm_configured() -> bool:
    return bool(settings.llm_enabled and settings.openai_api_key)


def complete_json(*, system: str, user: str, temperature: float = 0.2) -> dict:
    """Return parsed JSON object from chat completion."""
    if not is_llm_configured():
        raise LLMUnavailableError("LLM not configured")

    payload = {
        "model": settings.llm_model,
        "temperature": temperature,
        "response_format": {"type": "json_object"},
        "messages": [
            {"role": "system", "content": system},
            {"role": "user", "content": user},
        ],
    }
    headers = {
        "Authorization": f"Bearer {settings.openai_api_key}",
        "Content-Type": "application/json",
    }

    try:
        with httpx.Client(timeout=30.0) as client:
            resp = client.post(OPENAI_CHAT_URL, headers=headers, json=payload)
            resp.raise_for_status()
            data = resp.json()
    except httpx.HTTPError as exc:
        logger.exception("OpenAI request failed")
        raise RuntimeError(f"LLM request failed: {exc}") from exc

    content = data["choices"][0]["message"]["content"]
    try:
        return json.loads(content)
    except json.JSONDecodeError as exc:
        raise RuntimeError("LLM returned invalid JSON") from exc
