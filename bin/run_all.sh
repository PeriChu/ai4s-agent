#!/usr/bin/env bash
set -euo pipefail

RUN_ID="${RUN_ID:-$(date -u +'%Y-%m-%d_%H-%M-%S')}"
export RUN_ID
export LOG_JSONL="runs/${RUN_ID}/logs.jsonl"

mkdir -p "runs/${RUN_ID}" "runs/${RUN_ID}/intermediates"

# 1) pocket (fpocket -> pocket.json)
bash bin/make_pocket_from_fpocket.sh data/target.pdb data/pocket.json 5.0 18.0

# 2) generator placeholder (MVP): user should replace with RL/graph/3D generators.
# For now, expects a file at data/seed_smiles.smi (one SMILES per line).
python3 src/chemistry/standardize.py \
  --in_smi data/seed_smiles.smi \
  --out_smi runs/${RUN_ID}/intermediates/candidates_canon.smi

# 3) docking
bash bin/run_docking_batch.sh configs/docking.yaml runs/${RUN_ID}/intermediates/candidates_canon.smi

# 4) select top for retro
python3 src/scoring/select_for_retro.py \
  --vina_csv runs/${RUN_ID}/docking/vina_refine.csv \
  --topk 3000 \
  --out_smi runs/${RUN_ID}/intermediates/top_for_retro.smi

# 5) retro
bash bin/run_retro_batch.sh configs/retro.yaml runs/${RUN_ID}/intermediates/top_for_retro.smi

# 6) final selection & export 200
python3 src/export/to_csv.py \
  --run_dir runs/${RUN_ID} \
  --selection_cfg configs/selection.yaml \
  --out_csv runs/${RUN_ID}/result.csv

python3 src/export/validate_submission.py \
  --csv runs/${RUN_ID}/result.csv \
  --expected_n 200

cp runs/${RUN_ID}/logs.jsonl runs/${RUN_ID}/result.log

echo "Done: runs/${RUN_ID}/result.csv and runs/${RUN_ID}/result.log"
