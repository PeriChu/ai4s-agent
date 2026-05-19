import argparse
import os
from rdkit import Chem


def canonicalize(smiles: str) -> str | None:
    m = Chem.MolFromSmiles(smiles)
    if m is None:
        return None
    return Chem.MolToSmiles(m, canonical=True, isomericSmiles=True)


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('--in_smi', required=True)
    ap.add_argument('--out_smi', required=True)
    args = ap.parse_args()

    os.makedirs(os.path.dirname(args.out_smi), exist_ok=True) if os.path.dirname(args.out_smi) else None

    seen = set()
    n_in = 0
    n_ok = 0
    with open(args.in_smi) as r, open(args.out_smi, 'w') as w:
        for line in r:
            s = line.strip()
            if not s:
                continue
            n_in += 1
            cs = canonicalize(s)
            if cs is None:
                continue
            if cs in seen:
                continue
            seen.add(cs)
            w.write(cs + '\n')
            n_ok += 1

    print(f'standardize: in={n_in} ok={n_ok} out={args.out_smi}')


if __name__ == '__main__':
    main()
