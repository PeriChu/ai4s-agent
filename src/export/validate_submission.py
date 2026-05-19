import argparse
import pandas as pd
from rdkit import Chem


def canonicalize(smiles: str) -> str | None:
    m = Chem.MolFromSmiles(smiles)
    if m is None:
        return None
    return Chem.MolToSmiles(m, canonical=True, isomericSmiles=True)


def validate_step(step: str) -> tuple[bool, str]:
    if '>>' not in step:
        return False, 'missing_>>'
    left, prod = step.split('>>', 1)
    left = left.strip(); prod = prod.strip()
    if not prod:
        return False, 'empty_product'
    if canonicalize(prod) is None:
        return False, 'invalid_product_smiles'
    # reactants can be empty (not expected) but allow; if present must parse
    if left:
        for r in left.split('.'):
            r = r.strip()
            if not r:
                continue
            if canonicalize(r) is None:
                return False, 'invalid_reactant_smiles'
    return True, ''


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('--csv', required=True)
    ap.add_argument('--expected_n', type=int, required=True)
    args = ap.parse_args()

    df = pd.read_csv(args.csv)
    if list(df.columns) != ['mol_smiles', 'route']:
        raise SystemExit(f'CSV columns must be mol_smiles,route. Got: {list(df.columns)}')

    if len(df) != args.expected_n:
        raise SystemExit(f'Expected {args.expected_n} rows, got {len(df)}')

    seen = set()
    for i, row in df.iterrows():
        ms = str(row['mol_smiles']).strip()
        rt = str(row['route']).strip()
        cms = canonicalize(ms)
        if cms is None:
            raise SystemExit(f'Row {i}: invalid mol_smiles')
        if cms in seen:
            raise SystemExit(f'Row {i}: duplicate mol_smiles after canonicalization')
        seen.add(cms)

        steps = [s.strip() for s in rt.split(',') if s.strip()]
        if not steps:
            raise SystemExit(f'Row {i}: empty route')
        for st in steps:
            ok, err = validate_step(st)
            if not ok:
                raise SystemExit(f'Row {i}: invalid step: {err}: {st}')
        # last product must equal mol_smiles
        last_prod = steps[-1].split('>>', 1)[1].strip()
        if canonicalize(last_prod) != cms:
            raise SystemExit(f'Row {i}: last product does not match mol_smiles')

    print('validate_submission: OK')


if __name__ == '__main__':
    main()
