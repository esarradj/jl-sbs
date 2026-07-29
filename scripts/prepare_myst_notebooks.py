from __future__ import annotations

import json
import re
import sys
from pathlib import Path


COMMAND_RE = re.compile(r"\\(?:re)?newcommand|\\providecommand")
EQREF_RE = re.compile(r"\\eqref\{([^}]+)\}")
WRAPPER_RE = re.compile(r"^\s*(?:\$+|\\begin\{equation\*?\}|\\end\{equation\*?\})\s*$")


def read_group(text: str, start: int) -> tuple[str, int] | None:
    if start >= len(text) or text[start] != "{":
        return None
    depth = 0
    for index in range(start, len(text)):
        char = text[index]
        if char == "{":
            depth += 1
        elif char == "}":
            depth -= 1
            if depth == 0:
                return text[start + 1 : index], index + 1
    return None


def read_optional_arg_count(text: str, start: int) -> tuple[int, int]:
    if start >= len(text) or text[start] != "[":
        return 0, start
    end = text.find("]", start + 1)
    if end < 0:
        return 0, start
    value = text[start + 1 : end].strip()
    return int(value) if value.isdigit() else 0, end + 1


def find_commands(text: str) -> list[tuple[str, str, int, int]]:
    commands = []
    pos = 0
    while match := COMMAND_RE.search(text, pos):
        index = match.end()
        while index < len(text) and text[index].isspace():
            index += 1

        name = None
        if index < len(text) and text[index] == "{":
            group = read_group(text, index)
            if not group:
                pos = match.end()
                continue
            name, index = group
        elif index < len(text) and text[index] == "\\":
            name_match = re.match(r"\\[A-Za-z]+|\\.", text[index:])
            if not name_match:
                pos = match.end()
                continue
            name = name_match.group(0)
            index += len(name)

        if not name:
            pos = match.end()
            continue

        while index < len(text) and text[index].isspace():
            index += 1
        _, index = read_optional_arg_count(text, index)

        while index < len(text) and text[index].isspace():
            index += 1
        body = read_group(text, index)
        if not body:
            pos = match.end()
            continue

        macro, end = body
        commands.append((name, macro, match.start(), end))
        pos = end
    return commands


def yaml_quote(value: str) -> str:
    return "'" + value.replace("'", "''") + "'"


def frontmatter_lines(macros: dict[str, str]) -> list[str]:
    return ["---\n", *math_lines(macros), "---\n", "\n"]


def math_lines(macros: dict[str, str]) -> list[str]:
    return ["math:\n", *macro_entry_lines(macros)]


def macro_entry_lines(macros: dict[str, str]) -> list[str]:
    lines = []
    for name, macro in sorted(macros.items()):
        lines.append(f"  {yaml_quote(name)}: {yaml_quote(macro)}\n")
    return lines


def source_text(cell: dict) -> str:
    source = cell.get("source", [])
    return "".join(source) if isinstance(source, list) else source


def set_source(cell: dict, text: str) -> None:
    cell["source"] = text.splitlines(keepends=True)


def replace_eqrefs(text: str) -> str:
    return EQREF_RE.sub(r"[](#\1)", text)


def strip_commands(text: str, commands: list[tuple[str, str, int, int]]) -> str:
    chunks = []
    pos = 0
    for _, _, start, end in commands:
        chunks.append(text[pos:start])
        pos = end
    chunks.append(text[pos:])
    return "".join(chunks)


def is_empty_macro_cell(text: str) -> bool:
    return all(not line.strip() or WRAPPER_RE.match(line) for line in text.splitlines())


def update_frontmatter(first_cell: dict, macros: dict[str, str]) -> None:
    text = source_text(first_cell)
    lines = text.splitlines(keepends=True)
    if lines and lines[0].strip() == "---":
        for index, line in enumerate(lines[1:], start=1):
            if line.strip() == "---":
                header = "".join(lines[1:index])
                if re.search(r"^math\s*:", header, re.MULTILINE):
                    for line_index in range(1, index):
                        if re.match(r"^math\s*:", lines[line_index]):
                            lines[line_index + 1 : line_index + 1] = macro_entry_lines(macros)
                            break
                else:
                    lines[index:index] = math_lines(macros)
                set_source(first_cell, "".join(lines))
                return
    set_source(first_cell, "".join(frontmatter_lines(macros)) + text.lstrip("\n"))


def process_notebook(path: Path) -> bool:
    notebook = json.loads(path.read_text(encoding="utf-8"))
    cells = notebook.get("cells", [])
    macros: dict[str, str] = {}
    changed = False

    for cell in cells:
        if cell.get("cell_type") != "markdown":
            continue
        text = replace_eqrefs(source_text(cell))
        if text != source_text(cell):
            set_source(cell, text)
            changed = True
        commands = find_commands(text)
        if not commands:
            continue
        for name, macro, _, _ in commands:
            macros[name] = macro
        stripped = strip_commands(text, commands)
        set_source(cell, stripped)
        changed = True

    if not macros:
        if changed:
            path.write_text(
                json.dumps(notebook, indent=1, ensure_ascii=False) + "\n",
                encoding="utf-8",
            )
        return changed

    notebook["cells"] = [
        cell
        for cell in cells
        if cell.get("cell_type") != "markdown" or not is_empty_macro_cell(source_text(cell))
    ]
    first_markdown = next(
        cell for cell in notebook["cells"] if cell.get("cell_type") == "markdown"
    )
    update_frontmatter(first_markdown, macros)
    path.write_text(json.dumps(notebook, indent=1, ensure_ascii=False) + "\n", encoding="utf-8")
    return True


def main(argv: list[str]) -> int:
    roots = [Path(arg) for arg in argv] or [Path("content")]
    updated = 0
    for root in roots:
        for path in root.rglob("*.ipynb"):
            if process_notebook(path):
                updated += 1
                print(f"Prepared MyST notebook in {path}")
    print(f"Prepared {updated} notebook(s).")
    return 0


if __name__ == "__main__":
    raise SystemExit(main(sys.argv[1:]))
