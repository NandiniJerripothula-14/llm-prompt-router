"""OpenAI and local fallback client adapters used by router functions."""

from __future__ import annotations

import os
import re
from collections import Counter

from dotenv import load_dotenv
from openai import OpenAI

load_dotenv()


def has_real_openai_key(api_key: str | None = None) -> bool:
    """Return True only when a non-placeholder key is available."""
    resolved = (api_key or os.getenv("OPENAI_API_KEY") or "").strip()
    if not resolved:
        return False

    placeholder_prefixes = ("your_", "sk-your", "replace_me")
    if resolved.lower().startswith(placeholder_prefixes):
        return False
    return True


class OpenAIChatClient:
    def __init__(self, api_key: str | None = None) -> None:
        resolved_key = api_key or os.getenv("OPENAI_API_KEY")
        if not resolved_key:
            raise ValueError("OPENAI_API_KEY is required")
        self.client = OpenAI(api_key=resolved_key)

    def complete(
        self,
        *,
        model: str,
        system_prompt: str,
        user_message: str,
        temperature: float,
    ) -> str:
        response = self.client.chat.completions.create(
            model=model,
            temperature=temperature,
            messages=[
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": user_message},
            ],
        )
        return response.choices[0].message.content or ""


class LocalFallbackClient:
    """Offline heuristic client for local demo runs without API credentials."""

    def complete(
        self,
        *,
        model: str,
        system_prompt: str,
        user_message: str,
        temperature: float,
    ) -> str:
        _ = (model, temperature)
        if "classify" in system_prompt.lower() and "intent" in system_prompt.lower():
            return self._classify(user_message)
        return self._generate(system_prompt, user_message)

    def _classify(self, message: str) -> str:
        text = message.lower()

        code_terms = [
            "python",
            "javascript",
            "node",
            "api",
            "sql",
            "query",
            "bug",
            "function",
            "code",
            "error",
            "stack",
        ]
        data_terms = [
            "average",
            "median",
            "dataset",
            "data",
            "pivot",
            "chart",
            "distribution",
            "correlation",
            "anomaly",
            "table",
        ]
        writing_terms = [
            "paragraph",
            "rewrite",
            "writing",
            "tone",
            "grammar",
            "verbose",
            "awkward",
            "professional",
            "sentence",
        ]
        career_terms = [
            "career",
            "resume",
            "cover letter",
            "interview",
            "job",
            "promotion",
            "role",
            "salary",
        ]

        scores = Counter(
            {
                "code": self._count_hits(text, code_terms),
                "data": self._count_hits(text, data_terms),
                "writing": self._count_hits(text, writing_terms),
                "career": self._count_hits(text, career_terms),
            }
        )

        best_intent, best_score = scores.most_common(1)[0]
        second_best = scores.most_common(2)[1][1]

        if best_score == 0:
            return '{"intent":"unclear","confidence":0.2}'

        if best_score == second_best:
            return '{"intent":"unclear","confidence":0.4}'

        if best_score == 1:
            # Keep single-signal routing usable when threshold is 0.7.
            confidence = 0.78 if best_intent == "code" else 0.72
        else:
            confidence = 0.88
        return f'{{"intent":"{best_intent}","confidence":{confidence}}}'

    @staticmethod
    def _count_hits(text: str, terms: list[str]) -> int:
        hits = 0
        for term in terms:
            if re.search(r"\b" + re.escape(term) + r"\b", text):
                hits += 1
        return hits

    def _generate(self, system_prompt: str, message: str) -> str:
        prompt = system_prompt.lower()

        if "software engineer" in prompt:
            return (
                "Likely issue: syntax/logic mismatch. Start by reproducing the error, then add input validation and explicit "
                "exceptions around risky operations. If you share the exact snippet and traceback, I can provide a corrected, "
                "production-ready version with tests."
            )

        if "data analyst" in prompt:
            return (
                "Frame the question with summary statistics first (count, mean/median, spread), then inspect outliers and trend. "
                "A histogram plus a box plot would be a strong starting visualization."
            )

        if "writing coach" in prompt:
            return (
                "Your draft can improve by shortening long sentences, replacing vague words with specific nouns/verbs, and removing "
                "filler phrases. Keep one main idea per sentence and use direct voice for clarity."
            )

        if "career advisor" in prompt:
            return (
                "What role are you targeting and what is your current experience level? Once you share that, build a 30-day plan: "
                "update resume bullets with quantified impact, prepare 5 role-specific stories, and apply to a focused list weekly."
            )

        return f"I need a bit more context to help with: {message}"
