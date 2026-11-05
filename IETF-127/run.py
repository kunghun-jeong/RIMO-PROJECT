import json
import sys

from intent import intent_llm
from intent.extract import InputError
from intent.sink import LocalFileSink

if __name__ == "__main__":
    text = " ".join(sys.argv[1:]).strip()
    if not text:
        sys.exit('usage: python run.py "x:30 y:40 좌표까지 속도 0.2로 이동 후 보고해줘"')

    sink = LocalFileSink()
    intent_llm.set_next_seq(sink.next_seq())
    try:
        result, meta = intent_llm.infer(text)
    except InputError as e:
        sys.exit(f"input error: {e}")

    path = sink.deliver(result, meta, input_text=text)
    print(json.dumps(result, ensure_ascii=False, indent=2))
    print(f"[source={meta['source']}] corrections={meta['corrections']} error={meta['error']}", file=sys.stderr)
    print(f"saved: {path}", file=sys.stderr)
