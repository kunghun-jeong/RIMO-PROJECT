import requests
import json
import re

OLLAMA_URL = "http://localhost:11434/api/generate"
OLLAMA_MODEL = "llama3.1:8b"

LIMO_COMMANDS = ["go straight", "turn left", "turn right", "move back", "stop"]


def natural_to_limo_command(text: str) -> dict:
    prompt = f"""You are a controller for AgileX LIMO robot.
The user gives a natural language command. Select the best matching command and return JSON.

Available commands:
- "go straight" : move forward
- "turn left"   : rotate left
- "turn right"  : rotate right
- "move back"   : move backward
- "stop"        : stop all movement

Rules:
- command must be exactly one of the 5 options above
- speed: 0.1 to 1.0 (default 0.5)
- duration: seconds to run (default 2.0)

Examples:
Input: "앞으로 가줘"
Output: {{"command": "go straight", "speed": 0.5, "duration": 2.0}}

Input: "왼쪽으로 돌아"
Output: {{"command": "turn left", "speed": 0.4, "duration": 2.0}}

Input: "멈춰"
Output: {{"command": "stop", "speed": 0.0, "duration": 0.0}}

Input: "go forward for 3 seconds"
Output: {{"command": "go straight", "speed": 0.5, "duration": 3.0}}

Now convert:
Input: "{text}"
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
        print(f"[Llama] natural input='{text}' → raw: {raw}")

    except Exception as e:
        print(f"[Llama] 실패: {e}")
        parsed = {}

    command = parsed.get("command", "stop")
    if command not in LIMO_COMMANDS:
        command = "stop"

    duration_raw = parsed.get("duration")
    speed_raw = parsed.get("speed")

    return {
        "command":  command,
        "speed":    float(speed_raw) if speed_raw is not None else 0.5,
        "duration": float(duration_raw) if duration_raw is not None else 2.0,
    }


def natural_to_limo_sequence(text: str) -> list:
    prompt = f"""You are a controller for AgileX LIMO robot.
The user gives a natural language command that may contain multiple sequential actions.
Parse it into an ordered list of steps and return JSON.

Available commands:
- "go straight" : move forward
- "turn left"   : rotate left
- "turn right"  : rotate right
- "move back"   : move backward
- "stop"        : stop all movement

Rules:
- Each command must be exactly one of the 5 options above
- speed: 0.1 to 1.0 (default 0.5)
- duration in seconds. "one block"=3.0s, "two blocks"=6.0s, "three blocks"=9.0s
- Return a JSON object with a "steps" key containing the array

Examples:
Input: "go forward two blocks and turn left"
Output: {{"steps": [{{"command": "go straight", "speed": 0.5, "duration": 6.0}}, {{"command": "turn left", "speed": 0.4, "duration": 2.0}}]}}

Input: "앞으로 두 블록 가고 오른쪽으로 돌아"
Output: {{"steps": [{{"command": "go straight", "speed": 0.5, "duration": 6.0}}, {{"command": "turn right", "speed": 0.4, "duration": 2.0}}]}}

Input: "move forward, turn left, then go straight for 3 seconds"
Output: {{"steps": [{{"command": "go straight", "speed": 0.5, "duration": 3.0}}, {{"command": "turn left", "speed": 0.4, "duration": 2.0}}, {{"command": "go straight", "speed": 0.5, "duration": 3.0}}]}}

Input: "멈춰"
Output: {{"steps": [{{"command": "stop", "speed": 0.0, "duration": 0.0}}]}}

Now convert:
Input: "{text}"
Output:"""

    try:
        res = requests.post(OLLAMA_URL, json={
            "model": OLLAMA_MODEL,
            "prompt": prompt,
            "stream": False,
            "format": "json",
        }, timeout=60)

        raw = res.json().get("response", "{}")
        parsed_obj = json.loads(raw)
        print(f"[Llama] sequence input='{text}' → raw obj: {parsed_obj}")

        # "steps", "commands", "sequence" 등 어떤 키로 오든 배열을 찾음
        parsed = None
        for val in parsed_obj.values():
            if isinstance(val, list):
                parsed = val
                break
        if parsed is None:
            parsed = []

    except Exception as e:
        print(f"[Llama] sequence 실패: {e}")
        parsed = []

    result = []
    for item in parsed:
        command = item.get("command", "stop")
        if command not in LIMO_COMMANDS:
            command = "stop"
        speed_raw    = item.get("speed")
        duration_raw = item.get("duration")
        result.append({
            "command":  command,
            "speed":    float(speed_raw)    if speed_raw    is not None else 0.5,
            "duration": float(duration_raw) if duration_raw is not None else 2.0,
        })

    return result if result else [{"command": "stop", "speed": 0.0, "duration": 0.0}]


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
