import argparse
import pandas as pd

def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('--vina_csv', required=True)
    ap.add_argument('--topk', type=int, required=True)
    ap.add_argument('--out_smi', required=True)
    args = ap.parse_args()

    df = pd.read_csv(args.vina_csv)
    if 'status' in df.columns:
        df = df[df['status'] == 'ok']
    df = df.dropna(subset=['vina_score'])
    df = df.sort_values('vina_score', ascending=True).head(args.topk)

    with open(args.out_smi, 'w') as w:
        for s in df['smiles'].astype(str).tolist():
            w.write(s.strip() + '\n')

if __name__ == '__main__':
    main()
