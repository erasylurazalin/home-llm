# TODO

## Next: quantize a model myself

So far I've only used a model someone else quantized. Next I want to do it
myself on something small enough to iterate on quickly:

- Take a small model (1 to 4B) at full precision and quantize it with
  `llama-quantize` to a few levels, for example Q8_0, Q5_K_M and Q4_K_M.
- Run each through `bench/eval.py` and the speed test, and compare file size,
  memory, tok/s and answers against the unquantized model.
- Try an importance matrix (`llama-imatrix`) on the lowest level and see if it
  wins back quality.

## Later

- A harder eval. The current quiz is 8/8 for every model, so it can't rank
  them.
- Retest speed at 64k context, which is what the service actually runs.
- A coding-agent benchmark: the model works through real issues in a small
  TypeScript repo and gets graded by hidden tests. Half built, not in this repo
  yet.
