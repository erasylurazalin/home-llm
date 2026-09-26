# home-llm

A local LLM on my desktop for background jobs while I'm away: llama.cpp served
by a systemd user unit, plus the scripts I used to pick the model and tune it
for this hardware.

Hardware: Ryzen 9 5950X, 32 GB DDR4, GTX 1080 with 8 GB. Vulkan build of
llama.cpp (b10488).

The goal was quality first. Speed only has to be usable, since nobody is
waiting on the output.

## Picking the model

I compared Qwen3.8-27B (dense) with Qwen3.6-35B-A3B (mixture of experts). On
the Artificial Analysis Intelligence Index v4.3 the 27B scores 34 against 19.
Bigger models were out: most don't fit in 32 GB of RAM, and the one that fits
at 2-bit scores lower than the 27B.

I used a pre-quantized GGUF, Q5_K_M (20.9 GB, SHA256 checked). I didn't
quantize it myself. Uniform Q5_K_M on purpose: dynamic quants were reported to
be slow with partial CPU offload.

## Quiz

`bench/eval.py` asks 8 questions with checkable answers (logic, arithmetic
traps, counting letters, a weekday, a clock angle, conditional probability) and
runs the model's bracket matcher against 9 tests.

| | Qwen3.6-35B-A3B, medium | Qwen3.8-27B, medium | Qwen3.8-27B, xhigh |
|---|---|---|---|
| Passed | 8/8 | 8/8 | 8/8 |
| Tokens | 31,386 | 5,380 | 3,227 |
| Wall time | 17.6 min | 13.2 min | 9.2 min |
| Generation | about 31 tok/s | about 7 tok/s | about 6.3 tok/s |

Too easy to separate the models on accuracy. What it does show: the 27B thinks
far less on simple questions, so a job takes about as long as on the MoE model
despite a quarter of the speed. Answers and reasoning are in `bench/results/`.

## Tuning

At 32k context `llama-fit-params` puts 18 of 64 layers on the GPU, so most of
the model runs on the CPU. Plain generation is 2.6 tok/s, and the thread count
barely matters (8, 12 and 16 threads all land between 2.55 and 2.68 tok/s).

The model ships an MTP head, so speculative decoding needs no separate draft
model. One 1024 token request per config, from `bench/tune38.sh`:

| GPU layers | Draft length | Generation | Acceptance | VRAM |
|---|---|---|---|---|
| 18 | off | 2.6 tok/s | not used | 6738 MiB |
| 18 | 3 (default) | 6.4 to 6.7 tok/s | 77% | 7197 MiB |
| 18 | 4 | 6.0 tok/s | 66% | 7281 MiB |
| 18 | 6 | 5.7 tok/s | 55% | 7356 MiB |
| 20 | 3 | 6.4 tok/s | 71% | 7847 MiB |
| 20 | 5 | 6.6 tok/s | 61% | 7928 MiB |
| 22 | 4 | out of VRAM | not run | not run |

MTP is worth about 2.5x. Longer drafts get accepted less often and end up
slower. More GPU layers don't help and leave almost no VRAM for the desktop.
These are single runs with sampling on, so anything under about 0.5 tok/s is
noise.

The KV cache is q8_0, which halves its memory against f16.

## Running it

`systemd/llama.service` is the unit I run. It is the tuned config at 64k
context, which costs one GPU layer (17 instead of 18).

It also points at a patched copy of the model's chat template, which isn't in
this repo. I drive the model through Claude Code, which sends system messages
in the middle of a conversation, and the stock Qwen template refuses any
system message that isn't first. The patch renders those as ordinary system
blocks instead. Drop the `--chat-template-file` line to use the stock template.

```
cp systemd/llama.service ~/.config/systemd/user/
systemctl --user enable --now llama
```

The bench scripts expect the model in `~/models` (or `$MODELS`) and start their
own server on port 18080.

## Known limits

- One request at a time (`-np 1`). Fine for one background job.
- The quiz is too easy to rank the models.

What I'm doing next is in [TODO.md](TODO.md).
