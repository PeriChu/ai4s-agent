#!/usr/bin/env bash
set -euo pipefail

PDB="${1:-data/target.pdb}"
OUT_JSON="${2:-data/pocket.json}"
MARGIN="${3:-5.0}"
MIN_SIZE="${4:-18.0}"

RUN_ID="${RUN_ID:-manual}"
LOG_JSONL="${LOG_JSONL:-runs/${RUN_ID}/logs.jsonl}"

mkdir -p "$(dirname "$OUT_JSON")"
mkdir -p "runs/${RUN_ID}/pocket"

ts() { date -u +"%Y-%m-%dT%H:%M:%SZ"; }
log() {
  local event="$1"; local stage="$2"; local msg="$3"; local extra="${4:-{}}"
  printf '{"ts":"%s","run_id":"%s","event":"%s","stage":"%s","level":"INFO","msg":%s,"extra":%s}\n' \
    "$(ts)" "$RUN_ID" "$event" "$stage" "$(python3 - <<PY
import json; print(json.dumps("$msg"))
PY)" "$extra" >> "$LOG_JSONL"
}

log "POCKET_FP_START" "pocket" "Running fpocket" "{\"pdb\":\"$PDB\"}"

# Run fpocket in an isolated directory for reliable outputs.
WORK_DIR="runs/${RUN_ID}/pocket/fpocket_work"
rm -rf "$WORK_DIR"; mkdir -p "$WORK_DIR"
cp "$PDB" "$WORK_DIR/target.pdb"
pushd "$WORK_DIR" >/dev/null
fpocket -f target.pdb > fpocket.stdout 2> fpocket.stderr || true
POCKET_ATM="$(ls -t *pockets*_atm.pdb 2>/dev/null | head -n 1 || true)"
popd >/dev/null

if [[ -z "$POCKET_ATM" ]]; then
  log "POCKET_FP_FAIL" "pocket" "fpocket pocket atm file not found" "{}"
  exit 2
fi

POCKET_ATM_PATH="$WORK_DIR/$POCKET_ATM"

python3 - "$POCKET_ATM_PATH" "$OUT_JSON" "$MARGIN" "$MIN_SIZE" <<'PY'
import json, sys
pdb = sys.argv[1]
out = sys.argv[2]
margin = float(sys.argv[3])
min_size = float(sys.argv[4])

xs=[]; ys=[]; zs=[]
with open(pdb) as f:
    for line in f:
        if line.startswith(("ATOM","HETATM")):
            xs.append(float(line[30:38])); ys.append(float(line[38:46])); zs.append(float(line[46:54]))
if not xs:
    raise SystemExit("no atoms in pocket pdb")

mnx,mxx=min(xs),max(xs)
mny,mxy=min(ys),max(ys)
mnz,mxz=min(zs),max(zs)

cx=(mnx+mxx)/2; cy=(mny+mxy)/2; cz=(mnz+mxz)/2
sx=(mxx-mnx)+2*margin
sy=(mxy-mny)+2*margin
sz=(mxz-mnz)+2*margin
sx=max(sx,min_size); sy=max(sy,min_size); sz=max(sz,min_size)

data={
  "center_x":cx,"center_y":cy,"center_z":cz,
  "size_x":sx,"size_y":sy,"size_z":sz,
  "source":{
    "method":"fpocket",
    "pocket_file":pdb,
    "margin_A":margin,
    "min_size_A":min_size
  }
}
with open(out,"w") as w:
    json.dump(data,w,indent=2)
print(out)
PY

log "POCKET_FP_DONE" "pocket" "Pocket box written" "{\"out_json\":\"$OUT_JSON\",\"pocket_atm\":\"$POCKET_ATM_PATH\"}"
