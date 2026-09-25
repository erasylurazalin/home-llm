#!/usr/bin/env bash
# Qwen3.8-27B Q5_K_M: thread sweep, quick MTP A/B on a short generation, then one full quiz with the faster setup.
S="$(cd "$(dirname "$0")" && pwd)"
M=${MODELS:-$HOME/models}/Qwen3.8-27B-Q5_K_M.gguf
export PORT=18080
NGL=${NGL:-18}

start() {  # start <label> <extra args...>; sets SRV
    local label=$1; shift
    llama-server -m $M -ngl $NGL -c 32768 -np 1 -t 16 --jinja -fa on -ctk q8_0 -ctv q8_0 \
        --host 127.0.0.1 --port $PORT "$@" > $S/logs/server-$label.log 2>&1 &
    SRV=$!
    until curl -sf http://127.0.0.1:$PORT/health >/dev/null; do
        kill -0 $SRV 2>/dev/null || { echo "$label: server died"; grep -iE "error|fail|memory" $S/logs/server-$label.log | tail -10; return 1; }
        sleep 2
    done
    echo "== server $label up, $(nvidia-smi --query-gpu=memory.used --format=csv,noheader) VRAM, $(free -g | awk '/Mem/{print $7}')G RAM available =="
}
stop() { kill $SRV 2>/dev/null; wait $SRV 2>/dev/null; }

echo "== llama-bench qwen38 ngl=$NGL, thread sweep =="
llama-bench -m $M -ngl $NGL -fa 1 -ctk q8_0 -ctv q8_0 -t 8,12,16 -p 512 -n 64 -r 1 2>&1 | grep -E "^\| (model|qwen)|error|fail"

for mode in nomtp mtp; do
    extra=(); [ $mode = mtp ] && extra=(--spec-type draft-mtp)
    start ab-$mode "${extra[@]}" || continue
    echo "== A/B $mode: 1024 token generation =="
    python3 $S/gen_test.py low 1024 | grep -E "^(effort|prompt|gen|draft):" || echo "ab-$mode: request failed"
    stop
done

nomtp=$(grep -oE "eval time .* ([0-9.]+) tokens per second" $S/logs/server-ab-nomtp.log | tail -1 | grep -oE "[0-9.]+ tokens per second" | cut -d' ' -f1)
mtp=$(grep -oE "eval time .* ([0-9.]+) tokens per second" $S/logs/server-ab-mtp.log | tail -1 | grep -oE "[0-9.]+ tokens per second" | cut -d' ' -f1)
echo "== A/B result: nomtp=${nomtp:-none} tok/s, mtp=${mtp:-none} tok/s =="
extra=()
if [ -n "$mtp" ] && [ -n "$nomtp" ] && awk "BEGIN{exit !($mtp > $nomtp)}"; then extra=(--spec-type draft-mtp); label=qwen38-27b-mtp; else label=qwen38-27b-nomtp; fi

start $label "${extra[@]}" && {
    echo "== quiz $label =="
    python3 $S/eval.py $label $PORT medium 16000 || echo "$label: eval crashed"
    stop
}
echo "== PIPELINE DONE =="
