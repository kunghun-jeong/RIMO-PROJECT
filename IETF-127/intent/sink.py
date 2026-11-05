"""
Where a finished intent goes. A sink is any object with deliver(result, meta).
LocalFileSink is the only one for now; an HTTP/A2A sink can be added later
without touching intent_llm.py.
"""
import json
import re
from datetime import datetime
from pathlib import Path

OUTPUT_DIR = Path(__file__).resolve().parent.parent / "outputs"


class LocalFileSink:
    """
    outputs/<timestamp>_<intent_id>.json   the policy JSON itself ({"intent": ...})
    outputs/log.jsonl                      one line per request: input, source, corrections, file
    """

    def __init__(self, directory: Path = OUTPUT_DIR):
        self.dir = Path(directory)
        self.dir.mkdir(parents=True, exist_ok=True)

    def next_seq(self) -> int:
        """Continue numbering across runs (move_001, move_002, ...)."""
        nums = [
            int(m.group(1))
            for p in self.dir.glob("*_move_*.json")
            if (m := re.search(r"_move_(\d+)\.json$", p.name))
        ]
        return max(nums, default=0) + 1

    def deliver(self, result: dict, meta: dict, input_text: str = "") -> Path:
        stamp = datetime.now().strftime("%Y%m%d-%H%M%S")
        path = self.dir / f"{stamp}_{result['intent']['intent_id']}.json"
        path.write_text(json.dumps(result, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
        entry = {
            "time": datetime.now().isoformat(timespec="seconds"),
            "input": input_text,
            "file": path.name,
            "source": meta["source"],
            "corrections": meta["corrections"],
            "error": meta["error"],
        }
        with open(self.dir / "log.jsonl", "a", encoding="utf-8") as f:
            f.write(json.dumps(entry, ensure_ascii=False) + "\n")
        return path
