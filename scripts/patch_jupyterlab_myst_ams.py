from __future__ import annotations

import os
import sys
from pathlib import Path


TARGET = "mystParse)(e,{markdownit:{linkify:!0},directives:"
REPLACEMENT = "mystParse)(e,{markdownit:{linkify:!0},extensions:{amsmath:!0},directives:"


def main() -> int:
    static_dir_override = os.environ.get("JUPYTERLAB_MYST_STATIC_DIR")
    if static_dir_override:
        static_dir = Path(static_dir_override)
    else:
        static_dir = (
            Path(sys.prefix)
            / "share"
            / "jupyter"
            / "labextensions"
            / "jupyterlab-myst"
            / "static"
        )
    if not static_dir.is_dir():
        print(f"Could not find jupyterlab-myst static assets at {static_dir}")
        return 1

    patched = []
    already_patched = []
    for path in static_dir.glob("*.js"):
        text = path.read_text(encoding="utf-8")
        if REPLACEMENT in text:
            already_patched.append(path)
            continue
        if TARGET not in text:
            continue
        path.write_text(text.replace(TARGET, REPLACEMENT, 1), encoding="utf-8")
        patched.append(path)

    if patched:
        print("Enabled MyST amsmath extension in:")
        for path in patched:
            print(f"  {path}")
        return 0

    if already_patched:
        print("MyST amsmath extension was already enabled.")
        return 0

    print("Could not find the jupyterlab-myst parser initialization to patch.")
    return 1


if __name__ == "__main__":
    raise SystemExit(main())
