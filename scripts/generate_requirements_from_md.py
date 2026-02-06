import json, re
from pathlib import Path

CANONICAL = Path(r".\Requirements\BlackRavenia_RideShare_Canonical_Requirements_v6_1.md")
OUT_JSONL = Path(r".\Requirements\requirements.jsonl")
OUT_JSON  = Path(r".\Requirements\requirements.json")

def strip_code_fences(text: str) -> str:
    # Remove fenced code blocks ```...```
    return re.sub(r"```.*?```", "", text, flags=re.S)

def norm_ws(s: str) -> str:
    s = s.replace("\r\n", "\n")
    s = re.sub(r"[ \t]+$", "", s, flags=re.M)
    return s.strip()

def parse_sections(md: str):
    # Capture ## / ### / #### headings and their bodies
    # We treat each "### x.y Title" as a requirement unit (primary granularity).
    heading_re = re.compile(r"^(#{2,4})\s+(.+?)\s*$", re.M)

    hits = list(heading_re.finditer(md))
    sections = []

    for idx, m in enumerate(hits):
        level = len(m.group(1))
        title = m.group(2).strip()
        start = m.end()

        end = hits[idx+1].start() if idx+1 < len(hits) else len(md)
        body = md[start:end]

        sections.append({"level": level, "title": title, "body": body})
    return sections

def extract_numbered_prefix(title: str):
    # Titles like: "1.2 Definition of Done (DoD) ..."
    m = re.match(r"^(\d+(\.\d+)+)\s+(.*)$", title)
    if m:
        return m.group(1), m.group(3).strip()
    return None, title

def extract_acceptance(body: str):
    # Heuristics:
    # 1) If there's an "Acceptance:" label, capture bullets after it until blank line or next bold header.
    # 2) Otherwise capture explicit Given/When/Then lines if present.
    lines = [ln.rstrip() for ln in body.splitlines()]
    acc = []

    # Find "Acceptance:" marker
    acc_idx = None
    for i, ln in enumerate(lines):
        if re.search(r"\bAcceptance\b\s*:", ln, flags=re.I):
            acc_idx = i
            break

    if acc_idx is not None:
        for j in range(acc_idx+1, len(lines)):
            t = lines[j].strip()
            if not t:
                if acc:
                    break
                continue
            # stop on a new bold section label like **Evidence gates**
            if re.match(r"^\*\*.+\*\*\s*:?\s*$", t):
                break
            if t.startswith("- ") or t.startswith("* "):
                acc.append(t[2:].strip())
            elif re.match(r"^(Given|When|Then)\b", t, flags=re.I):
                acc.append(t)
        if acc:
            return acc

    # Given/When/Then anywhere
    for ln in lines:
        t = ln.strip()
        if re.match(r"^(Given|When|Then)\b", t, flags=re.I):
            acc.append(t)
    return acc

def main():
    if not CANONICAL.exists():
        raise SystemExit(f"Canonical requirements file not found: {CANONICAL}")

    md = CANONICAL.read_text(encoding="utf-8", errors="replace")
    md = strip_code_fences(md)

    secs = parse_sections(md)

    # Build requirements from level 3 headings (###) primarily.
    reqs = []
    for s in secs:
        if s["level"] != 3:
            continue

        num, clean_title = extract_numbered_prefix(s["title"])
        body = norm_ws(s["body"])
        acceptance = extract_acceptance(body)

        req_id = f"BRRS-{num}" if num else f"BRRS-{len(reqs)+1:04d}"

        reqs.append({
            "requirement_id": req_id,
            "section_number": num,
            "title": clean_title,
            "description": body,
            "acceptance_criteria": acceptance,
            "missing_acceptance_criteria": (len(acceptance) == 0),
            "source_file": str(CANONICAL).replace("\\", "/")
        })

    if not reqs:
        raise SystemExit("Parsed 0 requirements. Expected '###' headings in the markdown.")

    # Write JSONL + JSON
    OUT_JSONL.write_text("\n".join(json.dumps(r, ensure_ascii=False) for r in reqs) + "\n", encoding="utf-8")
    OUT_JSON.write_text(json.dumps(reqs, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")

    print(f"Wrote JavaScript Object Notation Lines (JSONL): {OUT_JSONL}  (count={len(reqs)})")
    print(f"Wrote JavaScript Object Notation (JSON):       {OUT_JSON}   (count={len(reqs)})")

if __name__ == "__main__":
    main()
