import json, re
from pathlib import Path

ROOT = Path(".").resolve()
REQ_MD = ROOT / "Requirements" / "BlackRavenia_RideShare_Canonical_Requirements_v6_1.md"
ASIS  = ROOT / "AgentInput" / "as_is_scan.json"
OUT   = ROOT / "AgentInput" / "implemented_not_documented_candidates.md"

def main():
    req_text = ""
    if REQ_MD.exists():
        req_text = REQ_MD.read_text(encoding="utf-8", errors="replace").lower()

    inv = json.loads(ASIS.read_text(encoding="utf-8", errors="replace"))
    endpoints = inv.get("endpoints", [])
    pkgs = inv.get("packages", [])

    lines = []
    lines.append("# Implemented-But-Not-Documented (Candidates)")
    lines.append("")
    lines.append("This is a *candidate list* for the agentic Artificial Intelligence (AI) to validate semantically.")
    lines.append("")

    # Candidate signals: uncommon package names/scripts + explicit endpoint paths
    lines.append("## Endpoints not mentioned in requirements text (string match only)")
    c = 0
    for e in endpoints:
        p = str(e.get("path","")).lower()
        if p and p not in req_text:
            lines.append(f"- {e.get('method')} {e.get('path')}  ({e.get('file')})")
            c += 1
            if c >= 100:
                lines.append("- ... (truncated at 100)")
                break
    if c == 0:
        lines.append("- (none detected by string match)")

    lines.append("")
    lines.append("## Package scripts / dependencies not mentioned in requirements text (string match only)")
    shown = 0
    for pj in pkgs:
        name = (pj.get("name") or "").lower()
        if name and name not in req_text:
            lines.append(f"- package: {pj.get('path')}  name={pj.get('name')}")
            shown += 1
            if shown >= 40:
                lines.append("- ... (truncated at 40)")
                break

    OUT.write_text("\n".join(lines) + "\n", encoding="utf-8")
    print(f"Wrote: {OUT}")

if __name__ == "__main__":
    main()
