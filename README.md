# LLM-Powered Prompt Router

This project implements a two-step LLM routing workflow:
1. `classify_intent(message)` performs lightweight intent classification.
2. `route_and_respond(message, intent)` routes to a specialized expert persona.

Supported intents:
- `code`
- `data`
- `writing`
- `career`
- `unclear`

## Features

- Four distinct expert personas stored in a separate config file (`prompts.py`).
- Structured classifier output with JSON parsing and safe fallback.
- Graceful handling of malformed classifier responses.
- Clarifying-question behavior for `unclear` intent.
- Per-request JSONL logging to `route_log.jsonl`.
- Optional confidence-threshold fallback to `unclear`.
- Optional manual override with `@intent` prefix (for example `@code`).
- Unit tests covering core and edge-case behavior.

## Project Structure

- `prompts.py`: classifier and expert system prompts
- `router.py`: `classify_intent`, `route_and_respond`, logging, orchestration
- `llm_client.py`: OpenAI client adapter
- `main.py`: CLI entry point
- `tests/test_router.py`: unit tests (including provided sample messages)
- `route_log.jsonl`: runtime log file (created on first run)

## Setup

```bash
python -m venv .venv
.venv\\Scripts\\activate
pip install -r requirements.txt
copy .env.example .env
```

Set your OpenAI key in `.env`:

```env
OPENAI_API_KEY=your_openai_api_key_here
```

## Secure API Key Handling

- Never hardcode API keys in source files.
- Keep your real key in `.env` or a system environment variable.
- `.env` is excluded by `.gitignore` and should never be committed.

Python loading in this project is already configured in `llm_client.py`:

```python
from dotenv import load_dotenv
import os

load_dotenv()
api_key = os.getenv("OPENAI_API_KEY")
```

Set key in current PowerShell session:

```powershell
$env:OPENAI_API_KEY="your_real_key_here"
python main.py
```

Persist key on Windows:

```powershell
setx OPENAI_API_KEY "your_real_key_here"
```

After running `setx`, open a new terminal for it to take effect.

## Run CLI

```bash
python main.py
```

If no real `OPENAI_API_KEY` is configured, the CLI automatically runs in a local fallback mode so you can test routing without storing any API key.

## Docker Compose

`docker-compose.yml` passes environment variables into the container.

PowerShell example:

```powershell
$env:OPENAI_API_KEY="your_real_key_here"
docker compose up --build
```

If your Docker uses legacy command naming, use `docker-compose up --build`.

Example input:

```text
how do i sort a list of objects in python?
```

CLI output shows:

- detected intent
- confidence score
- final response

## Run Tests

```bash
pytest -q
```

## Requirement Mapping

1. At least four prompts in configurable structure:

- Implemented in `prompts.py` as `EXPERT_PROMPTS` keyed by intent.

1. `classify_intent` with LLM call and JSON schema:

- Implemented in `router.py` (`classify_intent`).
- Returns `{"intent": "string", "confidence": float}`.

1. `route_and_respond` does second LLM call:

- Implemented in `router.py` (`route_and_respond`).

1. `unclear` requests ask a clarifying question:

- Implemented via `CLARIFICATION_QUESTION` in `prompts.py` and used in routing.

1. JSONL logging with required keys:

- Implemented in `append_route_log` in `router.py` writing to `route_log.jsonl`.

1. Malformed classifier output fallback:

- Implemented in `_safe_parse_classifier_output` returning `{"intent":"unclear","confidence":0.0}`.

## Notes

- Models are configurable via environment variables:
  - `CLASSIFIER_MODEL` (default `gpt-4o-mini`)
  - `GENERATOR_MODEL` (default `gpt-4.1-mini`)
- Optional confidence threshold (`CONFIDENCE_THRESHOLD`) can force low-confidence predictions to `unclear`.

## What To Commit

Include:

- `main.py`
- `router.py`
- `prompts.py`
- `llm_client.py`
- `Dockerfile`
- `docker-compose.yml`
- `README.md`
- `.env.example`

Do not include:

- `.env`
- any real API keys
