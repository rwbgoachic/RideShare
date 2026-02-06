import os, re, json, hashlib
from pathlib import Path
from datetime import datetime
from typing import List, Dict, Any, Tuple, Optional

from openai import OpenAI

ROOT = Path.cwd()

SKIP_DIRS = {
  ".git","node_modules",".next","dist","build","out",".venv","venv","__pycache__",
  "coverage",".pytest_cache","AgentInput","AgentOutput"
}

def read_text(p: Path) -> str:
  return p.read_text(encoding="utf-8", errors="replace") if p.exists() else ""

def write_text(p: Path, s: str) -> None:
  p.parent.mkdir(parents=True, exist_ok=True)
  p.write_text(s, encoding="utf-8")

def write_json(p: Path, obj: Any) -> None:
  write_text(p, json.dumps(obj, indent=2, ensure_ascii=False) + "\n")

def sha1(s: str) -> str:
  return hashlib.sha1(s.encode("utf-8", errors="ignore")).hexdigest()

def rel(p: Path) -> str:
  return str(p.relative_to(ROOT)).replace("\\","/")

def safe_read_file(p: Path) -> str:
  try:
    return p.read_text(encoding="utf-8", errors="replace")
  except Exception:
    return ""

# ---------------- Requirements parsing (from ### headings) ----------------
def find_canonical(req_dir: Path) -> Path:
  # Prefer the known name, else most-recent *Canonical_Requirements*.md
  exact = req_dir / "BlackRavenia_RideShare_Canonical_Requirements_v6_1.md"
  if exact.exists():
    return exact
  cands = sorted(req_dir.glob("*Canonical_Requirements*.md"), key=lambda p: p.stat().st_mtime, reverse=True)
  if not cands:
    raise SystemExit("Could not find canonical requirements markdown under Requirements/ (expected *Canonical_Requirements*.md).")
  return cands[0]

def extract_numbered_prefix(title: str) -> Tuple[Optional[str], str]:
  m = re.match(r"^(\d+(?:\.\d+)+)\s+(.*)$", title.strip())
  return (m.group(1), m.group(2).strip()) if m else (None, title.strip())

def extract_acceptance(body: str) -> List[str]:
  lines = [ln.rstrip() for ln in body.splitlines()]
  acc: List[str] = []
  acc_idx = None
  for i, ln in enumerate(lines):
    if re.search(r"\bAcceptance\b\s*:", ln, flags=re.I):
      acc_idx = i
      break
  if acc_idx is not None:
    for j in range(acc_idx+1, len(lines)):
      t = lines[j].strip()
      if not t:
        if acc: break
        continue
      if re.match(r"^\*\*.+\*\*\s*:?\s*$", t): break
      if t.startswith("- ") or t.startswith("* "):
        acc.append(t[2:].strip())
      elif re.match(r"^(Given|When|Then)\b", t, flags=re.I):
        acc.append(t)
    if acc:
      return acc
  for ln in lines:
    t = ln.strip()
    if re.match(r"^(Given|When|Then)\b", t, flags=re.I):
      acc.append(t)
  return acc

def parse_requirements(canonical_md: str, canonical_path: Path) -> List[Dict[str, Any]]:
  heading_re = re.compile(r"^###\s+(.+?)\s*$", re.M)
  hits = list(heading_re.finditer(canonical_md))
  if not hits:
    raise SystemExit("Parsed 0 requirements: expected '### ' headings in canonical requirements markdown.")
  reqs: List[Dict[str, Any]] = []
  for idx, m in enumerate(hits):
    title_raw = m.group(1).strip()
    start = m.end()
    end = hits[idx+1].start() if idx+1 < len(hits) else len(canonical_md)
    body = canonical_md[start:end].strip()

    sec_num, clean_title = extract_numbered_prefix(title_raw)
    rid = f"BRRS-{sec_num}" if sec_num else f"BRRS-{idx+1:04d}"

    desc = re.sub(r"\n{3,}", "\n\n", body).strip()
    acc = extract_acceptance(body)

    reqs.append({
      "requirement_id": rid,
      "section_number": sec_num,
      "title": clean_title,
      "description": desc,
      "acceptance_criteria": acc,
      "source_file": str(canonical_path).replace("\\","/"),
    })
  return reqs

