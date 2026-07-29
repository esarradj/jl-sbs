from __future__ import annotations

import site
import sys
import sysconfig
from pathlib import Path


PATCHES = {
    ",processEscapes:true,processEnvironments:true})": ',processEscapes:true,processEnvironments:true,tags:"ams"})',
    ",processEscapes:!0,processEnvironments:!0})": ',processEscapes:!0,processEnvironments:!0,tags:"ams"})',
}
ALREADY_PATCHED = (
    ',processEscapes:true,processEnvironments:true,tags:"ams"})',
    ',processEscapes:!0,processEnvironments:!0,tags:"ams"})',
)


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
        files: list[Path] = []
        for path in map(Path, paths):
            if path.is_dir():
                files.extend(path.rglob("*.js"))
            else:
                files.append(path)
        return files

    files: list[Path] = []
    for static_dir in static_dirs():
        files.extend(static_dir.glob("*.js"))
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
        if any(patched in text for patched in ALREADY_PATCHED):
            already_patched.append(path)
            continue

        new_text = text
        for old, new in PATCHES.items():
            new_text = new_text.replace(old, new)

        if new_text == text:
            continue

        if not dry_run:
            path.write_text(new_text)
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
