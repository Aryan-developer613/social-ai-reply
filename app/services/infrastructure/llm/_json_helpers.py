"""Shared JSON parsing utilities for LLM responses."""

from __future__ import annotations

import json
import re


def parse_json_payload(text: str) -> dict | list | None:
    """Parse JSON from LLM response text, handling markdown code blocks."""
    cleaned = text.strip()
    cleaned = re.sub(r"^```(?:json)?\s*", "", cleaned, flags=re.IGNORECASE)
    cleaned = re.sub(r"\s*```$", "", cleaned)

    decoder = json.JSONDecoder()
    first_brace = cleaned.find("{")
    first_bracket = cleaned.find("[")

    candidates = [cleaned]
    if first_brace != -1 and first_bracket != -1:
        if first_brace < first_bracket:
            candidates.extend([cleaned[first_brace:], cleaned[first_bracket:]])
        else:
            candidates.extend([cleaned[first_bracket:], cleaned[first_brace:]])
    elif first_brace != -1:
        candidates.append(cleaned[first_brace:])
    elif first_bracket != -1:
        candidates.append(cleaned[first_bracket:])
    for candidate in candidates:
        candidate = candidate.strip()
        if not candidate:
            continue
        try:
            payload, _index = decoder.raw_decode(candidate)
            return payload
        except json.JSONDecodeError:
            continue
    return None
