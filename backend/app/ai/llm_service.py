import json
import logging
import re
from typing import Any

import httpx
from pydantic import ValidationError

from app.core.config import settings
from app.schemas.meeting_analysis import (
    ActionItem,
    DeadlineItem,
    DecisionItem,
    KeyPointItem,
    UnresolvedQuestionItem,
)

logger = logging.getLogger(__name__)

DEFAULT_OLLAMA_TIMEOUT = 120.0


class LLMServiceError(Exception):
    """Base exception for local LLM communication and inference errors."""


class OllamaConnectionError(LLMServiceError):
    """Raised when Ollama daemon is unreachable."""


class OllamaModelNotFoundError(LLMServiceError):
    """Raised when the specified model is not pulled or found in Ollama."""


class OllamaOutputValidationError(LLMServiceError):
    """Raised when the model output cannot be parsed or validated against schemas."""


def _clean_json_output(raw_output: str) -> str:
    """Strip markdown code fence wrappers or trailing commentary to extract JSON."""
    cleaned = raw_output.strip()
    # Check for markdown code blocks
    match = re.search(r"```(?:json)?\s*([\s\S]*?)\s*```", cleaned, re.IGNORECASE)
    if match:
        cleaned = match.group(1).strip()
    # If starting/ending brackets exist, isolate the JSON object
    first_brace = cleaned.find("{")
    last_brace = cleaned.rfind("}")
    if first_brace != -1 and last_brace != -1 and last_brace > first_brace:
        cleaned = cleaned[first_brace : last_brace + 1]
    return cleaned


async def generate_ollama_chat_completion(
    system_prompt: str,
    user_prompt: str,
    model: str | None = None,
    base_url: str | None = None,
    timeout_seconds: float = DEFAULT_OLLAMA_TIMEOUT,
) -> str:
    """Send an asynchronous chat request to the local Ollama instance."""
    resolved_model = (model or settings.OLLAMA_MODEL).strip()
    resolved_base_url = (base_url or settings.OLLAMA_BASE_URL).rstrip("/")

    endpoint = f"{resolved_base_url}/api/chat"
    payload = {
        "model": resolved_model,
        "messages": [
            {"role": "system", "content": system_prompt},
            {"role": "user", "content": user_prompt},
        ],
        "stream": False,
        "format": "json",
        "options": {
            "temperature": 0.1,  # Low temperature to minimize hallucinations
        },
    }

    try:
        async with httpx.AsyncClient(timeout=timeout_seconds) as client:
            logger.info("Calling local Ollama endpoint '%s' with model '%s'...", endpoint, resolved_model)
            response = await client.post(endpoint, json=payload)
    except httpx.ConnectError as exc:
        logger.error("Could not connect to Ollama at '%s': %s", endpoint, exc)
        raise OllamaConnectionError(
            f"Could not connect to local Ollama service at {resolved_base_url}. Ensure Ollama is running."
        ) from exc
    except httpx.TimeoutException as exc:
        logger.error("Ollama inference timed out after %ds at '%s'", timeout_seconds, endpoint)
        raise LLMServiceError(f"Ollama inference timed out after {timeout_seconds} seconds.") from exc
    except httpx.HTTPError as exc:
        logger.error("HTTP error during Ollama request: %s", exc)
        raise LLMServiceError("Failed to communicate with local Ollama service.") from exc

    if response.status_code == 404:
        raise OllamaModelNotFoundError(
            f"Ollama model '{resolved_model}' was not found. Please pull the model using 'ollama pull {resolved_model}'."
        )
    if response.status_code != 200:
        raise LLMServiceError(
            f"Ollama returned error status code {response.status_code}: {response.text[:200]}"
        )

    try:
        response_data = response.json()
        message = response_data.get("message", {})
        content = message.get("content", "")
        if not content:
            raise LLMServiceError("Ollama returned an empty response content.")
        return content
    except Exception as exc:
        raise LLMServiceError(f"Failed to read Ollama response: {exc}") from exc


def parse_and_validate_analysis_json(raw_json_str: str) -> dict[str, Any]:
    """Parse raw LLM output, coerce items safely into Pydantic models, and validate structure."""
    cleaned = _clean_json_output(raw_json_str)
    try:
        data = json.loads(cleaned)
    except json.JSONDecodeError as exc:
        logger.error("Failed to parse JSON from LLM output: %s\nRaw output:\n%s", exc, raw_json_str[:500])
        raise OllamaOutputValidationError(f"Invalid JSON received from LLM: {exc}") from exc

    if not isinstance(data, dict):
        raise OllamaOutputValidationError("LLM response must be a JSON object.")

    summary = data.get("summary")
    if summary is not None:
        summary = str(summary).strip() or None

    def _validate_items(raw_list: Any, model_cls: Any) -> list[dict[str, Any]]:
        if not isinstance(raw_list, list):
            return []
        validated: list[dict[str, Any]] = []
        for item in raw_list:
            if not isinstance(item, dict):
                continue
            try:
                # If text is empty or missing, skip rather than failing entire analysis
                text = str(item.get("text", "")).strip()
                if not text:
                    continue
                item["text"] = text
                validated_obj = model_cls(**item)
                validated.append(validated_obj.model_dump())
            except ValidationError as err:
                logger.warning("Skipping malformed %s item from LLM: %s", model_cls.__name__, err)
                continue
        return validated

    key_points = _validate_items(data.get("key_points"), KeyPointItem)
    decisions = _validate_items(data.get("decisions"), DecisionItem)
    action_items = _validate_items(data.get("action_items"), ActionItem)
    deadlines = _validate_items(data.get("deadlines"), DeadlineItem)
    unresolved_questions = _validate_items(data.get("unresolved_questions"), UnresolvedQuestionItem)

    return {
        "summary": summary,
        "key_points": key_points,
        "decisions": decisions,
        "action_items": action_items,
        "deadlines": deadlines,
        "unresolved_questions": unresolved_questions,
    }
