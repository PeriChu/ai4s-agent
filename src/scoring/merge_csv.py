import argparse
import glob
import pandas as pd

def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('--glob', required=True)
    ap.add_argument('--out', required=True)
    args = ap.parse_args()

    files = sorted(glob.glob(args.glob))
    if not files:
        raise SystemExit(f'No files match glob: {args.glob}')

    dfs = []
    for f in files:
        df = pd.read_csv(f)
        dfs.append(df)

    merged = pd.concat(dfs, ignore_index=True)

    # De-duplicate by smiles: keep best (min vina_score) if present
    if 'smiles' in merged.columns:
        if 'vina_score' in merged.columns:
            merged = merged.sort_values('vina_score', ascending=True).drop_duplicates('smiles', keep='first')
        else:
            merged = merged.drop_duplicates('smiles', keep='first')

    merged.to_csv(args.out, index=False)

if __name__ == '__main__':
    main()
