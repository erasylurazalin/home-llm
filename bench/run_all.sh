#!/usr/bin/env bash
# Unattended chain: full Qwen3.8 medium run, tuning sweep, then an xhigh quiz. One summary at the end.
S="$(cd "$(dirname "$0")" && pwd)"
M=${MODELS:-$HOME/models}/Qwen3.8-27B-Q5_K_M.gguf
export PORT=18080

bash $S/run38b.sh > $S/logs/pipeline38.log 2>&1
bash $S/tune38.sh > $S/logs/tune38.log 2>&1

llama-server -m $M -ngl 18 -c 32768 -np 1 -t 12 --jinja -fa on -ctk q8_0 -ctv q8_0 \
    --spec-type draft-mtp --host 127.0.0.1 --port $PORT > $S/logs/server-xhigh.log 2>&1 &
srv=$!
until curl -sf http://127.0.0.1:$PORT/health >/dev/null; do
    kill -0 $srv 2>/dev/null || { echo "xhigh: server died" > $S/logs/xhigh.log; break; }
    sleep 2
done
kill -0 $srv 2>/dev/null && python3 $S/eval.py qwen38-27b-mtp-xhigh $PORT xhigh 32000 > $S/logs/xhigh.log 2>&1
kill $srv 2>/dev/null; wait $srv 2>/dev/null

echo "=== medium ==="; grep -E "PASS|FAIL|^== (A/B result|qwen)|died|crash|rror" $S/logs/pipeline38.log
echo "=== tune ==="; cat $S/logs/tune38.log
echo "=== xhigh ==="; grep -E "PASS|FAIL|^==|died|crash|rror|Traceback" $S/logs/xhigh.log
