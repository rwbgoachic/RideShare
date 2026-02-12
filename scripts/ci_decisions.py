#!/usr/bin/env python3
import os
from pathlib import Path

root = Path(".").resolve()

def exists(p: str) -> bool:
    return (root / p).exists()

# pkg mgr
pkg_mgr = "npm"
if exists("pnpm-lock.yaml"):
    pkg_mgr = "pnpm"
elif exists("yarn.lock"):
    pkg_mgr = "yarn"

# web dir heuristics
candidates = [
    "apps/web",
    "apps/frontend",
    "web",
    "frontend",
    ".",
]
web_dir = ""
for d in candidates:
    if exists(d) and exists(str(Path(d) / "package.json")):
        web_dir = d
        break

# output env lines (key=value)
# Keep this stable; workflows can source it.
out = {
    "PKG_MGR": pkg_mgr,
    "WEB_DIR": web_dir,
    "HAS_WEB": "1" if web_dir else "0",
    "RUN_A11Y_WEB": "1" if web_dir else "0",
}
for k, v in out.items():
    print(f"{k}={v}")
