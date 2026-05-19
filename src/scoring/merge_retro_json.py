import argparse
import glob
import json


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('--glob', required=True)
    ap.add_argument('--out', required=True)
    args = ap.parse_args()

    files = sorted(glob.glob(args.glob))
    if not files:
        raise SystemExit(f'No files match glob: {args.glob}')

    merged = []
    for f in files:
        with open(f) as r:
            data = json.load(r)
            if isinstance(data, list):
                merged.extend(data)
            else:
                merged.append(data)

    with open(args.out, 'w') as w:
        json.dump(merged, w, ensure_ascii=False, indent=2)


if __name__ == '__main__':
    main()
