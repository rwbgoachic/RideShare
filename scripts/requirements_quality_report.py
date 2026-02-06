import json
from pathlib import Path

REQ = Path("AgentInput/Requirements/requirements.jsonl")
OUT = Path("AgentInput/requirements_quality_report.md")

def main():
    if not REQ.exists():
        raise SystemExit(f"Missing: {REQ}")

    reqs = []
    for line in REQ.read_text(encoding="utf-8", errors="replace").splitlines():
        line = line.strip()
        if not line:
            continue
        reqs.append(json.loads(line))

    missing = [r for r in reqs if r.get("missing_acceptance_criteria") or not r.get("acceptance_criteria")]
    total = len(reqs)

    md = []
    md.append("# Requirements Quality Report")
    md.append("")
    md.append(f"- Total requirements: {total}")
    md.append(f"- Missing acceptance criteria (Given/When/Then): {len(missing)}")
    md.append("")
    if missing:
        md.append("## Missing acceptance criteria list")
        for r in missing:
            md.append(f"- {r.get('requirement_id')} — {r.get('title')}")
        md.append("")
        md.append("### Instruction to agent")
        md.append("For each item above: add Proposed Given/When/Then in requirements_status.jsonl and set needs_acceptance=true.")
    else:
        md.append("All requirements include acceptance criteria.")

    OUT.write_text("\n".join(md) + "\n", encoding="utf-8")
    print(f"Wrote: {OUT}")

if __name__ == "__main__":
    main()
