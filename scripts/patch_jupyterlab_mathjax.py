from __future__ import annotations

import site
import sys
import sysconfig
from pathlib import Path


OLD = ',processEscapes:true,processEnvironments:true});const'
NEW = ',processEscapes:true,processEnvironments:true,tags:"ams"});const'
ALREADY_PATCHED = ',processEscapes:true,processEnvironments:true,tags:"ams"});const'


def static_dirs() -> set[Path]:
    roots: set[Path] = set()

    for key in ("purelib", "platlib"):
        value = sysconfig.get_paths().get(key)
        if value:
            roots.add(Path(value))

    for value in site.getsitepackages():
        roots.add(Path(value))

    user_site = site.getusersitepackages()
    if user_site:
        roots.add(Path(user_site))

    return {root / "jupyterlab" / "static" for root in roots}


def candidate_files(paths: list[str]) -> list[Path]:
    if paths:
        return [Path(path) for path in paths]

    files: list[Path] = []
    for static_dir in static_dirs():
        files.extend(static_dir.glob("jlab_core*.js"))
    return files


def main() -> int:
    dry_run = "--check" in sys.argv
    paths = [arg for arg in sys.argv[1:] if arg != "--check"]

    patched: list[Path] = []
    already_patched: list[Path] = []

    for path in candidate_files(paths):
        if not path.is_file():
            continue

        text = path.read_text()
        if ALREADY_PATCHED in text:
            already_patched.append(path)
            continue

        count = text.count(OLD)
        if count == 0:
            continue

        if not dry_run:
            path.write_text(text.replace(OLD, NEW))
        patched.append(path)

    if patched:
        action = "Found" if dry_run else "Patched"
        print(f"{action} JupyterLab MathJax config in {len(patched)} file(s).")
        return 0

    if already_patched:
        print(f"JupyterLab MathJax config already patched in {len(already_patched)} file(s).")
        return 0

    print(
        "Could not find the JupyterLab MathJax initialization to patch. "
        "The JupyterLab bundle may have changed.",
        file=sys.stderr,
    )
    return 1


if __name__ == "__main__":
    raise SystemExit(main())
