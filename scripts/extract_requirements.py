import argparse, json, re, sys
from pathlib import Path

def find_marker(lines):
    for i, line in enumerate(lines):
        if re.search(r"MACHINE_READABLE_JSONL", line, re.IGNORECASE):
            return i
    return -1

def extract_jsonl(lines, start_idx):
    out = []
    for j in range(start_idx + 1, len(lines)):
        t = lines[j].strip()

        # stop if we hit another major section marker
        if re.match(r"^(HUMAN_READABLE_TXT|MACHINE_READABLE_JSONL)\b", t, re.IGNORECASE) and j > start_idx + 1:
            break

        if not t:
            continue
        if t.startswith("```"):
            continue

        # keep only single-line JSON objects
        if t.startswith("{") and t.endswith("}"):
            out.append(lines[j].rstrip("\n"))
    return out

def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--input-md", required=True)
    ap.add_argument("--out-jsonl", required=True)
    ap.add_argument("--out-json", required=True)
    args = ap.parse_args()

    inp = Path(args.input_md)
    if not inp.exists():
        raise SystemExit(f"Input file not found: {inp}")

    lines = inp.read_text(encoding="utf-8", errors="replace").splitlines(True)
    si = find_marker(lines)
    if si < 0:
        # helpful debug: show the top of file
        preview = "".join(lines[:80])
        raise SystemExit(
            "Could not find MACHINE_READABLE_JSONL marker in the markdown.\n"
            "Top-of-file preview (first ~80 lines):\n"
            + preview
        )

    jsonl_lines = extract_jsonl(lines, si)
    if not jsonl_lines:
        raise SystemExit(
            "Found MACHINE_READABLE_JSONL marker, but extracted 0 JSONL records.\n"
            "Your MACHINE_READABLE_JSONL section must contain lines like: { ... } (one JSON object per line)."
        )

    objs = []
    for idx, l in enumerate(jsonl_lines, start=1):
        try:
            objs.append(json.loads(l))
        except Exception as e:
            raise SystemExit(f"Invalid JSON on JSONL line #{idx}: {e}\nLINE: {l}")

    Path(args.out_jsonl).write_text("\n".join(jsonl_lines) + "\n", encoding="utf-8")
    Path(args.out_json).write_text(json.dumps(objs, indent=2), encoding="utf-8")

    print(f"Wrote JavaScript Object Notation Lines (JSONL): {args.out_jsonl}")
    print(f"Wrote JavaScript Object Notation (JSON):       {args.out_json}")

if __name__ == "__main__":
    main()
