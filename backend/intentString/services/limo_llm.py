import requests
import json
import re

OLLAMA_URL = "http://localhost:11434/api/generate"
OLLAMA_MODEL = "llama3.1:8b"

LIMO_COMMANDS = [
    "go straight", "go straight slow", "go straight fast",
    "move back", "move back slow",
    "stop",
    "rotate left", "rotate right",
    "turn left", "turn right",
    "sharp left", "sharp right",
    "curve left", "curve right",
]


def natural_to_limo_command(text: str) -> dict:
    prompt = f"""You are a controller for AgileX LIMO robot.
The user gives a natural language command. Select the best matching command and return JSON.

Available commands:
- "go straight"      : move forward at normal speed
- "go straight slow" : move forward slowly
- "go straight fast" : move forward fast
- "move back"        : move backward at normal speed
- "move back slow"   : move backward slowly
- "stop"             : stop all movement
- "rotate left"      : spin in place to the left
- "rotate right"     : spin in place to the right
- "turn left"        : arc turn left while moving forward
- "turn right"       : arc turn right while moving forward
- "sharp left"       : tight left turn while moving forward
- "sharp right"      : tight right turn while moving forward
- "curve left"       : gentle left curve at higher speed
- "curve right"      : gentle right curve at higher speed

Rules:
- command must be exactly one of the 14 options above
- duration: seconds to run (default 2.0)

Examples:
Input: "앞으로 가줘"
Output: {{"command": "go straight", "duration": 2.0}}

Input: "천천히 앞으로"
Output: {{"command": "go straight slow", "duration": 2.0}}

Input: "빠르게 전진"
Output: {{"command": "go straight fast", "duration": 2.0}}

Input: "제자리에서 왼쪽으로 돌아"
Output: {{"command": "rotate left", "duration": 2.0}}

Input: "왼쪽으로 크게 돌아"
Output: {{"command": "sharp left", "duration": 2.0}}

Input: "완만하게 오른쪽으로 곡선"
Output: {{"command": "curve right", "duration": 3.0}}

Input: "멈춰"
Output: {{"command": "stop", "duration": 0.0}}

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
- "go straight"      : move forward at normal speed
- "go straight slow" : move forward slowly
- "go straight fast" : move forward fast
- "move back"        : move backward at normal speed
- "move back slow"   : move backward slowly
- "stop"             : stop all movement
- "rotate left"      : spin in place to the left
- "rotate right"     : spin in place to the right
- "turn left"        : arc turn left while moving forward
- "turn right"       : arc turn right while moving forward
- "sharp left"       : tight left turn while moving forward
- "sharp right"      : tight right turn while moving forward
- "curve left"       : gentle left curve at higher speed
- "curve right"      : gentle right curve at higher speed

Rules:
- Each command must be exactly one of the 14 options above
- duration in seconds. "one block"=3.0s, "two blocks"=6.0s, "three blocks"=9.0s
- Return a JSON object with a "steps" key containing the array

Examples:
Input: "go forward two blocks and turn left"
Output: {{"steps": [{{"command": "go straight", "duration": 6.0}}, {{"command": "turn left", "duration": 2.0}}]}}

Input: "천천히 앞으로 가다가 오른쪽으로 크게 돌아"
Output: {{"steps": [{{"command": "go straight slow", "duration": 3.0}}, {{"command": "sharp right", "duration": 2.0}}]}}

Input: "제자리에서 왼쪽으로 돌고 빠르게 전진"
Output: {{"steps": [{{"command": "rotate left", "duration": 2.0}}, {{"command": "go straight fast", "duration": 3.0}}]}}

Input: "완만하게 왼쪽 곡선으로 이동 후 정지"
Output: {{"steps": [{{"command": "curve left", "duration": 4.0}}, {{"command": "stop", "duration": 0.0}}]}}

Input: "멈춰"
Output: {{"steps": [{{"command": "stop", "duration": 0.0}}]}}

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


def natural_to_limo_intent(text: str) -> dict:
    """
    자연어를 분석해 mode와 필요한 데이터를 반환.

    반환 형태:
      {"mode": "move",       "steps": [...]}
      {"mode": "trace",      "target_class": "person"}
      {"mode": "avoid"}
      {"mode": "stop_mode"}
    """
    prompt = f"""You are a controller for AgileX LIMO robot.
