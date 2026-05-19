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


def format_route(route_nodes) -> str:
    # route_nodes expected: list of dicts with 'reaction_smiles' OR reactants/product.
    steps = []
    for node in route_nodes:
        rxn = node.get('reaction_smiles')
        if rxn and '>>' in rxn:
            left, right = rxn.split('>>', 1)
            left = left.replace(' ', '')
            right = right.replace(' ', '')
            steps.append(f"{left}>>{right}")
        else:
            reactants = node.get('reactants', [])
            product = node.get('product', '')
            steps.append(f"{'.'.join(reactants)}>>{product}")
    return ','.join(steps)


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('--retro_json', required=True)
    ap.add_argument('--out_csv', required=True)
    args = ap.parse_args()

    with open(args.retro_json) as f:
        data = json.load(f)

    rows = []
    for rec in data:
        s = rec.get('smiles', '')
        cs = canonicalize(s)
        if not cs:
            continue
        route = format_route(rec.get('route_nodes', []))
        rows.append({'smiles': cs, 'route': route, 'retro_success': bool(rec.get('retro_success', False))})

    df = pd.DataFrame(rows)
    df.to_csv(args.out_csv, index=False)


if __name__ == '__main__':
    main()
