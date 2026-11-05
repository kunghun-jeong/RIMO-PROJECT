# IETF-127: natural language -> intent JSON (Manager side)

Turns a natural-language command into the intent JSON handed to the Edge Agent,
using few-shot prompting on a local Ollama model.

```json
{"intent": {
  "intent_id": "move_001",
  "action": "move",
  "target_location": {"x": 30.0, "y": 40.0, "frame_id": "map"},
  "constraints": {"safety_margin_m": 0.45, "speed_mps": 0.2},
  "report": true
}}
```

## Run

```bash
python run.py "x:30 y:40 좌표까지 속도 0.2로 이동 후 보고해줘"
python -m unittest test_intent
```

Results are saved to `outputs/` (git-ignored): one JSON per request plus `log.jsonl`
(input, `source` = `llm` or `rules`, corrections).

## How it works

- `intent/extract.py` reads x, y (and speed / safety margin if stated) from the text.
- `intent/prompt.py` + `intent/intent_llm.py` ask the LLM for the JSON (Ollama, `config.py`).
- `intent/schema.py` validates the output and overrides numbers with the values from the text,
  so a wrong LLM number never reaches the robot. If the LLM is unreachable the result is built
  from the text alone and marked `source: rules`.
- `intent/sink.py` is where results go. Only a local-file sink exists; HTTP/A2A delivery is not implemented yet.

Requires `requests`. Default model: `llama3.1:8b` (`intent/config.py`).
