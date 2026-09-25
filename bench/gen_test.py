"""Send one chat request to a running llama-server and print its timings.

usage: gen_test.py [effort] [max_tokens]
"""
import json
import os
import sys
import time
import urllib.request

effort = sys.argv[1] if len(sys.argv) > 1 else "medium"
max_tokens = int(sys.argv[2]) if len(sys.argv) > 2 else 1024

prompt = (
    "A farmer has 17 sheep. All but 9 run away, then he buys twice as many as "
    "he has left and sells a third of the total. How many sheep does he have? "
    "Then write a short Python function that solves the general version, with "
    "the counts as parameters."
)

body = {
    "messages": [{"role": "user", "content": prompt}],
    "max_tokens": max_tokens,
    "temperature": 1.0,
    "top_p": 0.95,
    "top_k": 20,
    "min_p": 0.0,
    "chat_template_kwargs": {"reasoning_effort": effort},
}

req = urllib.request.Request(
    f"http://127.0.0.1:{os.environ.get('PORT', '8080')}/v1/chat/completions",
    data=json.dumps(body).encode(),
    headers={"Content-Type": "application/json"},
)
start = time.time()
with urllib.request.urlopen(req, timeout=7200) as resp:
    out = json.load(resp)
wall = time.time() - start

msg = out["choices"][0]["message"]
t = out.get("timings", {})
print(f"effort={effort} wall={wall:.1f}s finish={out['choices'][0].get('finish_reason')}")
print(f"prompt: {t.get('prompt_n')} tok at {t.get('prompt_per_second', 0):.1f} tok/s")
print(f"gen:    {t.get('predicted_n')} tok at {t.get('predicted_per_second', 0):.2f} tok/s")
if "draft_n" in t:
    print(f"draft:  {t.get('draft_n_accepted')}/{t.get('draft_n')} accepted")
print("--- reasoning (first 300 chars) ---")
print((msg.get("reasoning_content") or "")[:300])
print("--- answer ---")
print(msg.get("content") or "")