# ---------------- Rich As-Is scan ----------------
ROUTE_PATTERNS = [
  re.compile(r"\brouter\.(get|post|put|patch|delete)\s*\(\s*['\"]([^'\"]+)['\"]", re.I),
  re.compile(r"\bapp\.(get|post|put|patch|delete)\s*\(\s*['\"]([^'\"]+)['\"]", re.I),
  re.compile(r"\bfastify\.(get|post|put|patch|delete)\s*\(\s*['\"]([^'\"]+)['\"]", re.I),
]

NEXT_ROUTE_METHOD_RE = re.compile(r"export\s+(?:async\s+)?function\s+(GET|POST|PUT|PATCH|DELETE)\b", re.I)

TEST_FILE_RE = re.compile(r"\.(test|spec)\.(ts|tsx|js|jsx|py)$", re.I)
TEST_NAME_RES = [
  re.compile(r"\bdescribe\s*\(\s*['\"](.+?)['\"]", re.I),
  re.compile(r"\b(it|test)\s*\(\s*['\"](.+?)['\"]", re.I),
]

CREATE_TABLE_RE = re.compile(r"create\s+table\s+(?:if\s+not\s+exists\s+)?([a-zA-Z0-9_\"\.]+)\s*\(", re.I)
ALTER_ADD_COL_RE = re.compile(r"alter\s+table\s+([a-zA-Z0-9_\"\.]+)\s+add\s+column\s+(?:if\s+not\s+exists\s+)?([a-zA-Z0-9_\"\.]+)\s+([a-zA-Z0-9_\"\[\]\(\)\.]+)", re.I)

def normalize_ident(x: str) -> str:
  x = x.strip().strip('"')
  return x

def scan_supabase_schema() -> Dict[str, Any]:
  schema: Dict[str, Any] = {"tables": {}}
  # Common Supabase path
  mig_dirs = [
    ROOT / "supabase" / "migrations",
    ROOT / "Supabase" / "migrations",
  ]
  mig_files: List[Path] = []
  for d in mig_dirs:
    if d.exists():
      mig_files += sorted(d.glob("*.sql"))
  # Also accept any */migrations/*.sql if repo differs
  if not mig_files:
    mig_files = sorted([p for p in ROOT.rglob("*.sql") if "migrations" in p.parts and not any(s in p.parts for s in SKIP_DIRS)])[:80]

  for mf in mig_files:
    txt = safe_read_file(mf)
    for m in CREATE_TABLE_RE.finditer(txt):
      tname = normalize_ident(m.group(1))
      schema["tables"].setdefault(tname, {"columns": {}, "sources": set()})
      schema["tables"][tname]["sources"].add(rel(mf))

    for m in ALTER_ADD_COL_RE.finditer(txt):
      tname = normalize_ident(m.group(1))
      col = normalize_ident(m.group(2))
      ctype = m.group(3).strip()
      schema["tables"].setdefault(tname, {"columns": {}, "sources": set()})
      schema["tables"][tname]["columns"][col] = ctype
      schema["tables"][tname]["sources"].add(rel(mf))

  # JSON-ify sets
  for t, v in list(schema["tables"].items()):
    v["sources"] = sorted(list(v["sources"]))
  schema["migration_files_scanned"] = [rel(p) for p in mig_files]
  return schema

def derive_next_api_path(route_file: Path) -> str:
  # app/api/foo/bar/route.ts -> /api/foo/bar
  r = rel(route_file)
  parts = r.split("/")
  try:
    idx = parts.index("api")
  except ValueError:
    return ""
  after = parts[idx+1:]
  # drop route.ts
  if after and after[-1].startswith("route."):
    after = after[:-1]
  # Next dynamic segments [id] -> :id
  after = [re.sub(r"^\[(.+?)\]$", r":\1", s) for s in after]
  return "/api/" + "/".join(after)

