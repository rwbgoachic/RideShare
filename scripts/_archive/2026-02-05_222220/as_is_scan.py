import json, os, re, subprocess, sys
from pathlib import Path

ROOT = Path(".").resolve()
AGENT_IN = ROOT / "AgentInput"
OUT_JSON = AGENT_IN / "as_is_scan.json"
OUT_MD   = AGENT_IN / "as_is_scan.md"

CODE_EXTS = {".ts",".tsx",".js",".jsx",".py",".go",".java",".cs",".rb",".php"}
SKIP_DIRS = {"node_modules",".git",".next","dist","build","out",".turbo",".cache",".venv","venv","coverage"}

def run(cmd, timeout=30):
    try:
        p = subprocess.run(cmd, cwd=str(ROOT), capture_output=True, text=True, timeout=timeout, shell=False)
        return {"cmd": cmd, "rc": p.returncode, "out": p.stdout.strip(), "err": p.stderr.strip()}
    except Exception as e:
        return {"cmd": cmd, "rc": -1, "out": "", "err": str(e)}

def walk_files():
    files = []
    for dp, dns, fns in os.walk(ROOT):
        dname = Path(dp).name
        dns[:] = [d for d in dns if d not in SKIP_DIRS]
        rel_dp = Path(dp).relative_to(ROOT)
        for fn in fns:
            p = Path(dp) / fn
            rel = p.relative_to(ROOT)
            files.append(str(rel).replace("\\","/"))
    return files

def find_package_jsons():
    pkgs = []
    for p in ROOT.rglob("package.json"):
        if any(part in SKIP_DIRS for part in p.parts):
            continue
        try:
            j = json.loads(p.read_text(encoding="utf-8", errors="replace"))
        except Exception:
            continue
        pkgs.append({
            "path": str(p.relative_to(ROOT)).replace("\\","/"),
            "name": j.get("name"),
            "private": j.get("private"),
            "scripts": list((j.get("scripts") or {}).keys()),
            "dependencies": list((j.get("dependencies") or {}).keys())[:200],
            "devDependencies": list((j.get("devDependencies") or {}).keys())[:200],
        })
    return pkgs

ROUTE_PATTERNS = [
    # Express (Express.js), Router
    re.compile(r"\b(app|router)\.(get|post|put|delete|patch)\s*\(\s*['\"]([^'\"]+)['\"]", re.I),
    # Fastify (Fastify)
    re.compile(r"\bfastify\.(get|post|put|delete|patch)\s*\(\s*['\"]([^'\"]+)['\"]", re.I),
    # Koa Router
    re.compile(r"\brouter\.(get|post|put|delete|patch)\s*\(\s*['\"]([^'\"]+)['\"]", re.I),
]

def scan_endpoints():
    endpoints = []
    for p in ROOT.rglob("*"):
        if p.is_dir(): 
            continue
        if any(part in SKIP_DIRS for part in p.parts):
            continue
        if p.suffix.lower() not in {".ts",".tsx",".js",".jsx"}:
            continue
        try:
            txt = p.read_text(encoding="utf-8", errors="replace")
        except Exception:
            continue
        for pat in ROUTE_PATTERNS:
            for m in pat.finditer(txt):
                if pat.pattern.startswith("\\bfastify"):
                    method = m.group(1).upper()
                    path = m.group(2)
                else:
                    method = m.group(2).upper()
                    path = m.group(3)
                endpoints.append({
                    "method": method,
                    "path": path,
                    "file": str(p.relative_to(ROOT)).replace("\\","/"),
                })

    # Next.js style API routes: pages/api/** or app/api/**
    for base in ["pages/api", "src/pages/api", "app/api", "src/app/api"]:
        b = ROOT / base
        if b.exists() and b.is_dir():
            for f in b.rglob("*"):
                if f.is_file() and f.suffix.lower() in {".ts",".js"}:
                    endpoints.append({
                        "method": "NEXTJS",
                        "path": "/" + str(f.relative_to(b)).replace("\\","/"),
                        "file": str(f.relative_to(ROOT)).replace("\\","/"),
                    })

    # De-dupe
    seen = set()
    out = []
    for e in endpoints:
        k = (e["method"], e["path"], e["file"])
        if k in seen:
            continue
        seen.add(k)
        out.append(e)
    return out

