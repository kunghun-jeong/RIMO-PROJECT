import json
import unittest

import requests

from intent import intent_llm
from intent.extract import InputError, extract


def fake(intent_overrides=None, raw=None):
    """LLM stub returning a valid intent, with optional wrong fields."""
    def llm(_prompt):
        if raw is not None:
            return raw
        body = {
            "intent_id": "x", "action": "move",
            "target_location": {"x": 0, "y": 0, "frame_id": "map"},
            "constraints": {"safety_margin_m": 0.45, "speed_mps": 0.2},
            "report": True,
        }
        body.update(intent_overrides or {})
        return json.dumps({"intent": body})
    return llm


def loc(result):
    t = result["intent"]["target_location"]
    return t["x"], t["y"]


class Extract(unittest.TestCase):
    def test_basic(self):
        self.assertEqual(extract("x 50, y 50 위치로 이동해줘"), {"x": 50.0, "y": 50.0})

    def test_negative_decimal(self):
        self.assertEqual(extract("x -16, y 0.5로 가"), {"x": -16.0, "y": 0.5})

    def test_korean_particles(self):
        self.assertEqual(extract("x는 3.5, y는 -2.25로 가"), {"x": 3.5, "y": -2.25})

    def test_swapped(self):
        self.assertEqual(extract("y 2, x 7"), {"x": 7.0, "y": 2.0})

    def test_pair(self):
        self.assertEqual(extract("move to (1, 2)"), {"x": 1.0, "y": 2.0})

    def test_unicode_minus(self):
        self.assertEqual(extract("x −4 y 5"), {"x": -4.0, "y": 5.0})

    def test_speed_margin(self):
        e = extract("x 1 y 2 0.3 m/s, 안전 여유 0.6")
        self.assertEqual((e["speed_mps"], e["safety_margin_m"]), (0.3, 0.6))

    def test_meeting_scenario_form(self):
        e = extract("x:30 y:40 좌표까지 속도 0.3으로 이동 후 보고해줘")
        self.assertEqual(e, {"x": 30.0, "y": 40.0, "speed_mps": 0.3})

    def test_speed_word_without_unit(self):
        self.assertEqual(extract("x 1 y 2 속도 0.15")["speed_mps"], 0.15)
        self.assertEqual(extract("x 1 y 2 speed: 0.25")["speed_mps"], 0.25)

    def test_speed_zero_rejected(self):
        with self.assertRaises(InputError):
            extract("x:00 y:00 좌표까지 속도 00으로 이동 후 보고해줘")

    def test_conflicting_speeds(self):
        with self.assertRaises(InputError):
            extract("x 1 y 2 속도 0.2, 0.4 m/s")

    def test_missing(self):
        for t in ("앞으로 가", "x 5 로 가", "y 5 로 가", ""):
            with self.assertRaises(InputError, msg=t):
                extract(t)

    def test_ambiguous(self):
        with self.assertRaises(InputError):
            extract("x 1, y 2, x 3")

    def test_speed_cap(self):
        with self.assertRaises(InputError):
            extract("x 1 y 2 2.0 m/s")

    def test_word_containing_x_is_ignored(self):
        with self.assertRaises(InputError):
            extract("max 5 and by 3")


