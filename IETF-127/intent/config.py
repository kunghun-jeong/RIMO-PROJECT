OLLAMA_URL = "http://localhost:11434"
OLLAMA_MODEL = "qwen2.5vl:3b"  # per the Edge team (ICTC2026 setup)
OLLAMA_TIMEOUT = 60
LLM_RETRIES = 1  # extra attempts after the first invalid response

FRAME_ID = "map"
DEFAULT_SAFETY_MARGIN_M = 0.45
DEFAULT_SPEED_MPS = 0.2
MAX_SPEED_MPS = 0.5  # reject anything faster than this
ALLOWED_ACTIONS = ("move",)
