OLLAMA_URL = "http://localhost:11434"
OLLAMA_MODEL = "llama3.1:8b"
OLLAMA_TIMEOUT = 60
LLM_RETRIES = 1  # extra attempts after the first invalid response

FRAME_ID = "map"
DEFAULT_SAFETY_MARGIN_M = 0.45
DEFAULT_SPEED_MPS = 0.2
MAX_SPEED_MPS = 0.5  # reject anything faster than this
ALLOWED_ACTIONS = ("move",)
