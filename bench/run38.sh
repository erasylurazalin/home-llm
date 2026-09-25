#!/usr/bin/env bash
# Overnight test pipeline: baseline quiz on Qwen3.6, then Qwen3.8-27B Q5_K_M speed + quiz with MTP off and on.
S="$(cd "$(dirname "$0")" && pwd)"
M38=${MODELS:-$HOME/models}/Qwen3.8-27B-Q5_K_M.gguf
M36=${MODELS:-$HOME/models}/Qwen3.6-35B-A3B-UD-IQ4_XS.gguf
PORT=18080
NGL=${NGL:-18}

serve() {  # serve <label> <server args...>, runs the quiz, stops the server
    local label=$1; shift
    llama-server "$@" -c 32768 -np 1 -t 16 --jinja -fa on -ctk q8_0 -ctv q8_0 \
        --host 127.0.0.1 --port $PORT > $S/logs/server-$label.log 2>&1 &
    local srv=$!
    until curl -sf http://127.0.0.1:$PORT/health >/dev/null; do
        kill -0 $srv 2>/dev/null || { echo "$label: server died"; grep -iE "error|fail|memory" $S/logs/server-$label.log | tail -10; return 1; }
        sleep 2
    done
    echo "== quiz $label =="
    python3 $S/eval.py $label $PORT medium 16000 || echo "$label: eval crashed"
    kill $srv; wait $srv 2>/dev/null
}

if [ -z "$SKIP36" ]; then
    serve qwen36-35b-a3b -m $M36 -ngl 99 --n-cpu-moe 36
fi

echo "== llama-bench qwen38 ngl=$NGL, thread sweep =="
llama-bench -m $M38 -ngl $NGL -fa 1 -ctk q8_0 -ctv q8_0 -t 8,12,16 -p 512 -n 64 -r 1 2>&1 | grep -E "^\| (model|qwen)|error|fail"

serve qwen38-27b-nomtp -m $M38 -ngl $NGL
serve qwen38-27b-mtp -m $M38 -ngl $NGL --spec-type draft-mtp
echo "== PIPELINE DONE =="