def collect_snippets(file_path: Path, patterns: List[re.Pattern], max_snips: int = 6, context: int = 6) -> List[Dict[str, Any]]:
  txt = safe_read_file(file_path)
  if not txt:
    return []
  lines = txt.splitlines()
  snips = []
  for pat in patterns:
    for m in pat.finditer(txt):
      # approximate line number
      line_no = txt[:m.start()].count("\n")
      lo = max(0, line_no - context)
      hi = min(len(lines), line_no + context + 1)
      snippet = "\n".join(lines[lo:hi])
      snips.append({
        "file": rel(file_path),
        "line_start": lo + 1,
        "line_end": hi,
        "pattern": pat.pattern,
        "snippet": snippet[:1200],
      })
      if len(snips) >= max_snips:
        return snips
  return snips

def as_is_scan_rich() -> Dict[str, Any]:
  exts_count: Dict[str, int] = {}
  endpoints: List[Dict[str, Any]] = []
  tests: List[Dict[str, Any]] = []
  ui_pages: List[str] = []
  evidence_paths: List[str] = []
  snippets: List[Dict[str, Any]] = []

  # Supabase (best-effort)
  db_schema = scan_supabase_schema()

  files_scanned = 0
  for p in ROOT.rglob("*"):
    if any(part in SKIP_DIRS for part in p.parts):
      continue
    if not p.is_file():
      continue
    files_scanned += 1
    ext = p.suffix.lower() or "(no_ext)"
    exts_count[ext] = exts_count.get(ext, 0) + 1

    r = rel(p)

    # Next.js API routes
    if re.search(r"(^|/)app/api/.+/route\.(ts|js)$", r, re.I):
      txt = safe_read_file(p)
      methods = sorted(set([mm.group(1).upper() for mm in NEXT_ROUTE_METHOD_RE.finditer(txt)])) or ["(unknown)"]
      path = derive_next_api_path(p)
      endpoints.append({"type":"next","path":path,"methods":methods,"file":r})
      evidence_paths.append(r)
      snippets += collect_snippets(p, [NEXT_ROUTE_METHOD_RE], max_snips=2)

    # Express/Fastify routes
    if p.suffix.lower() in {".ts",".tsx",".js",".jsx"}:
      txt = safe_read_file(p)
      for rp in ROUTE_PATTERNS:
        for m in rp.finditer(txt):
          method = m.group(1).upper()
          path = m.group(2)
          endpoints.append({"type":"node","path":path,"methods":[method],"file":r})
          evidence_paths.append(r)
      if any(rp.search(txt) for rp in ROUTE_PATTERNS):
        snippets += collect_snippets(p, ROUTE_PATTERNS, max_snips=2)

    # Tests
    if TEST_FILE_RE.search(r):
      txt = safe_read_file(p)
      names: List[str] = []
      for tr in TEST_NAME_RES:
        for m in tr.finditer(txt):
          if m.lastindex and m.lastindex >= 1:
            names.append(m.group(m.lastindex))
      tests.append({"file": r, "names": names[:20]})
      evidence_paths.append(r)
      snippets += collect_snippets(p, TEST_NAME_RES, max_snips=1)

    # UI pages/screens (best-effort)
    if re.search(r"(^|/)(app|pages)/.+page\.(tsx|jsx)$", r, re.I) or re.search(r"(^|/)(screens|views)/.+\.(tsx|jsx)$", r, re.I):
      ui_pages.append(r)

  # Keep bounded
  endpoints = endpoints[:250]
  tests = tests[:200]
  ui_pages = sorted(set(ui_pages))[:250]
  evidence_paths = sorted(set(evidence_paths))[:250]
  snippets = snippets[:40]  # critical: keep prompt bounded

  return {
    "repo_root": str(ROOT),
    "files_scanned": files_scanned,
    "file_extensions": dict(sorted(exts_count.items(), key=lambda kv: (-kv[1], kv[0]))),
    "db_schema_supabase_best_effort": db_schema,
    "api_endpoints": endpoints,
    "tests": tests,
    "ui_pages_screens": ui_pages,
    "interesting_evidence_paths": evidence_paths,
    "snippets": snippets,
    "generated_at": datetime.utcnow().isoformat() + "Z",
  }

