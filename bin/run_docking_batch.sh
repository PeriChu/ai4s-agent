#!/usr/bin/env bash
set -euo pipefail

RUN_ID="${RUN_ID:?RUN_ID required}"
CFG="${1:-configs/docking.yaml}"
SMI="${2:-runs/${RUN_ID}/intermediates/candidates_canon.smi}"

LOG_JSONL="${LOG_JSONL:-runs/${RUN_ID}/logs.jsonl}"
mkdir -p "runs/${RUN_ID}/docking" "runs/${RUN_ID}/tmp"

ts() { date -u +"%Y-%m-%dT%H:%M:%SZ"; }
log() {
  local event="$1"; local stage="$2"; local msg="$3"; local extra="${4:-{}}"
  printf '{"ts":"%s","run_id":"%s","event":"%s","stage":"%s","level":"INFO","msg":%s,"extra":%s}\n' \
    "$(ts)" "$RUN_ID" "$event" "$stage" "$(python3 - <<PY
import json; print(json.dumps("$msg"))
PY)" "$extra" >> "$LOG_JSONL"
}

command -v yq >/dev/null || { echo "yq is required"; exit 1; }
command -v jq >/dev/null || { echo "jq is required"; exit 1; }

VINA_IMG="$(yq -r '.vina.docker_image' "$CFG")"
EXH_FAST="$(yq -r '.vina.exhaustiveness_fast' "$CFG")"
EXH_REF="$(yq -r '.vina.exhaustiveness_refine' "$CFG")"
BATCH="$(yq -r '.parallel.batch_size' "$CFG")"
JOBS="$(yq -r '.parallel.vina_jobs' "$CFG")"
NUM_MODES="$(yq -r '.vina.num_modes' "$CFG")"
TIMEOUT_S="$(yq -r '.vina.timeout_s_per_ligand' "$CFG")"

POCKET_JSON="$(yq -r '.box.pocket_json' "$CFG")"
CX="$(jq -r '.center_x' "$POCKET_JSON")"
CY="$(jq -r '.center_y' "$POCKET_JSON")"
CZ="$(jq -r '.center_z' "$POCKET_JSON")"
SX="$(jq -r '.size_x' "$POCKET_JSON")"
SY="$(jq -r '.size_y' "$POCKET_JSON")"
SZ="$(jq -r '.size_z' "$POCKET_JSON")"

log "DOCK_VINA_FAST_START" "docking" "Starting Vina fast docking" "{\"smi\":\"$SMI\",\"jobs\":$JOBS,\"batch\":$BATCH,\"exhaustiveness\":$EXH_FAST}"

SPLIT_DIR="runs/${RUN_ID}/tmp/vina_fast_batches"
rm -rf "$SPLIT_DIR"; mkdir -p "$SPLIT_DIR"
split -l "$BATCH" -d -a 4 "$SMI" "$SPLIT_DIR/batch_"

run_one_batch_fast() {
  local batch_file="$1"
  local out_csv="${batch_file}.vina_fast.csv"
  docker run --rm -v "$(pwd)":/work -w /work "$VINA_IMG" bash -lc "\
    python3 src/scoring/docking_vina_runner.py \
      --smiles_file '$batch_file' \
      --out_csv '$out_csv' \
      --center $CX $CY $CZ \
      --size $SX $SY $SZ \
      --exhaustiveness $EXH_FAST \
      --num_modes $NUM_MODES \
      --timeout_s $TIMEOUT_S \
      --work_dir runs/${RUN_ID}/docking/vina_fast\
  " >/dev/null
}
export -f run_one_batch_fast
export VINA_IMG CX CY CZ SX SY SZ EXH_FAST NUM_MODES TIMEOUT_S RUN_ID

parallel -j "$JOBS" run_one_batch_fast ::: "$SPLIT_DIR"/batch_*

python3 src/scoring/merge_csv.py --glob "$SPLIT_DIR/batch_*.vina_fast.csv" --out "runs/${RUN_ID}/docking/vina_fast.csv"
log "DOCK_VINA_FAST_DONE" "docking" "Vina fast docking done" "{\"out\":\"runs/${RUN_ID}/docking/vina_fast.csv\"}"

python3 src/scoring/select_topk.py \
  --in_csv runs/${RUN_ID}/docking/vina_fast.csv \
  --score_col vina_score \
  --mode min \
  --topk 2000 \
  --out_smi runs/${RUN_ID}/docking/topk_for_vina_refine.smi

log "DOCK_VINA_REFINE_START" "docking" "Starting Vina refine docking" "{\"topk\":2000,\"exhaustiveness\":$EXH_REF}"

SPLIT_DIR2="runs/${RUN_ID}/tmp/vina_ref_batches"
rm -rf "$SPLIT_DIR2"; mkdir -p "$SPLIT_DIR2"
split -l "$BATCH" -d -a 4 runs/${RUN_ID}/docking/topk_for_vina_refine.smi "$SPLIT_DIR2/batch_"

run_one_batch_ref() {
  local batch_file="$1"
  local out_csv="${batch_file}.vina_ref.csv"
  docker run --rm -v "$(pwd)":/work -w /work "$VINA_IMG" bash -lc "\
    python3 src/scoring/docking_vina_runner.py \
      --smiles_file '$batch_file' \
      --out_csv '$out_csv' \
      --center $CX $CY $CZ \
      --size $SX $SY $SZ \
      --exhaustiveness $EXH_REF \
      --num_modes $NUM_MODES \
      --timeout_s $TIMEOUT_S \
      --work_dir runs/${RUN_ID}/docking/vina_refine\
  " >/dev/null
}
export -f run_one_batch_ref
export EXH_REF

parallel -j "$JOBS" run_one_batch_ref ::: "$SPLIT_DIR2"/batch_*

python3 src/scoring/merge_csv.py --glob "$SPLIT_DIR2/batch_*.vina_ref.csv" --out "runs/${RUN_ID}/docking/vina_refine.csv"
log "DOCK_VINA_REFINE_DONE" "docking" "Vina refine docking done" "{\"out\":\"runs/${RUN_ID}/docking/vina_refine.csv\"}"

# GNINA stage is intentionally left for later integration.
