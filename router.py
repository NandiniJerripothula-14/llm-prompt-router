"""Core logic for intent classification, routing, and response generation."""

from __future__ import annotations

import json
from datetime import datetime, timezone
from pathlib import Path
from typing import Protocol

from prompts import CLARIFICATION_QUESTION, CLASSIFIER_SYSTEM_PROMPT, EXPERT_PROMPTS, SUPPORTED_INTENTS


DEFAULT_INTENT = {"intent": "unclear", "confidence": 0.0}


class LLMClient(Protocol):
    """Small interface to keep router logic testable and provider-agnostic."""

    def complete(
        self,
        *,
        model: str,
        system_prompt: str,
        user_message: str,
        temperature: float,
    ) -> str:
        ...


def _clean_json_text(raw_text: str) -> str:
    text = raw_text.strip()
    if text.startswith("```"):
        lines = text.splitlines()
        if len(lines) >= 3:
            text = "\n".join(lines[1:-1]).strip()
    return text


def _safe_parse_classifier_output(raw_text: str) -> dict[str, float | str]:
    try:
        parsed = json.loads(_clean_json_text(raw_text))
        if not isinstance(parsed, dict):
            return DEFAULT_INTENT.copy()

        intent = str(parsed.get("intent", "unclear")).strip().lower()
        if intent not in SUPPORTED_INTENTS:
            intent = "unclear"

        confidence_raw = parsed.get("confidence", 0.0)
        confidence = float(confidence_raw)
        if confidence < 0.0 or confidence > 1.0:
            confidence = max(0.0, min(1.0, confidence))

        return {"intent": intent, "confidence": confidence}
    except (TypeError, ValueError, json.JSONDecodeError):
        return DEFAULT_INTENT.copy()


def _apply_confidence_threshold(intent_obj: dict[str, float | str], threshold: float | None) -> dict[str, float | str]:
    if threshold is None:
        return intent_obj

    confidence = float(intent_obj.get("confidence", 0.0))
    if confidence < threshold:
        return DEFAULT_INTENT.copy()
    return intent_obj


def parse_manual_override(message: str) -> tuple[str | None, str]:
    stripped = message.strip()
    for intent in SUPPORTED_INTENTS:
        prefix = f"@{intent}"
        if stripped.lower().startswith(prefix):
            remainder = stripped[len(prefix) :].strip()
            return intent, remainder or stripped
    return None, message


def classify_intent(
    message: str,
    llm_client: LLMClient,
    *,
    model: str = "gpt-4o-mini",
    confidence_threshold: float | None = None,
) -> dict[str, float | str]:
    """Classify user message into {intent, confidence} with safe fallback."""
    raw_output = llm_client.complete(
        model=model,
        system_prompt=CLASSIFIER_SYSTEM_PROMPT,
        user_message=message,
        temperature=0.0,
    )
    parsed = _safe_parse_classifier_output(raw_output)
    return _apply_confidence_threshold(parsed, confidence_threshold)


def route_and_respond(
    message: str,
    intent_obj: dict[str, float | str],
    llm_client: LLMClient,
    *,
    model: str = "gpt-4.1-mini",
) -> str:
    """Route the message to specialized persona or ask a clarifying question."""
    intent = str(intent_obj.get("intent", "unclear")).lower().strip()
    if intent == "unclear":
        return CLARIFICATION_QUESTION

    system_prompt = EXPERT_PROMPTS.get(intent)
    if not system_prompt:
        return CLARIFICATION_QUESTION

    return llm_client.complete(
        model=model,
        system_prompt=system_prompt,
        user_message=message,
        temperature=0.3,
    ).strip()


def append_route_log(
    *,
    log_path: str | Path,
    intent: str,
    confidence: float,
    user_message: str,
    final_response: str,
) -> None:
    payload = {
        "timestamp": datetime.now(timezone.utc).isoformat(),
        "intent": intent,
        "confidence": confidence,
        "user_message": user_message,
        "final_response": final_response,
    }
    target = Path(log_path)
    target.parent.mkdir(parents=True, exist_ok=True)
    with target.open("a", encoding="utf-8") as file:
        file.write(json.dumps(payload, ensure_ascii=True) + "\n")


def process_message(
    message: str,
    llm_client: LLMClient,
    *,
    classifier_model: str = "gpt-4o-mini",
    generator_model: str = "gpt-4.1-mini",
    confidence_threshold: float | None = None,
    log_path: str | Path = "route_log.jsonl",
) -> dict[str, float | str]:
    """End-to-end router flow used by API or CLI callers."""
    override_intent, cleaned_message = parse_manual_override(message)

    if override_intent and override_intent != "unclear":
        intent_obj = {"intent": override_intent, "confidence": 1.0}
    else:
        intent_obj = classify_intent(
            cleaned_message,
            llm_client,
            model=classifier_model,
            confidence_threshold=confidence_threshold,
        )

    final_response = route_and_respond(
        cleaned_message,
        intent_obj,
        llm_client,
        model=generator_model,
    )

    append_route_log(
        log_path=log_path,
        intent=str(intent_obj["intent"]),
        confidence=float(intent_obj["confidence"]),
        user_message=message,
        final_response=final_response,
    )

    return {
        "intent": str(intent_obj["intent"]),
        "confidence": float(intent_obj["confidence"]),
        "final_response": final_response,
    }