def format_as_is_md(as_is: Dict[str, Any], canonical_path: str) -> str:
  lines = []
  lines.append("# As-Is Scan (deterministic, evidence-oriented)")
  lines.append(f"- Canonical requirements: `{canonical_path}`")
  lines.append(f"- Files scanned: `{as_is['files_scanned']}`")
  lines.append("")
  lines.append("## Database (Database (DB)) schema (Supabase best-effort)")
  tables = as_is["db_schema_supabase_best_effort"].get("tables", {})
  lines.append(f"- Tables found: `{len(tables)}`")
  for t in list(tables.keys())[:25]:
    cols = tables[t].get("columns", {})
    lines.append(f"  - `{t}` (columns: {len(cols)})")
  lines.append("")
  lines.append("## API endpoints (Application Programming Interface (API)) (sample)")
  for ep in as_is["api_endpoints"][:40]:
    lines.append(f"- `{','.join(ep.get('methods',[]))}` `{ep.get('path')}` — `{ep.get('file')}`")
  lines.append("")
  lines.append("## Tests (sample)")
  for t in as_is["tests"][:25]:
    lines.append(f"- `{t['file']}`")
  lines.append("")
  lines.append("## UI pages/screens (sample)")
  for u in as_is["ui_pages_screens"][:25]:
    lines.append(f"- `{u}`")
  lines.append("")
  lines.append("## Snippets included in prompt (count)")
  lines.append(f"- Snippets: `{len(as_is.get('snippets', []))}`")
  return "\n".join(lines).strip() + "\n"

# ---------------- Milestones + determinants of truth ----------------
def milestone_for(req: Dict[str, Any]) -> str:
  blob = (req.get("title","") + " " + req.get("description","")).lower()
  if "rider" in blob:
    return "Rider App"
  if "driver" in blob:
    return "Driver App"
  if "dispatch" in blob or "dispatcher" in blob:
    return "Dispatch Console"
  if "tenant" in blob:
    return "Tenant Admin"
  if "super admin" in blob or "platform" in blob:
    return "Platform Admin"
  if "payment" in blob or "payout" in blob:
    return "Payments/Payouts"
  if "security" in blob or "auth" in blob or "rbac" in blob:
    return "Security/Identity"
  return "Core/Other"

def evidence_type(e: str) -> str:
  e = e.strip().lower()
  for pref in ["route:","db:","test:","ui:","ci:","file:"]:
    if e.startswith(pref):
      return pref[:-1]
  return "other"

