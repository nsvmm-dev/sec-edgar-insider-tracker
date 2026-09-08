"""Shared Claude client helpers.

Each agent gets an independent conversation (a fresh call with its own system
prompt), satisfying the spec's "run each agent in an isolated context" rule.
"""
from __future__ import annotations

import json
from functools import lru_cache
from typing import Any

import anthropic

from .config import settings


@lru_cache(maxsize=1)
def get_client() -> anthropic.Anthropic:
    # Credentials resolve from ANTHROPIC_API_KEY / ANTHROPIC_AUTH_TOKEN / CLI profile.
    return anthropic.Anthropic()


def _first_text(response: anthropic.types.Message) -> str:
    for block in response.content:
        if block.type == "text":
            return block.text
    return ""


def complete_text(system: str, user: str, *, max_tokens: int = 4000) -> str:
    resp = get_client().messages.create(
        model=settings.anthropic_model,
        max_tokens=max_tokens,
        system=system,
        messages=[{"role": "user", "content": user}],
    )
    if resp.stop_reason == "refusal":
        raise RuntimeError(f"Model refused the request: {resp.stop_details}")
    return _first_text(resp).strip()


def complete_json(
    system: str,
    user: str,
    schema: dict[str, Any],
    *,
    max_tokens: int = 4000,
) -> dict[str, Any]:
    resp = get_client().messages.create(
        model=settings.anthropic_model,
        max_tokens=max_tokens,
        system=system,
        messages=[{"role": "user", "content": user}],
        output_config={"format": {"type": "json_schema", "schema": schema}},
    )
    if resp.stop_reason == "refusal":
        raise RuntimeError(f"Model refused the request: {resp.stop_details}")
    return json.loads(_first_text(resp))
