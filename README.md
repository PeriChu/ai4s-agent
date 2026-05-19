```
AI4S Agent Bootstrap (MVP)

This branch scaffolds an AI4S Task2 pipeline with:
- pocket detection (fpocket -> pocket.json)
- docking batch runner (Vina runner placeholder; to be implemented)
- retrosynthesis runner (AiZynthFinder placeholder; to be implemented)
- exporter that writes result.csv and validates route format
- pure JSONL logs

## Quick start

Prereqs on host:
- Linux
- docker
- GNU parallel
- yq, jq
- fpocket

Data:
- data/target.pdb (provided by contest)
- data/seed_smiles.smi (temporary seed list; replace with generators)

Run:

```bash
bash bin/run_all.sh
```

Outputs:
- runs/<RUN_ID>/result.csv
- runs/<RUN_ID>/result.log (JSONL)

## Notes
- `src/scoring/docking_vina_runner.py` and `src/scoring/retro_aizynth_runner.py` are placeholders.
  Replace with real implementations inside your docker images.

```
