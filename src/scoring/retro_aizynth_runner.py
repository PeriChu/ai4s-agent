import argparse
import json


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('--smiles_file', required=True)
    ap.add_argument('--out_json', required=True)
    ap.add_argument('--stock', required=True)
    ap.add_argument('--max_steps', type=int, required=True)
    ap.add_argument('--time_limit_s', type=int, required=True)
    ap.add_argument('--topk_routes', type=int, default=1)
    args = ap.parse_args()

    # Placeholder runner: writes failure results for all smiles.
    # Replace with actual AiZynthFinder invocation inside the aizynth docker image.
    with open(args.smiles_file) as f:
        smiles = [ln.strip() for ln in f if ln.strip()]

    out = []
    for s in smiles:
        out.append({
            'smiles': s,
            'retro_success': False,
            'steps': None,
            'route_nodes': [],
            'status': 'fail',
            'error': 'retro_not_implemented',
        })

    with open(args.out_json, 'w') as w:
        json.dump(out, w, ensure_ascii=False, indent=2)


if __name__ == '__main__':
    main()
