"""Simple CLI for the LLM-powered prompt router."""

from __future__ import annotations

import os

from llm_client import LocalFallbackClient, OpenAIChatClient, has_real_openai_key
from router import process_message


def main() -> None:
    classifier_model = os.getenv("CLASSIFIER_MODEL", "gpt-4o-mini")
    generator_model = os.getenv("GENERATOR_MODEL", "gpt-4.1-mini")

    threshold_env = os.getenv("CONFIDENCE_THRESHOLD")
    confidence_threshold = float(threshold_env) if threshold_env else None

    if has_real_openai_key():
        client = OpenAIChatClient()
        run_mode = "openai"
    else:
        client = LocalFallbackClient()
        run_mode = "local-fallback"

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
            else:
                print("Local fallback mode error. Please retry.\n")
            continue

        print(f"intent={result['intent']} confidence={result['confidence']:.2f}")
        print(result["final_response"])
        print()


if __name__ == "__main__":
    main()