def find_workflows():
    wf = []
    p = ROOT / ".github" / "workflows"
    if p.exists():
        for f in p.rglob("*.yml"):
            wf.append(str(f.relative_to(ROOT)).replace("\\","/"))
        for f in p.rglob("*.yaml"):
            wf.append(str(f.relative_to(ROOT)).replace("\\","/"))
    return sorted(set(wf))

def find_migrations():
    mig = []
    for candidate in ["migrations","migration","prisma/migrations","drizzle","supabase/migrations","db/migrations","infra/db/migrations"]:
        for p in ROOT.rglob(candidate):
            if p.is_dir() and not any(part in SKIP_DIRS for part in p.parts):
                for f in p.rglob("*"):
                    if f.is_file():
                        mig.append(str(f.relative_to(ROOT)).replace("\\","/"))
    # Also common "migrations" anywhere
    for f in ROOT.rglob("*"):
        if f.is_file() and not any(part in SKIP_DIRS for part in f.parts):
            low = str(f).lower()
            if "migration" in low or "migrations" in low:
                mig.append(str(f.relative_to(ROOT)).replace("\\","/"))
    return sorted(set(mig))[:2000]

def find_tests():
    tests = []
    for f in ROOT.rglob("*"):
        if f.is_file() and not any(part in SKIP_DIRS for part in f.parts):
            name = f.name.lower()
            if any(x in name for x in [".spec.", ".test."]) or name.endswith("_test.py"):
                tests.append(str(f.relative_to(ROOT)).replace("\\","/"))
    return sorted(set(tests))[:2000]

def main():
    inv = {
        "root": str(ROOT),
        "git": {
            "head": run(["git","rev-parse","HEAD"]),
            "branch": run(["git","branch","--show-current"]),
            "status": run(["git","status","-sb"]),
            "remotes": run(["git","remote","-v"]),
        },
        "lockfiles": [p for p in ["pnpm-lock.yaml","package-lock.json","yarn.lock"] if (ROOT/p).exists()],
        "packages": find_package_jsons(),
        "workflows": find_workflows(),
        "migrations": find_migrations(),
        "tests": find_tests(),
        "endpoints": scan_endpoints(),
    }

    OUT_JSON.write_text(json.dumps(inv, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")

    md = []
    md.append("# As-Is Scan (Evidence Pack)")
    md.append("")
    md.append("## Git (Git)")
    md.append(f"- HEAD: {inv['git']['head'].get('out','')}")
    md.append(f"- Branch: {inv['git']['branch'].get('out','')}")
    md.append("```")
    md.append(inv["git"]["status"].get("out",""))
    md.append("```")
    md.append("")
    md.append("## Lockfiles")
    md.append("- " + (", ".join(inv["lockfiles"]) if inv["lockfiles"] else "(none found)"))
    md.append("")
    md.append("## Packages (package.json)")
    md.append(f"- Count: {len(inv['packages'])}")
    for p in inv["packages"][:20]:
        md.append(f"- {p['path']}  (name={p.get('name')})")
    if len(inv["packages"]) > 20:
        md.append(f"- ... (showing 20 of {len(inv['packages'])})")
    md.append("")
    md.append("## Workflows (Continuous Integration (CI))")
    md.append(f"- Count: {len(inv['workflows'])}")
    for w in inv["workflows"][:50]:
        md.append(f"- {w}")
    md.append("")
    md.append("## Migrations (Database (DB))")
    md.append(f"- Count: {len(inv['migrations'])}")
    for m in inv["migrations"][:50]:
        md.append(f"- {m}")
    md.append("")
    md.append("## Tests")
    md.append(f"- Count: {len(inv['tests'])}")
    for t in inv["tests"][:50]:
        md.append(f"- {t}")
    md.append("")
    md.append("## Endpoints (best-effort)")
    md.append(f"- Count: {len(inv['endpoints'])}")
    for e in inv["endpoints"][:60]:
        md.append(f"- {e['method']} {e['path']}  ({e['file']})")
    md.append("")

    OUT_MD.write_text("\n".join(md), encoding="utf-8")
    print(f"Wrote: {OUT_JSON}")
    print(f"Wrote: {OUT_MD}")

if __name__ == "__main__":
    main()