class Infer(unittest.TestCase):
    def test_50_50(self):
        r, m = intent_llm.infer("x 50, y 50 위치로 이동해줘", llm=fake({"target_location": {"x": 50, "y": 50}}))
        self.assertEqual(loc(r), (50.0, 50.0))
        self.assertEqual(m["source"], "llm")
        self.assertEqual(m["corrections"][:0], [])

    def test_wrong_llm_numbers_are_overridden(self):
        r, m = intent_llm.infer("x 50, y 50 위치로 이동해줘", llm=fake({"target_location": {"x": 5, "y": 500}}))
        self.assertEqual(loc(r), (50.0, 50.0))
        self.assertTrue(any(c.startswith("x:") for c in m["corrections"]))
        self.assertTrue(any(c.startswith("y:") for c in m["corrections"]))

    def test_wrong_action_forced_to_move(self):
        r, _ = intent_llm.infer("x 1 y 2", llm=fake({"action": "delete_all"}))
        self.assertEqual(r["intent"]["action"], "move")

    def test_extra_fields_stripped(self):
        r, _ = intent_llm.infer("x 1 y 2", llm=fake({"evil": "rm -rf", "target_location": {"x": 1, "y": 2, "z": 9}}))
        self.assertEqual(set(r["intent"]), {"intent_id", "action", "target_location", "constraints", "report"})
        self.assertEqual(set(r["intent"]["target_location"]), {"x", "y", "frame_id"})

    def test_report_false_kept(self):
        r, _ = intent_llm.infer("x 1 y 2 보고하지 마", llm=fake({"report": False}))
        self.assertIs(r["intent"]["report"], False)

    def test_defaults(self):
        r, _ = intent_llm.infer("x 1 y 2", llm=fake())
        self.assertEqual(r["intent"]["constraints"], {"safety_margin_m": 0.45, "speed_mps": 0.2})
        self.assertEqual(r["intent"]["target_location"]["frame_id"], "map")

    def test_stated_speed_wins(self):
        r, _ = intent_llm.infer("x 1 y 2 0.3 m/s", llm=fake())
        self.assertEqual(r["intent"]["constraints"]["speed_mps"], 0.3)

    def test_garbage_then_fallback(self):
        r, m = intent_llm.infer("x 50, y 50", llm=fake(raw="sorry, I cannot"))
        self.assertEqual(m["source"], "rules")
        self.assertEqual(loc(r), (50.0, 50.0))

    def test_retry_recovers(self):
        calls = []
        good = fake()
        def flaky(p):
            calls.append(1)
            return "nope" if len(calls) == 1 else good(p)
        _, m = intent_llm.infer("x 1 y 2", llm=flaky)
        self.assertEqual((m["source"], len(calls)), ("llm", 2))

    def test_non_numeric_llm_coords_rejected(self):
        _, m = intent_llm.infer("x 1 y 2", llm=fake({"target_location": {"x": "fifty", "y": 2}}))
        self.assertEqual(m["source"], "rules")

    def test_llm_unreachable_falls_back(self):
        def down(_):
            raise requests.ConnectionError("refused")
        r, m = intent_llm.infer("x 50, y 50", llm=down)
        self.assertEqual((m["source"], loc(r)), ("rules", (50.0, 50.0)))

    def test_no_coords_never_calls_llm(self):
        def boom(_):
            raise AssertionError("LLM called")
        with self.assertRaises(InputError):
            intent_llm.infer("앞으로 가", llm=boom)

    def test_ids_increment(self):
        a, _ = intent_llm.infer("x 1 y 2", llm=fake())
        b, _ = intent_llm.infer("x 1 y 2", llm=fake())
        self.assertNotEqual(a["intent"]["intent_id"], b["intent"]["intent_id"])


class Sink(unittest.TestCase):
    def test_saves_json_and_continues_numbering(self):
        import tempfile
        from pathlib import Path
        from intent.sink import LocalFileSink

        with tempfile.TemporaryDirectory() as d:
            sink = LocalFileSink(Path(d))
            self.assertEqual(sink.next_seq(), 1)
            intent_llm.set_next_seq(sink.next_seq())
            r, m = intent_llm.infer("x 50, y 50", llm=fake())
            path = sink.deliver(r, m, input_text="x 50, y 50")
            self.assertEqual(json.loads(path.read_text(encoding="utf-8")), r)
            self.assertEqual(r["intent"]["intent_id"], "move_001")
            self.assertEqual(sink.next_seq(), 2)
            log = [json.loads(l) for l in (Path(d) / "log.jsonl").read_text(encoding="utf-8").splitlines()]
            self.assertEqual((log[0]["input"], log[0]["source"]), ("x 50, y 50", "llm"))


if __name__ == "__main__":
    unittest.main()
