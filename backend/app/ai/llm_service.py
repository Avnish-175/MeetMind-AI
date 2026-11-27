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
TIMESTAMP_TOLERANCE_SECONDS = 0.5
REQUIRED_ANALYSIS_KEYS = (
    "summary",
    "key_points",
    "decisions",
    "action_items",
    "deadlines",
    "unresolved_questions",
)
INSIGHT_LIST_MODELS: tuple[tuple[str, Any], ...] = (
    ("key_points", KeyPointItem),
    ("decisions", DecisionItem),
    ("action_items", ActionItem),
    ("deadlines", DeadlineItem),
    ("unresolved_questions", UnresolvedQuestionItem),
)


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
    match = re.search(r"```(?:json)?\s*([\s\S]*?)\s*```", cleaned, re.IGNORECASE)
    if match:
        cleaned = match.group(1).strip()
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
            "temperature": 0.1,
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
    except LLMServiceError:
        raise
    except Exception as exc:
        raise LLMServiceError(f"Failed to read Ollama response: {exc}") from exc


def validate_analysis_evidence(
    analysis_data: dict[str, Any],
    segments: list[dict[str, Any]],
) -> None:
    """Verify all cited transcript_segment_ids exist and timestamps match referenced segments."""
    segment_bounds: dict[int, tuple[float | None, float | None]] = {}
    for seg in segments:
        raw_id = seg.get("id")
        if raw_id is None:
            continue
        seg_id = int(raw_id)
        start = float(seg["start"]) if seg.get("start") is not None else None
        end = float(seg["end"]) if seg.get("end") is not None else None
        segment_bounds[seg_id] = (start, end)

    for field_name, _ in INSIGHT_LIST_MODELS:
        for item in analysis_data.get(field_name, []):
            seg_ids: list[int] = item.get("transcript_segment_ids", [])
            for seg_id in seg_ids:
                if seg_id not in segment_bounds:
                    raise OllamaOutputValidationError(
                        f"Insight in '{field_name}' references nonexistent transcript segment ID {seg_id}."
                    )

            start_time = item.get("start_time")
            end_time = item.get("end_time")
            if seg_ids and (start_time is not None or end_time is not None):
                ref_starts = [
                    segment_bounds[sid][0]
                    for sid in seg_ids
                    if segment_bounds[sid][0] is not None
                ]
                ref_ends = [
                    segment_bounds[sid][1]
                    for sid in seg_ids
                    if segment_bounds[sid][1] is not None
                ]
                if ref_starts and ref_ends:
                    min_start = min(ref_starts) - TIMESTAMP_TOLERANCE_SECONDS
                    max_end = max(ref_ends) + TIMESTAMP_TOLERANCE_SECONDS
                    if start_time is not None and (start_time < min_start or start_time > max_end):
                        raise OllamaOutputValidationError(
                            f"Insight start_time {start_time}s in '{field_name}' is inconsistent with referenced segments {seg_ids}."
                        )
                    if end_time is not None and (end_time < min_start or end_time > max_end):
                        raise OllamaOutputValidationError(
                            f"Insight end_time {end_time}s in '{field_name}' is inconsistent with referenced segments {seg_ids}."
                        )


def parse_and_validate_analysis_json(
    raw_json_str: str,
    segments: list[dict[str, Any]] | None = None,
) -> dict[str, Any]:
    """Strictly parse raw LLM JSON, validate all fields with Pydantic, and verify evidence."""
    cleaned = _clean_json_output(raw_json_str)
    try:
        data = json.loads(cleaned)
    except json.JSONDecodeError as exc:
        logger.error("Failed to parse JSON from LLM output: %s", exc)
        raise OllamaOutputValidationError(f"Invalid JSON received from LLM: {exc}") from exc

    if not isinstance(data, dict):
        raise OllamaOutputValidationError("LLM response must be a JSON object.")

    missing_keys = [key for key in REQUIRED_ANALYSIS_KEYS if key not in data]
    if missing_keys:
        raise OllamaOutputValidationError(
            f"LLM response is missing required fields: {', '.join(missing_keys)}."
        )

    raw_summary = data["summary"]
    if raw_summary is not None and not isinstance(raw_summary, str):
        raise OllamaOutputValidationError("LLM 'summary' field must be a string or null.")
    summary = raw_summary.strip() or None if isinstance(raw_summary, str) else None

    validated_result: dict[str, Any] = {"summary": summary}

    for field_name, model_cls in INSIGHT_LIST_MODELS:
        raw_list = data[field_name]
        if not isinstance(raw_list, list):
            raise OllamaOutputValidationError(
                f"LLM '{field_name}' field must be a JSON array."
            )
        validated_items: list[dict[str, Any]] = []
        for idx, item in enumerate(raw_list):
            if not isinstance(item, dict):
                raise OllamaOutputValidationError(
                    f"Item {idx} in '{field_name}' must be a JSON object."
                )
            try:
                validated_obj = model_cls.model_validate(item)
                validated_items.append(validated_obj.model_dump())
            except ValidationError as exc:
                raise OllamaOutputValidationError(
                    f"Invalid {model_cls.__name__} at index {idx} in '{field_name}': {exc}"
                ) from exc
        validated_result[field_name] = validated_items

    if segments is not None:
        validate_analysis_evidence(validated_result, segments)

    return validated_result


def parse_summary_synthesis_json(raw_json_str: str) -> str | None:
    """Parse and validate the synthesized summary JSON object."""
    cleaned = _clean_json_output(raw_json_str)
    try:
        data = json.loads(cleaned)
    except json.JSONDecodeError as exc:
        raise OllamaOutputValidationError(f"Invalid summary JSON received from LLM: {exc}") from exc

    if not isinstance(data, dict) or "summary" not in data:
        raise OllamaOutputValidationError("Synthesized summary response must contain 'summary'.")

    raw_summary = data["summary"]
    if raw_summary is not None and not isinstance(raw_summary, str):
        raise OllamaOutputValidationError("Synthesized 'summary' must be a string or null.")
    return raw_summary.strip() or None if isinstance(raw_summary, str) else None
