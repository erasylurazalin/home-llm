"""Tiny checkable eval against a running llama-server.

usage: eval.py <label> <port> <effort> [max_tokens]
Writes results/<label>.json next to this script and prints a summary.
"""
import json
import pathlib
import re
import subprocess
import sys
import time
import urllib.request

label, port, effort = sys.argv[1], sys.argv[2], sys.argv[3]
max_tokens = int(sys.argv[4]) if len(sys.argv) > 4 else 16000
here = pathlib.Path(__file__).parent
(here / "results").mkdir(exist_ok=True)

SUFFIX = "\n\nEnd your reply with a final line of the form: ANSWER: <answer>"

TASKS = [
    ("sheep", "A farmer has 17 sheep. All but 9 run away. He then buys twice as many "
              "sheep as he has left, and afterwards sells a third of his total flock. "
              "How many sheep does he have now?", "18"),
    ("order", "Alice is older than Bob. Carol is younger than Bob. Dave is older than "
              "Alice. Erin is younger than Carol. Who is the second youngest?", "carol"),
    ("zeros", "What is the smallest positive integer n such that n! ends in exactly "
              "100 trailing zeros?", "405"),
    ("letters", "How many times does the letter r appear in the phrase "
                "'strawberry raspberry'?", "6"),
    ("weekday", "What day of the week was 15 September 2026?", "tuesday"),
    ("clock", "At exactly 3:40, what is the smaller angle in degrees between the hour "
              "hand and the minute hand of an analog clock?", "130"),
    ("probability", "I roll two fair six-sided dice. Given that at least one die shows a 6, "
                    "what is the probability that both show a 6? Give a reduced fraction.",
     "1/11"),
    ("brackets", "Write a Python function `is_balanced(s: str) -> bool` that returns True "
                 "when the brackets (), [] and {} in s are balanced and properly nested, "
                 "ignoring all other characters. Put the full function in one ```python "
                 "code block.", None),
]

BRACKET_TESTS = [
    ("", True), ("()", True), ("([]{})", True), ("([)]", False), ("((", False),
    ("a(b[c]{d}e)f", True), ("}{", False), ("{[()()]}", True), ("(]", False),
]


def ask(content):
    body = {
        "messages": [{"role": "user", "content": content}],
        "max_tokens": max_tokens,
        "temperature": 1.0, "top_p": 0.95, "top_k": 20, "min_p": 0.0,
        "chat_template_kwargs": {"reasoning_effort": effort},
    }
    req = urllib.request.Request(
        f"http://127.0.0.1:{port}/v1/chat/completions",
        data=json.dumps(body).encode(), headers={"Content-Type": "application/json"})
    start = time.time()
    with urllib.request.urlopen(req, timeout=4 * 3600) as resp:
        out = json.load(resp)
    return out, time.time() - start


def check_code(text):
    m = re.findall(r"```python\n(.*?)```", text, re.S)
    if not m:
        return False, "no code block"
    harness = m[-1] + "\nimport json\nprint(json.dumps([is_balanced(s) for s, _ in %r]))" % BRACKET_TESTS
    try:
        r = subprocess.run([sys.executable, "-c", harness], capture_output=True, text=True, timeout=10)
        got = json.loads(r.stdout.strip().splitlines()[-1])
    except Exception as e:  # noqa: BLE001
        return False, f"crash: {e}"
    want = [w for _, w in BRACKET_TESTS]
    return got == want, f"{sum(g == w for g, w in zip(got, want))}/{len(want)} tests"


results = []
for name, question, expected in TASKS:
    prompt = question if expected is None else question + SUFFIX
    out, wall = ask(prompt)
    choice = out["choices"][0]
    content = choice["message"].get("content") or ""
    t = out.get("timings", {})
    if expected is None:
        ok, note = check_code(content)
    else:
        m = re.findall(r"ANSWER:\s*(.+)", content)
        got = m[-1].strip().strip("*.` ").lower() if m else ""
        ok = got.replace(" degrees", "").replace("°", "") == expected
        note = f"got {got!r}"
    row = {
        "task": name, "ok": ok, "note": note, "finish": choice.get("finish_reason"),
        "gen_tokens": t.get("predicted_n"), "gen_tps": t.get("predicted_per_second"),
        "draft_n": t.get("draft_n"), "draft_accepted": t.get("draft_n_accepted"),
        "wall_s": round(wall, 1), "content": content,
        "reasoning": choice["message"].get("reasoning_content") or "",
    }
    results.append(row)
    print(f"{name:12} {'PASS' if ok else 'FAIL'}  {note:28} {row['gen_tokens']} tok "
          f"@ {row['gen_tps'] or 0:.2f} tok/s  {row['wall_s']}s  finish={row['finish']}", flush=True)

(here / "results" / f"{label}.json").write_text(json.dumps(results, indent=1))
passed = sum(r["ok"] for r in results)
tok = sum(r["gen_tokens"] or 0 for r in results)
wall = sum(r["wall_s"] for r in results)
print(f"== {label}: {passed}/{len(results)} passed, {tok} tokens, {wall/60:.1f} min total")
