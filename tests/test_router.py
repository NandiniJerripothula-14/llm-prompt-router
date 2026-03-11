import json
from pathlib import Path

from router import classify_intent, parse_manual_override, process_message, route_and_respond


class FakeLLMClient:
    def __init__(self, outputs):
        self.outputs = list(outputs)
        self.calls = []

    def complete(self, *, model, system_prompt, user_message, temperature):
        self.calls.append(
            {
                "model": model,
                "system_prompt": system_prompt,
                "user_message": user_message,
                "temperature": temperature,
            }
        )
        if not self.outputs:
            return ""
        return self.outputs.pop(0)


def test_classify_intent_returns_structured_json():
    client = FakeLLMClient(['{"intent":"code","confidence":0.92}'])
    result = classify_intent("fix python bug", client)
    assert result["intent"] == "code"
    assert result["confidence"] == 0.92


def test_classify_intent_handles_malformed_json():
    client = FakeLLMClient(["not-a-json-response"])
    result = classify_intent("hello", client)
    assert result == {"intent": "unclear", "confidence": 0.0}


def test_unclear_routes_to_clarification_question():
    client = FakeLLMClient([])
    result = route_and_respond("help me", {"intent": "unclear", "confidence": 0.0}, client)
    assert result.endswith("?")


def test_process_message_logs_required_fields(tmp_path: Path):
    log_file = tmp_path / "route_log.jsonl"
    client = FakeLLMClient([
        '{"intent":"writing","confidence":0.88}',
        "Focus on tightening long sentences and reducing filler words.",
    ])

    result = process_message("My boss says my writing is too verbose.", client, log_path=log_file)

    assert result["intent"] == "writing"
    assert log_file.exists()

    entries = log_file.read_text(encoding="utf-8").strip().splitlines()
    assert len(entries) == 1

    record = json.loads(entries[0])
    assert "intent" in record
    assert "confidence" in record
    assert "user_message" in record
    assert "final_response" in record


def test_manual_override_routes_directly_without_classifier_call():
    client = FakeLLMClient(["Use try/except around file access."])
    result = process_message("@code handle file read errors", client)

    assert result["intent"] == "code"
    assert result["confidence"] == 1.0
    assert len(client.calls) == 1


def test_confidence_threshold_falls_back_to_unclear():
    client = FakeLLMClient(['{"intent":"career","confidence":0.4}'])
    result = classify_intent("career question", client, confidence_threshold=0.7)
    assert result == {"intent": "unclear", "confidence": 0.0}


def test_sample_messages_do_not_crash(tmp_path: Path):
    sample_messages = [
        "how do i sort a list of objects in python?",
        "explain this sql query for me",
        "This paragraph sounds awkward, can you help me fix it?",
        "I'm preparing for a job interview, any tips?",
        "what's the average of these numbers: 12, 45, 23, 67, 34",
        "Help me make this better.",
        "I need to write a function that takes a user id and returns their profile, but also i need help with my resume.",
        "hey",
        "Can you write me a poem about clouds?",
        "Rewrite this sentence to be more professional.",
        "I'm not sure what to do with my career.",
        "what is a pivot table",
        "fxi thsi bug pls: for i in range(10) print(i)",
        "How do I structure a cover letter?",
        "My boss says my writing is too verbose.",
    ]

    # Two outputs are consumed per message in this setup:
    # one classifier JSON, then one generated response.
    outputs = []
    for _ in sample_messages:
        outputs.append('{"intent":"unclear","confidence":0.2}')
        outputs.append("Could you clarify what kind of help you want?")

    client = FakeLLMClient(outputs)
    log_file = tmp_path / "route_log.jsonl"

    for message in sample_messages:
        result = process_message(message, client, log_path=log_file)
        assert "intent" in result
        assert "confidence" in result
        assert "final_response" in result

    assert log_file.exists()
    assert len(log_file.read_text(encoding="utf-8").strip().splitlines()) == len(sample_messages)


def test_parse_manual_override():
    intent, cleaned = parse_manual_override("@writing this sounds rough")
    assert intent == "writing"
    assert cleaned == "this sounds rough"