# ---------------- OpenAI call ----------------
def openai_batch_eval(client: OpenAI, model: str, batch: List[Dict[str, Any]], as_is_short: str, snippets_short: str, include_undoc: bool) -> Dict[str, Any]:
  schema = {
    "name": "agent_result",
    "strict": True,
    "schema": {
      "type": "object",
      "additionalProperties": False,
      "required": ["updated_statuses", "implemented_not_documented"],
      "properties": {
        "updated_statuses": {
          "type": "array",
          "items": {
            "type": "object",
            "additionalProperties": False,
            "required": ["requirement_id", "status", "evidence", "gaps", "notes"],
            "properties": {
              "requirement_id": {"type": "string"},
              "status": {"type": "string", "enum": ["Not Started","In Progress","Implemented","Tested","Blocked"]},
              "evidence": {"type": "array", "items": {"type": "string"}},
              "gaps": {"type": "array", "items": {"type": "string"}},
              "notes": {"type": "string"},
            }
          }
        },
        "implemented_not_documented": {
          "type": "array",
          "items": {
            "type": "object",
            "additionalProperties": False,
            "required": ["title", "evidence", "why_not_in_requirements"],
            "properties": {
              "title": {"type": "string"},
              "evidence": {"type": "array", "items": {"type": "string"}},
              "why_not_in_requirements": {"type": "string"},
            }
          }
        }
      }
    }
  }

  batch_slim = []
  for r in batch:
    batch_slim.append({
      "requirement_id": r["requirement_id"],
      "title": r["title"],
      "acceptance_criteria": r.get("acceptance_criteria", []),
      "description": (r.get("description","") or "")[:2000],
    })

  rules = (
    "STRICT EVIDENCE RULES (non-negotiable):\n"
    "- Be conservative. If you cannot cite explicit evidence from AS-IS or SNIPPETS, do NOT mark Implemented/Tested.\n"
    "- Evidence must be concrete and typed with prefixes:\n"
    "  - route:METHOD PATH @ file:line\n"
    "  - db:table.column @ file:line\n"
    "  - test:framework file:line (test name)\n"
    "  - ui:path\n"
    "  - ci:workflow\n"
    "  - file:path\n"
    "- If status=Tested, include at least one test: evidence.\n"
    "- Only update requirement_id values in this batch.\n"
  )

  undoc_rule = (
    "Also identify implemented features NOT covered by the requirements, using ONLY evidence in AS-IS/SNIPPETS.\n"
    if include_undoc else
    "implemented_not_documented MUST be an empty array for this call.\n"
  )

  user_prompt = (
    f"{rules}\n\n"
    "AS-IS (summary):\n"
    f"{as_is_short}\n\n"
    "SNIPPETS (short, evidence):\n"
    f"{snippets_short}\n\n"
    "REQUIREMENTS BATCH:\n"
    f"{json.dumps(batch_slim, ensure_ascii=False, indent=2)}\n\n"
    f"{undoc_rule}"
  )

  resp = client.chat.completions.create(
    model=model,
    messages=[
      {"role":"system","content":"You are an agentic Artificial Intelligence (AI) doing evidence-based codebase-to-requirements mapping."},
      {"role":"user","content": user_prompt},
    ],
    response_format={"type":"json_schema","json_schema": schema},
  )
  return json.loads(resp.choices[0].message.content)

