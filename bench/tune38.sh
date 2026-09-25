#!/usr/bin/env bash
# After the quiz: sweep MTP draft length and GPU layers on the same 1024 token request.
S="$(cd "$(dirname "$0")" && pwd)"
M=${MODELS:-$HOME/models}/Qwen3.8-27B-Q5_K_M.gguf
export PORT=18080

for cfg in "18 4" "18 6" "20 3" "20 5" "22 4"; do
    set -- $cfg; ngl=$1; nmax=$2; label=tune-ngl$ngl-n$nmax
    llama-server -m $M -ngl $ngl -c 32768 -np 1 -t 12 --jinja -fa on -ctk q8_0 -ctv q8_0 \
        --spec-type draft-mtp --spec-draft-n-max $nmax \
        --host 127.0.0.1 --port $PORT > $S/logs/server-$label.log 2>&1 &
    srv=$!
    ok=1
    until curl -sf http://127.0.0.1:$PORT/health >/dev/null; do
        kill -0 $srv 2>/dev/null || { echo "$label: server died: $(grep -iE 'error|memory|fail' $S/logs/server-$label.log | tail -2 | tr '\n' ' ')"; ok=0; break; }
        sleep 2
    done
    [ $ok = 1 ] || continue
    vram=$(nvidia-smi --query-gpu=memory.used --format=csv,noheader)
    python3 $S/gen_test.py low 1024 > $S/$label.out 2>&1
    gen=$(grep "^gen:" $S/$label.out)
    acc=$(grep -oE "draft acceptance = [0-9.]+ .*mean len = +[0-9.]+" $S/logs/server-$label.log | tail -1)
    echo "$label vram=$vram | ${gen:-request failed} | ${acc:-no draft stats}"
    kill $srv; wait $srv 2>/dev/null
done
echo "== TUNE DONE =="
