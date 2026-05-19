import argparse
import json
import os
import time
from dataclasses import dataclass

import pandas as pd
from rdkit import Chem

try:
    from meeko import MoleculePreparation
except Exception as e:  # pragma: no cover
    MoleculePreparation = None


def utc_ts() -> str:
    return time.strftime('%Y-%m-%dT%H:%M:%SZ', time.gmtime())


def log_event(event: str, stage: str, msg: str, extra: dict):
    run_id = os.environ.get('RUN_ID', 'manual')
    log_path = os.environ.get('LOG_JSONL')
    if not log_path:
        return
    rec = {
        'ts': utc_ts(),
        'run_id': run_id,
        'event': event,
        'stage': stage,
        'level': 'INFO',
        'msg': msg,
        'extra': extra,
    }
    os.makedirs(os.path.dirname(log_path), exist_ok=True)
    with open(log_path, 'a') as w:
        w.write(json.dumps(rec, ensure_ascii=False) + '\n')


@dataclass
class DockResult:
    smiles: str
    vina_score: float | None
    pose_path: str
    status: str
    error: str


def canonicalize(smiles: str) -> str | None:
    m = Chem.MolFromSmiles(smiles)
    if m is None:
        return None
    return Chem.MolToSmiles(m, canonical=True, isomericSmiles=True)


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('--smiles_file', required=True)
    ap.add_argument('--out_csv', required=True)
    ap.add_argument('--center', nargs=3, type=float, required=True)
    ap.add_argument('--size', nargs=3, type=float, required=True)
    ap.add_argument('--exhaustiveness', type=int, required=True)
    ap.add_argument('--num_modes', type=int, default=10)
    ap.add_argument('--timeout_s', type=int, default=60)
    ap.add_argument('--work_dir', required=True)
    args = ap.parse_args()

    if MoleculePreparation is None:
        raise SystemExit('meeko is required in the vina docker image (pip install meeko).')

    os.makedirs(args.work_dir, exist_ok=True)
    poses_dir = os.path.join(args.work_dir, 'poses')
    os.makedirs(poses_dir, exist_ok=True)

    with open(args.smiles_file) as f:
        raw = [ln.strip() for ln in f if ln.strip()]

    log_event('DOCK_VINA_BATCH_START', 'docking', 'Vina batch start', {
        'smiles_file': args.smiles_file,
        'n_in': len(raw),
        'exhaustiveness': args.exhaustiveness,
        'center': args.center,
        'size': args.size,
        'timeout_s': args.timeout_s,
    })

    t0 = time.time()
    results: list[DockResult] = []

    # NOTE: This is a placeholder implementation.
    # It does NOT actually invoke vina yet; it only validates SMILES and writes fail entries.
    # You should replace this with actual vina invocation inside the vina docker image.
    for s in raw:
        cs = canonicalize(s)
        if cs is None:
            results.append(DockResult(smiles=s, vina_score=None, pose_path='', status='fail', error='invalid_smiles'))
            continue
        results.append(DockResult(smiles=cs, vina_score=None, pose_path='', status='fail', error='vina_not_implemented'))

    elapsed = time.time() - t0
    df = pd.DataFrame([r.__dict__ for r in results])
    df.to_csv(args.out_csv, index=False)

    log_event('DOCK_VINA_BATCH_DONE', 'docking', 'Vina batch done', {
        'out_csv': args.out_csv,
        'n_ok': int((df['status'] == 'ok').sum()),
        'n_fail': int((df['status'] != 'ok').sum()),
        'elapsed_s': elapsed,
    })


if __name__ == '__main__':
    main()
