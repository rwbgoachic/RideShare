import json
from pathlib import Path

OUT_JSONL = Path("AgentOutput/requirements_status.jsonl")
OUT_MD    = Path("AgentOutput/requirements_status.md")
OUT_UNDOC = Path("AgentOutput/implemented_not_documented.md")

REQUIRED_TOP_KEYS = {"requirement_id","title","status","evidence","gaps","proposed_work","needs_acceptance","proposed_acceptance_criteria"}
VALID_STATUS = {"NOT_STARTED","IN_PROGRESS","IMPLEMENTED","TESTED","BLOCKED"}

def main():
    missing_files = [p for p in [OUT_JSONL, OUT_MD, OUT_UNDOC] if not p.exists()]
    if missing_files:
        raise SystemExit("Missing expected agent outputs:\n" + "\n".join(str(p) for p in missing_files))

    bad = []
    lines = OUT_JSONL.read_text(encoding="utf-8", errors="replace").splitlines()
    for i, line in enumerate(lines, start=1):
        if not line.strip():
            continue
        try:
            obj = json.loads(line)
        except Exception as e:
            bad.append((i, f"Invalid JSON: {e}"))
            continue

        missing = REQUIRED_TOP_KEYS - set(obj.keys())
        if missing:
            bad.append((i, f"Missing keys: {sorted(missing)}"))
        if obj.get("status") not in VALID_STATUS:
            bad.append((i, f"Invalid status: {obj.get('status')}"))
        if not isinstance(obj.get("evidence"), dict):
            bad.append((i, "evidence must be an object"))

    if bad:
        msg = "AgentOutput/requirements_status.jsonl failed validation:\n" + "\n".join([f"Line {i}: {m}" for i,m in bad[:20]])
        raise SystemExit(msg)

    print("OK: Agent outputs exist and requirements_status.jsonl is valid JSONL with expected schema.")

if __name__ == "__main__":
    main()
