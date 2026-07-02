import requests
import json
import re

OLLAMA_URL = "http://localhost:11434/api/generate"
OLLAMA_MODEL = "llama3.1:8b"


def aot_to_limo_command(intent: dict) -> dict:
    prompt = f"""You are a controller for AgileX LIMO robot.
Convert the intent into a LIMO movement command.

Available commands:
- "go straight" : move forward
- "turn left"   : rotate left
- "turn right"  : rotate right
- "move back"   : move backward
- "stop"        : stop all movement

Example A:
Intent: Action=Move, Object=desk, Target=chair
Output: {{"command": "go straight", "speed": 0.4, "duration": 3}}

Example B:
Intent: Action=Turn, Object=Robot, Target=left
Output: {{"command": "turn left", "speed": 0.3, "duration": 2}}

Example C:
Intent: Action=Stop, Object=Robot, Target=Stop
Output: {{"command": "stop", "speed": 0.0, "duration": 0}}

Example D:
Intent: Action=Go, Object=door, Target=forward
Output: {{"command": "go straight", "speed": 0.5, "duration": 5}}

Now convert:
Intent: Action={intent.get("Action", "")}, Object={intent.get("ExpectationObject", "")}, Target={intent.get("ExpectationTarget", "")}
Output:"""

    try:
        res = requests.post(OLLAMA_URL, json={
            "model": OLLAMA_MODEL,
            "prompt": prompt,
            "stream": False,
            "format": "json"
        }, timeout=30)

        raw = res.json().get("response", "{}")
        parsed = json.loads(raw)
        print(f"[Llama] raw: {raw}")

    except Exception as e:
        print(f"[Llama] 실패: {e}")
        parsed = {}

    duration_raw = parsed.get("duration")
    speed_raw = parsed.get("speed")

    return {
        "command":  parsed.get("command", "stop"),
        "speed":    float(speed_raw) if speed_raw is not None else 0.3,
        "duration": float(duration_raw) if duration_raw is not None else 2.0
    }
