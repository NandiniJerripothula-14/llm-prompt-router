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

## Demo Run Order

Use this exact sequence during your video demo:

1. Run tests and show they pass:

```powershell
pytest -q
```

1. Set local provider mode:

```powershell
$env:LLM_PROVIDER="local"
```

1. Start the app and test 5 prompts:

```powershell
python main.py
```

Suggested 5 prompts:

1. `how do i sort a list of objects in python?`
1. `what is a pivot table and when should i use it?`
1. `My boss says my writing is too verbose.`
1. `I'm preparing for a job interview, any tips?`
1. `hey`

1. Show latest logs:

```powershell
Get-Content route_log.jsonl -Tail 8
```

## Demo Test Prompts

Use these prompts during a live demo to show each route:

1. `how do i sort a list of objects in python?`
1. `fxi thsi bug pls: for i in range(10) print(i)`
1. `explain this sql query: select * from users where created_at > now() - interval '7 day'`
1. `what's the average of these numbers: 12, 45, 23, 67, 34`
1. `what is a pivot table and when should i use it?`
1. `This paragraph sounds awkward, can you help me fix it?`
1. `My boss says my writing is too verbose.`
1. `Rewrite this sentence to be more professional: "i need this done asap"`
1. `I'm preparing for a job interview, any tips?`
1. `How do I structure a cover letter?`
1. `I'm not sure what to do with my career.`
1. `Help me make this better.`
1. `hey`
1. `Can you write me a poem about clouds?`
1. `I need to write a function that takes a user id and returns their profile, but also i need help with my resume.`

Short demo set (fast 5-prompt run):

1. `how do i sort a list of objects in python?`
1. `what is a pivot table and when should i use it?`
1. `My boss says my writing is too verbose.`
1. `I'm preparing for a job interview, any tips?`
1. `hey`

Show latest route logs after the run:

```powershell
Get-Content route_log.jsonl -Tail 10
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