Classify the user command into one of 4 modes and return JSON.

Modes:
- "move"      : movement command (go, turn, rotate, curve, stop movement, etc.)
- "trace"     : follow or chase a specific object or person
- "avoid"     : autonomous obstacle avoidance mode
- "greet"     : find a person and greet them (search → approach → greeting motion)
- "stop_mode" : stop current autonomous mode (trace, avoid, or greet)

For "move" mode, parse steps using these commands:
"go straight", "go straight slow", "go straight fast",
"move back", "move back slow", "stop",
"rotate left", "rotate right",
"turn left", "turn right", "sharp left", "sharp right",
"curve left", "curve right"
duration unit is seconds. "one block"=3.0s, "two blocks"=6.0s

For "trace" mode, set target_class to the YOLO object name (e.g. "person", "bottle", "chair", "dog").

Output format per mode:
move      -> {{"mode": "move", "steps": [{{"command": "...", "duration": 0.0}}]}}
trace     -> {{"mode": "trace", "target_class": "person"}}
avoid     -> {{"mode": "avoid"}}
greet     -> {{"mode": "greet"}}
stop_mode -> {{"mode": "stop_mode"}}

Examples:
Input: "앞으로 가줘"
Output: {{"mode": "move", "steps": [{{"command": "go straight", "duration": 2.0}}]}}

Input: "천천히 앞으로 가다가 왼쪽으로 돌아"
Output: {{"mode": "move", "steps": [{{"command": "go straight slow", "duration": 3.0}}, {{"command": "turn left", "duration": 2.0}}]}}

Input: "앞 사람 쫒아"
Output: {{"mode": "trace", "target_class": "person"}}

Input: "저 병 따라가"
Output: {{"mode": "trace", "target_class": "bottle"}}

Input: "의자 추적해"
Output: {{"mode": "trace", "target_class": "chair"}}

Input: "장애물 피해"
Output: {{"mode": "avoid"}}

Input: "자율 주행 시작"
Output: {{"mode": "avoid"}}

Input: "사람 찾아서 인사해"
Output: {{"mode": "greet"}}

Input: "사람한테 가서 인사해"
Output: {{"mode": "greet"}}

Input: "사람 찾아"
Output: {{"mode": "greet"}}

Input: "추적 멈춰"
Output: {{"mode": "stop_mode"}}

Input: "모드 종료"
Output: {{"mode": "stop_mode"}}

Now convert:
Input: "{text}"
Output:"""

    try:
        res = requests.post(OLLAMA_URL, json={
            "model":  OLLAMA_MODEL,
            "prompt": prompt,
            "stream": False,
            "format": "json",
        }, timeout=60)

        raw    = res.json().get("response", "{}")
        parsed = json.loads(raw)
        print(f"[Llama] intent input='{text}' → {parsed}")

    except Exception as e:
        print(f"[Llama] intent 실패: {e}")
        parsed = {}

    mode = parsed.get("mode", "move")
    if mode not in ("move", "trace", "avoid", "greet", "stop_mode"):
        mode = "move"

    if mode == "trace":
        return {
            "mode":         "trace",
            "target_class": parsed.get("target_class", "person"),
        }

    if mode == "avoid":
        return {"mode": "avoid"}

    if mode == "greet":
        return {"mode": "greet"}

    if mode == "stop_mode":
        return {"mode": "stop_mode"}

    # move: steps 정제
    raw_steps = parsed.get("steps", [])
    steps = []
    for item in raw_steps:
        command = item.get("command", "stop")
        if command not in LIMO_COMMANDS:
            command = "stop"
        duration_raw = item.get("duration")
        steps.append({
            "command":  command,
            "duration": float(duration_raw) if duration_raw is not None else 2.0,
        })

    if not steps:
        steps = [{"command": "stop", "duration": 0.0}]

    return {"mode": "move", "steps": steps}
