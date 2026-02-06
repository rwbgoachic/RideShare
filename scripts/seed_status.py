import json, re
from pathlib import Path

ROOT = Path(".").resolve()
REQ_JSONL = ROOT / "AgentInput" / "requirements.jsonl"
ASIS_JSON = ROOT / "AgentInput" / "as_is_scan.json"

OUT_SEED_JSONL = ROOT / "AgentInput" / "requirements_status_seed.jsonl"
OUT_SEED_MD    = ROOT / "AgentInput" / "requirements_status_seed.md"

STOP = set("""
a an and are as at be but by for from has have if in into is it its of on or our so that the then this to was were when where will with without
""".split())

def load_jsonl(p: Path):
    out = []
    for line in p.read_text(encoding="utf-8", errors="replace").splitlines():
        line = line.strip()
        if not line:
            continue
        out.append(json.loads(line))
    return out

def tokenize(text: str):
    text = text.lower()
    words = re.findall(r"[a-z0-9][a-z0-9\-\_]{2,}", text)
    words = [w for w in words if w not in STOP]
    return words

def best_keywords(req):
    blob = (req.get("title","") + "\n" + req.get("description",""))[:5000]
    toks = tokenize(blob)
    # simple frequency
    freq = {}
    for t in toks:
        freq[t] = freq.get(t, 0) + 1
    kws = sorted(freq.items(), key=lambda x: (-x[1], x[0]))
    return [k for k,_ in kws[:10]]

def search_evidence(repo_root: Path, keywords):
    hits = []
    # Search within common code/config extensions only
    exts = {".ts",".tsx",".js",".jsx",".md",".json",".yml",".yaml",".sql",".prisma"}
    skip = {"node_modules",".git",".next","dist","build","out",".turbo",".cache","coverage"}
    for p in repo_root.rglob("*"):
        if p.is_dir():
            continue
        if any(part in skip for part in p.parts):
            continue
        if p.suffix.lower() not in exts:
            continue
        try:
            txt = p.read_text(encoding="utf-8", errors="replace").lower()
        except Exception:
            continue
        score = 0
        for k in keywords:
            if k in txt:
                score += 1
        if score > 0:
            hits.append((score, str(p.relative_to(repo_root)).replace("\\","/")))
    hits.sort(reverse=True)
    return [h[1] for h in hits[:6]]

def main():
    if not REQ_JSONL.exists():
        raise SystemExit(f"Missing requirements.jsonl: {REQ_JSONL}")
    reqs = load_jsonl(REQ_JSONL)

    # repo root is parent of AgentInput
    repo_root = ROOT

    out_lines = []
    md = []
    md.append("# Requirements Status Seed (auto-generated; agent must refine semantically)")
    md.append("")
    md.append("Legend: NOT_STARTED / IN_PROGRESS (evidence found) — this is a *seed*, not final proof.")
    md.append("")

    for r in reqs:
        kws = best_keywords(r)
        evidence = search_evidence(repo_root, kws)
        status = "IN_PROGRESS" if evidence else "NOT_STARTED"
        rec = {
            "requirement_id": r.get("requirement_id"),
            "title": r.get("title"),
            "seed_status": status,
            "keywords": kws,
            "evidence_paths": evidence,
            "missing_acceptance_criteria": bool(r.get("missing_acceptance_criteria"))
        }
        out_lines.append(json.dumps(rec, ensure_ascii=False))

        md.append(f"## {r.get('requirement_id')} — {r.get('title')}")
        md.append(f"- Seed status: **{status}**")
        md.append(f"- Keywords: {', '.join(kws)}")
        if r.get("missing_acceptance_criteria"):
            md.append(f"- Acceptance criteria: **MISSING (agent should add Given/When/Then)**")
        if evidence:
            md.append("- Evidence:")
            for e in evidence:
                md.append(f"  - {e}")
        else:
            md.append("- Evidence: (none found by keyword scan)")
        md.append("")

    OUT_SEED_JSONL.write_text("\n".join(out_lines) + "\n", encoding="utf-8")
    OUT_SEED_MD.write_text("\n".join(md) + "\n", encoding="utf-8")
    print(f"Wrote: {OUT_SEED_JSONL}")
    print(f"Wrote: {OUT_SEED_MD}")

if __name__ == "__main__":
    main()
