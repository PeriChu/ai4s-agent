#!/usr/bin/env bash
set -euo pipefail

RUN_ID="${RUN_ID:?RUN_ID required}"
CFG="${1:-configs/retro.yaml}"
SMI="${2:-runs/${RUN_ID}/intermediates/top_for_retro.smi}"

LOG_JSONL="${LOG_JSONL:-runs/${RUN_ID}/logs.jsonl}"
mkdir -p "runs/${RUN_ID}/retro" "runs/${RUN_ID}/tmp"

ts() { date -u +"%Y-%m-%dT%H:%M:%SZ"; }
log() {
  local event="$1"; local stage="$2"; local msg="$3"; local extra="${4:-{}}"
  printf '{"ts":"%s","run_id":"%s","event":"%s","stage":"%s","level":"INFO","msg":%s,"extra":%s}\n' \
    "$(ts)" "$RUN_ID" "$event" "$stage" "$(python3 - <<PY
import json; print(json.dumps("$msg"))
PY)" "$extra" >> "$LOG_JSONL"
}

command -v yq >/dev/null || { echo "yq is required"; exit 1; }

IMG="$(yq -r '.aizynth.docker_image' "$CFG")"
BATCH="$(yq -r '.parallel.batch_size' "$CFG")"
JOBS="$(yq -r '.parallel.retro_jobs' "$CFG")"
MAX_STEPS="$(yq -r '.aizynth.max_steps' "$CFG")"
TL="$(yq -r '.aizynth.time_limit_s' "$CFG")"
STOCK="$(yq -r '.aizynth.stock_smiles' "$CFG")"
TOPK_ROUTES="$(yq -r '.aizynth.topk_routes' "$CFG")"

log "RETRO_START" "retro" "Starting retrosynthesis batches" "{\"smi\":\"$SMI\",\"jobs\":$JOBS,\"batch\":$BATCH}"

SPLIT_DIR="runs/${RUN_ID}/tmp/retro_batches"
rm -rf "$SPLIT_DIR"; mkdir -p "$SPLIT_DIR"
split -l "$BATCH" -d -a 4 "$SMI" "$SPLIT_DIR/batch_"

run_one_retro_batch() {
  local batch_file="$1"
  local out_json="${batch_file}.retro.json"
  docker run --rm -v "$(pwd)":/work -w /work "$IMG" bash -lc "\
    python3 src/scoring/retro_aizynth_runner.py \
      --smiles_file '$batch_file' \
      --out_json '$out_json' \
      --stock '$STOCK' \
      --max_steps $MAX_STEPS \
      --time_limit_s $TL \
      --topk_routes $TOPK_ROUTES\
  " >/dev/null
}
export -f run_one_retro_batch
export IMG MAX_STEPS TL STOCK TOPK_ROUTES

parallel -j "$JOBS" run_one_retro_batch ::: "$SPLIT_DIR"/batch_*

python3 src/scoring/merge_retro_json.py --glob "$SPLIT_DIR/batch_*.retro.json" --out "runs/${RUN_ID}/retro/retro_merged.json"
log "RETRO_DONE" "retro" "Retrosynthesis done" "{\"out\":\"runs/${RUN_ID}/retro/retro_merged.json\"}"
