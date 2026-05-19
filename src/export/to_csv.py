import argparse
import json
import os
import pandas as pd

from rdkit import Chem


def canonicalize(smiles: str) -> str | None:
    m = Chem.MolFromSmiles(smiles)
    if m is None:
        return None
    return Chem.MolToSmiles(m, canonical=True, isomericSmiles=True)


def score_row(row: dict, weights: dict) -> float:
    # Higher is better
    score = 0.0
    vina = row.get('vina_score')
    if vina is not None and pd.notna(vina):
        score += weights.get('vina', 1.0) * (-float(vina))
    gnina = row.get('gnina_cnn_score')
    if gnina is not None and pd.notna(gnina):
        score += weights.get('gnina', 0.0) * float(gnina)

    if row.get('retro_success'):
        score += weights.get('synth_success', 0.0)

    steps = row.get('steps')
    if steps is not None and pd.notna(steps):
        score -= weights.get('steps_penalty', 0.0) * float(steps)

    return score


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('--run_dir', required=True)
    ap.add_argument('--selection_cfg', required=True)
    ap.add_argument('--out_csv', required=True)
    args = ap.parse_args()

    with open(args.selection_cfg) as f:
        cfg = json.loads(json.dumps(__import__('yaml').safe_load(f)))

    export_n = int(cfg['selection']['export_n'])
    weights = cfg['selection']['weights']

    vina_csv = os.path.join(args.run_dir, 'docking', 'vina_refine.csv')
    retro_json = os.path.join(args.run_dir, 'retro', 'retro_merged.json')

    df_vina = pd.read_csv(vina_csv) if os.path.exists(vina_csv) else pd.DataFrame()

    # Retro: convert json list to df
    retro = []
    if os.path.exists(retro_json):
        with open(retro_json) as f:
            data = json.load(f)
        for r in data:
            retro.append({
                'smiles': r.get('smiles'),
                'retro_success': bool(r.get('retro_success', False)),
                'steps': r.get('steps'),
                'route_nodes': r.get('route_nodes', []),
            })
    df_retro = pd.DataFrame(retro)

    if not df_vina.empty:
        df = df_vina
    else:
        df = pd.DataFrame(columns=['smiles','vina_score','status','error'])

    if not df_retro.empty:
        df = df.merge(df_retro[['smiles','retro_success','steps','route_nodes']], on='smiles', how='left')
    else:
        df['retro_success'] = False
        df['steps'] = None
        df['route_nodes'] = [[] for _ in range(len(df))]

    # canonicalize and drop invalid
    df['smiles'] = df['smiles'].astype(str)
    df['smiles'] = df['smiles'].map(lambda s: canonicalize(s) or '')
    df = df[df['smiles'] != '']

    # route formatting
    from src.export.route_format import format_route
    df['route'] = df['route_nodes'].map(format_route)

    # filter (require retro success)
    if cfg['selection']['constraints'].get('require_retro_success', True):
        df = df[df['retro_success'] == True]

    # score
    df['final_score'] = df.apply(lambda r: score_row(r.to_dict(), weights), axis=1)
    df = df.sort_values('final_score', ascending=False)

    # de-dup by smiles
    df = df.drop_duplicates('smiles', keep='first')

    out = df[['smiles','route']].head(export_n).copy()
    out.columns = ['mol_smiles', 'route']

    os.makedirs(os.path.dirname(args.out_csv), exist_ok=True)
    out.to_csv(args.out_csv, index=False)


if __name__ == '__main__':
    main()
