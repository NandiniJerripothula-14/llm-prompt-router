"""Simple CLI for the LLM-powered prompt router."""

from __future__ import annotations

import os

from llm_client import (
    GroqChatClient,
    LocalFallbackClient,
    OpenAIChatClient,
    has_real_groq_key,
    has_real_openai_key,
)
from router import process_message


def main() -> None:
    classifier_model = os.getenv("CLASSIFIER_MODEL")
    generator_model = os.getenv("GENERATOR_MODEL")
    provider = os.getenv("LLM_PROVIDER", "auto").strip().lower()

    threshold_env = os.getenv("CONFIDENCE_THRESHOLD")
    confidence_threshold = float(threshold_env) if threshold_env else None

    if provider == "openai":
        if not has_real_openai_key():
            raise RuntimeError("LLM_PROVIDER=openai but OPENAI_API_KEY is missing or invalid")
        client = OpenAIChatClient()
        run_mode = "openai"
        classifier_model = classifier_model or "gpt-4o-mini"
        generator_model = generator_model or "gpt-4.1-mini"
    elif provider == "groq":
        if not has_real_groq_key():
            raise RuntimeError("LLM_PROVIDER=groq but GROQ_API_KEY is missing or invalid")
        client = GroqChatClient()
        run_mode = "groq"
        classifier_model = classifier_model or os.getenv("GROQ_CLASSIFIER_MODEL", "llama-3.1-8b-instant")
        generator_model = generator_model or os.getenv("GROQ_GENERATOR_MODEL", "llama-3.1-8b-instant")
    elif provider == "local":
        client = LocalFallbackClient()
        run_mode = "local-fallback"
        classifier_model = classifier_model or "gpt-4o-mini"
        generator_model = generator_model or "gpt-4.1-mini"
    elif has_real_openai_key():
        client = OpenAIChatClient()
        run_mode = "openai"
        classifier_model = classifier_model or "gpt-4o-mini"
        generator_model = generator_model or "gpt-4.1-mini"
    elif has_real_groq_key():
        client = GroqChatClient()
        run_mode = "groq"
        classifier_model = classifier_model or os.getenv("GROQ_CLASSIFIER_MODEL", "llama-3.1-8b-instant")
        generator_model = generator_model or os.getenv("GROQ_GENERATOR_MODEL", "llama-3.1-8b-instant")
    else:
        client = LocalFallbackClient()
        run_mode = "local-fallback"
        classifier_model = classifier_model or "gpt-4o-mini"
        generator_model = generator_model or "gpt-4.1-mini"

    print("LLM Prompt Router CLI")
    print(f"Mode: {run_mode}")
    print("Type a message, or 'exit' to quit.\n")

    while True:
        message = input("> ").strip()
        if message.lower() in {"exit", "quit"}:
            print("Goodbye.")
            break
        if not message:
            continue

        try:
            result = process_message(
                message,
                client,
                classifier_model=classifier_model,
                generator_model=generator_model,
                confidence_threshold=confidence_threshold,
                log_path="route_log.jsonl",
            )
        except Exception as exc:
            print(f"Request failed: {exc}")
            if run_mode == "openai":
                print("Check your OpenAI quota/billing, then try again.\n")
            elif run_mode == "groq":
                print("Check your Groq API key, model name, and rate limits, then try again.\n")
            else:
                print("Local fallback mode error. Please retry.\n")
            continue

        print(f"intent={result['intent']} confidence={result['confidence']:.2f}")
        print(result["final_response"])
        print()


if __name__ == "__main__":
    main()
