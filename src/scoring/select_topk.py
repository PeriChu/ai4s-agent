import argparse
import pandas as pd

def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('--in_csv', required=True)
    ap.add_argument('--score_col', required=True)
    ap.add_argument('--mode', choices=['min','max'], required=True)
    ap.add_argument('--topk', type=int, required=True)
    ap.add_argument('--out_smi', required=True)
    args = ap.parse_args()

    df = pd.read_csv(args.in_csv)
    df = df[df.get('status', 'ok') == 'ok'] if 'status' in df.columns else df
    df = df.dropna(subset=[args.score_col])

    asc = True if args.mode == 'min' else False
    df = df.sort_values(args.score_col, ascending=asc).head(args.topk)

    with open(args.out_smi, 'w') as w:
        for s in df['smiles'].astype(str).tolist():
            w.write(s.strip() + '\n')

if __name__ == '__main__':
    main()