def main():
  req_dir = ROOT / "Requirements"
  agent_input = ROOT / "AgentInput"
  agent_output = ROOT / "AgentOutput"
  agent_input.mkdir(parents=True, exist_ok=True)
  agent_output.mkdir(parents=True, exist_ok=True)

  run_mode = os.getenv("RUN_MODE","test").strip().lower()
  model = os.getenv("OPENAI_MODEL","gpt-5.2")
  batch_size = int(os.getenv("BATCH_SIZE","10"))
  max_requirements = int(os.getenv("MAX_REQUIREMENTS","200"))

  canonical_path = find_canonical(req_dir)
  md = read_text(canonical_path)
  reqs = parse_requirements(md, canonical_path)

  # Write AgentInput requirements
  write_text(agent_input / "requirements.jsonl", "\n".join(json.dumps(r, ensure_ascii=False) for r in reqs) + "\n")
  write_json(agent_input / "requirements.json", reqs)

  # Rich as-is scan
  as_is = as_is_scan_rich()
  as_is["canonical_requirements"] = str(canonical_path).replace("\\","/")
  write_json(agent_input / "as_is_scan.json", as_is)
  write_text(agent_input / "as_is_scan.md", format_as_is_md(as_is, as_is["canonical_requirements"]))

  # Seed status
  seed = [{
    "requirement_id": r["requirement_id"],
    "title": r["title"],
    "status": "Not Started",
    "evidence": [],
    "gaps": ["Not yet evaluated by agentic Artificial Intelligence (AI)."],
    "notes": "",
  } for r in reqs]
  write_text(agent_input / "requirements_status_seed.jsonl", "\n".join(json.dumps(x, ensure_ascii=False) for x in seed) + "\n")

  # Build bounded prompt blocks
  as_is_md = read_text(agent_input / "as_is_scan.md")
  if len(as_is_md) > 12000:
    as_is_md = as_is_md[:12000] + "\n[TRUNCATED]\n"

  snips = as_is.get("snippets", [])
  snips_txt = []
  for s in snips:
    snips_txt.append(f"- {s['file']}:{s['line_start']}-{s['line_end']}\n{s['snippet']}")
  snippets_short = "\n\n".join(snips_txt)
  if len(snippets_short) > 12000:
    snippets_short = snippets_short[:12000] + "\n[TRUNCATED]\n"

  # Select target
  target = reqs[:max_requirements]
  if run_mode == "test":
    target = target[:5]

  status_by_id = {s["requirement_id"]: s for s in seed}

  client = OpenAI()

  implemented_not_documented_all: List[Dict[str, Any]] = []

  for i in range(0, len(target), batch_size):
    batch = target[i:i+batch_size]
    include_undoc = (i == 0)
    out = openai_batch_eval(client, model, batch, as_is_md, snippets_short, include_undoc=include_undoc)

    for u in out["updated_statuses"]:
      rid = u["requirement_id"]
      if rid not in status_by_id:
        continue

      # Enforce conservative gates
      ev = u.get("evidence", []) or []
      st = u.get("status", "Not Started")

      if st in {"Implemented","Tested"} and not ev:
        st = "Blocked"
        u["gaps"] = (u.get("gaps") or []) + ["No concrete evidence provided; cannot mark Implemented/Tested."]

      if st == "Tested" and not any(str(e).lower().startswith("test:") for e in ev):
        st = "Blocked"
        u["gaps"] = (u.get("gaps") or []) + ["Status=Tested requires at least one test: evidence item."]

      status_by_id[rid]["status"] = st
      status_by_id[rid]["evidence"] = ev
      status_by_id[rid]["gaps"] = u.get("gaps", []) or []
      status_by_id[rid]["notes"] = u.get("notes", "") or ""

    if include_undoc:
      implemented_not_documented_all = out.get("implemented_not_documented", []) or []

  # Write AgentOutput
  status_rows = []
  for r in reqs:
    s = status_by_id.get(r["requirement_id"], {})
    status_rows.append({
      "requirement_id": r["requirement_id"],
      "title": r["title"],
      "milestone": milestone_for(r),
      "status": s.get("status","Not Started"),
      "evidence": s.get("evidence",[]),
      "gaps": s.get("gaps",[]),
      "notes": s.get("notes",""),
    })

  # requirements_status.jsonl
  write_text(ROOT / "AgentOutput" / "requirements_status.jsonl", "\n".join(json.dumps(x, ensure_ascii=False) for x in status_rows) + "\n")

  # requirements_status.md
  md_lines = []
  md_lines.append("# Requirements Status (evidence-based)")
  md_lines.append(f"- Generated: {datetime.utcnow().isoformat()}Z")
  md_lines.append(f"- Run mode: `{run_mode}` | Model: `{model}` | Batch size: `{batch_size}`")
  md_lines.append("")
  md_lines.append("| Requirement ID | Milestone | Status | Title | Evidence (count) |")
  md_lines.append("|---|---|---|---|---:|")
  for x in status_rows:
    title_safe = (x.get('title') or '').replace('|', '\\|')
    md_lines.append(f"| `{x['requirement_id']}` | {x['milestone']} | **{x['status']}** | {title_safe} | {len(x['evidence'])} |")
  md_lines.append("")
  md_lines.append("## Notes (only items with evidence/gaps/notes)")
  for x in status_rows:
    if x["evidence"] or x["gaps"] or x["notes"]:
      md_lines.append(f"### {x['requirement_id']} — {x['title']}")
      if x["evidence"]:
        md_lines.append("**Evidence:**")
        md_lines += [f"- {e}" for e in x["evidence"]]
      if x["gaps"]:
        md_lines.append("**Gaps:**")
        md_lines += [f"- {g}" for g in x["gaps"]]
      if x["notes"]:
        md_lines.append("**Notes:**")
        md_lines.append(x["notes"])
      md_lines.append("")
  write_text(ROOT / "AgentOutput" / "requirements_status.md", "\n".join(md_lines).strip() + "\n")

  # implemented_not_documented.md
  undoc_md = ["# Implemented but Not Documented", ""]
  if implemented_not_documented_all:
    for item in implemented_not_documented_all:
      undoc_md.append(f"## {item.get('title','(untitled)')}")
      undoc_md.append("")
      undoc_md.append("**Evidence:**")
      for e in item.get("evidence", []):
        undoc_md.append(f"- {e}")
      undoc_md.append("")
      undoc_md.append("**Why not in requirements:**")
      undoc_md.append(item.get("why_not_in_requirements",""))
      undoc_md.append("")
  else:
    undoc_md.append("_None identified from the current evidence._")
  write_text(ROOT / "AgentOutput" / "implemented_not_documented.md", "\n".join(undoc_md).strip() + "\n")

  # Milestone summary with determinants-of-truth counts
  ms: Dict[str, Dict[str, Any]] = {}
  for row in status_rows:
    m = row["milestone"]
    ms.setdefault(m, {"total":0,"Not Started":0,"In Progress":0,"Implemented":0,"Tested":0,"Blocked":0,"det":{}})
    ms[m]["total"] += 1
    ms[m][row["status"]] = ms[m].get(row["status"], 0) + 1
    for e in row.get("evidence", []):
      et = evidence_type(str(e))
      ms[m]["det"][et] = ms[m]["det"].get(et, 0) + 1

  ms_md = ["# Milestone Summary (Definition of Done (DoD) rollups)", ""]
  ms_md.append("| Milestone | Total | Tested | Implemented | Blocked | Determinants of truth (route/db/test/ui/ci/file/other) |")
  ms_md.append("|---|---:|---:|---:|---:|---|")
  for k in sorted(ms.keys()):
    det = ms[k]["det"]
    det_str = "/".join(str(det.get(t,0)) for t in ["route","db","test","ui","ci","file","other"])
    ms_md.append(f"| {k} | {ms[k]['total']} | {ms[k].get('Tested',0)} | {ms[k].get('Implemented',0)} | {ms[k].get('Blocked',0)} | {det_str} |")
  ms_md.append("")
  ms_md.append("**Milestone Done rule (current):** Done when `Tested == Total` (all requirements in milestone are Tested) and each Tested item has at least one `test:` evidence line.")
  write_text(ROOT / "AgentOutput" / "milestone_summary.md", "\n".join(ms_md).strip() + "\n")

  # run_metadata.json (lets you verify files are from the latest run)
  status_counts: Dict[str,int] = {}
  det_counts: Dict[str,int] = {}
  for row in status_rows:
    status_counts[row["status"]] = status_counts.get(row["status"], 0) + 1
    for e in row.get("evidence", []):
      et = evidence_type(str(e))
      det_counts[et] = det_counts.get(et, 0) + 1

  run_url = f"{os.getenv('GITHUB_SERVER_URL','')}/{os.getenv('GITHUB_REPOSITORY','')}/actions/runs/{os.getenv('GITHUB_RUN_ID','')}".strip("/")
  meta = {
    "generated_at_utc": datetime.utcnow().isoformat() + "Z",
    "run_mode": run_mode,
    "model": model,
    "batch_size": batch_size,
    "max_requirements": max_requirements,
    "requirements_total": len(reqs),
    "requirements_evaluated_this_run": len(target),
    "status_counts": status_counts,
    "determinants_of_truth_counts": det_counts,
    "git_sha": os.getenv("GITHUB_SHA",""),
    "workflow_run_url": run_url,
    "canonical_requirements": str(canonical_path).replace("\\","/"),
  }
  write_json(ROOT / "AgentOutput" / "run_metadata.json", meta)

  print("Wrote: AgentOutput/requirements_status.jsonl")
  print("Wrote: AgentOutput/requirements_status.md")
  print("Wrote: AgentOutput/implemented_not_documented.md")
  print("Wrote: AgentOutput/milestone_summary.md")
  print("Wrote: AgentOutput/run_metadata.json")

if __name__ == "__main__":
  main()
