#!/usr/bin/env python3

from __future__ import annotations

import argparse
import os
import re
import shutil
import subprocess
import sys
from dataclasses import dataclass
from pathlib import Path


class ScriptError(RuntimeError):
    pass


def eprint(*args: object) -> None:
    print(*args, file=sys.stderr)


def _slugify(name: str) -> str:
    s = name.strip().lower()
    s = re.sub(r"[^\w\- ]+", "", s, flags=re.UNICODE)
    s = re.sub(r"[\s_]+", "-", s)
    s = re.sub(r"-{2,}", "-", s).strip("-")
    return s or "diagram"


def _ensure_svg_name(svg_name: str | None, markdown_path: Path, topic: str | None) -> str:
    if svg_name:
        base = Path(svg_name).name
        base = base[:-4] if base.lower().endswith(".svg") else base
        return _slugify(base)
    md_base = markdown_path.stem
    if topic:
        return _slugify(f"{md_base}-{topic}")
    return _slugify(f"{md_base}-diagram")


def _read_xml(args: argparse.Namespace) -> str:
    if args.xml_file:
        p = Path(args.xml_file)
        if not p.exists():
            raise ScriptError(f"draw.io XML file not found: {p}")
        return p.read_text(encoding="utf-8")
    if args.xml_stdin:
        data = sys.stdin.read()
        if not data.strip():
            raise ScriptError("No XML received from stdin (use --xml-stdin and provide content).")
        return data
    raise ScriptError("Missing XML input: provide --xml-file or --xml-stdin.")


def _normalize_heading_text(s: str) -> str:
    s = s.strip()
    s = s.lstrip("#").strip()
    return s


def _insert_payload(markdown_text: str, payload: str, position: str, placeholder: str | None, heading: str | None) -> str:
    block = "\n" + payload.strip() + "\n"

    if position == "placeholder":
        if not placeholder:
            raise ScriptError("--placeholder is required when --position placeholder")
        if placeholder not in markdown_text:
            raise ScriptError(f"Placeholder not found in Markdown: {placeholder!r}")
        return markdown_text.replace(placeholder, block, 1)

    if position == "after-heading":
        if not heading:
            raise ScriptError("--heading is required when --position after-heading")
        target = _normalize_heading_text(heading)
        lines = markdown_text.splitlines(keepends=True)
        for i, line in enumerate(lines):
            stripped = line.strip()
            if not stripped.startswith("#"):
                continue
            if _normalize_heading_text(stripped) == target:
                insert_at = i + 1
                before = "".join(lines[:insert_at])
                after = "".join(lines[insert_at:])
                # Ensure a blank line after heading before SVG for readability.
                if not before.endswith("\n"):
                    before += "\n"
                if not before.endswith("\n\n"):
                    before += "\n"
                return before + block + "\n" + after.lstrip("\n")
        raise ScriptError(f"Heading not found in Markdown: {heading!r}")

    if position == "end":
        text = markdown_text.rstrip() + "\n\n" + payload.strip() + "\n"
        return text

    raise ScriptError(f"Unknown position: {position!r}")


@dataclass(frozen=True)
class DrawioRunner:
    executable: str  # full path to CLI executable

    def build_command(self, input_drawio: Path, output_svg: Path, border: int) -> list[str]:
        base_args = ["-x", "-f", "svg", "-o", str(output_svg), "-b", str(border), str(input_drawio)]
        return [self.executable, *base_args]


def _resolve_app_executable(app_path: Path) -> Path:
    """
    Prefer synchronous CLI binary inside the .app bundle.
    For draw.io desktop on macOS this is typically: <App>.app/Contents/MacOS/draw.io
    """
    macos_dir = app_path / "Contents" / "MacOS"
    if macos_dir.exists():
        # Prefer the canonical binary name if present.
        preferred = macos_dir / "draw.io"
        if preferred.exists() and os.access(preferred, os.X_OK):
            return preferred
        # Fallback to the first executable file in Contents/MacOS.
        for child in sorted(macos_dir.iterdir()):
            if child.is_file() and os.access(child, os.X_OK):
                return child
    raise ScriptError(
        f"draw.io app bundle found but no runnable CLI executable detected: {app_path}\n"
        "Tip: pass --drawio-app with a direct executable path, e.g. "
        "/Applications/draw.io.app/Contents/MacOS/draw.io"
    )


def _detect_drawio_runner(drawio_app: str | None) -> DrawioRunner:
    if drawio_app:
        p = Path(drawio_app).expanduser()
        if p.suffix.lower() == ".app":
            if not p.exists():
                raise ScriptError(f"draw.io app not found: {p}")
            exe = _resolve_app_executable(p)
            return DrawioRunner(executable=str(exe))
        if not p.exists():
            raise ScriptError(f"draw.io executable not found: {p}")
        if not os.access(p, os.X_OK):
            raise ScriptError(f"draw.io executable is not runnable: {p}")
        return DrawioRunner(executable=str(p))

    for candidate in ("drawio", "draw.io"):
        exe = shutil.which(candidate)
        if exe:
            return DrawioRunner(executable=exe)

    app_candidates = [
        Path("/Applications/draw.io.app"),
        Path("/Applications/diagrams.net.app"),
    ]
    for app in app_candidates:
        if app.exists():
            exe = _resolve_app_executable(app)
            return DrawioRunner(executable=str(exe))

    raise ScriptError(
        "draw.io CLI/app not found.\n"
        "- Install draw.io/diagrams.net desktop app, or ensure `drawio` is on PATH.\n"
        "- Or pass --drawio-app with an .app path, e.g. /Applications/draw.io.app\n"
        "- Homebrew (common): `brew install --cask drawio`"
    )


def _run_export(runner: DrawioRunner, input_drawio: Path, output_svg: Path, border: int) -> None:
    output_svg.parent.mkdir(parents=True, exist_ok=True)
    cmd = runner.build_command(input_drawio=input_drawio, output_svg=output_svg, border=border)
    try:
        proc = subprocess.run(cmd, capture_output=True, text=True, check=False)
    except FileNotFoundError as ex:
        raise ScriptError(f"Failed to run draw.io export command: {cmd[0]}\n{ex}") from ex

    if proc.returncode != 0:
        msg = (
            "draw.io export failed.\n"
            f"- Command: {cmd}\n"
            f"- Exit code: {proc.returncode}\n"
            f"- Stdout:\n{proc.stdout.strip()}\n"
            f"- Stderr:\n{proc.stderr.strip()}\n"
        )
        raise ScriptError(msg)

    if not output_svg.exists() or output_svg.stat().st_size == 0:
        raise ScriptError(f"SVG export did not produce output: {output_svg}")


def _clean_svg(svg_text: str) -> str:
    """
    Make SVG more Markdown-friendly by removing:
    - XML declaration: <?xml ... ?>
    - DOCTYPE line: <!DOCTYPE svg ...>
    Keep the <svg ...> root and everything inside.
    """
    s = svg_text.lstrip("\ufeff")
    # Remove optional XML declaration.
    s = re.sub(r"^\s*<\?xml[^>]*\?>\s*", "", s, flags=re.IGNORECASE)
    # Remove optional DOCTYPE (single-line in draw.io exports).
    s = re.sub(r"^\s*<!DOCTYPE[^>]*>\s*", "", s, flags=re.IGNORECASE)
    return s.strip() + "\n"


def main(argv: list[str]) -> int:
    parser = argparse.ArgumentParser(
        description="Write draw.io XML to .drawio, export SVG, and embed it into Markdown (by link or inline)."
    )
    parser.add_argument("--markdown", required=True, help="Target Markdown file path.")
    parser.add_argument("--position", required=True, choices=["placeholder", "after-heading", "end"])
    parser.add_argument("--placeholder", help="Placeholder string to replace when position=placeholder.")
    parser.add_argument("--heading", help="Heading text to insert after when position=after-heading.")
    parser.add_argument("--svg-name", help="SVG base name (optional). Can include or omit .svg.")
    parser.add_argument("--topic", help="Diagram topic (used for auto-naming when --svg-name not provided).")
    parser.add_argument("--margin", type=int, default=10, help="Export border/margin in px (default: 10).")
    parser.add_argument("--drawio-app", help="Override draw.io app (.app) or executable path.")
    parser.add_argument(
        "--embed",
        choices=["obsidian", "markdown", "inline"],
        default="obsidian",
        help="How to embed into Markdown: obsidian (![[...]]), markdown (![](...)), or inline (<svg...>). Default: obsidian.",
    )

    xml_group = parser.add_mutually_exclusive_group(required=True)
    xml_group.add_argument("--xml-file", help="Path to a file containing draw.io XML.")
    xml_group.add_argument("--xml-stdin", action="store_true", help="Read draw.io XML from stdin.")

    args = parser.parse_args(argv)

    md_path = Path(args.markdown).expanduser()
    if not md_path.exists():
        raise ScriptError(f"Markdown file not found: {md_path}")
    if not md_path.is_file():
        raise ScriptError(f"Markdown path is not a file: {md_path}")

    xml = _read_xml(args)

    svg_base = _ensure_svg_name(args.svg_name, md_path, args.topic)
    images_dir = md_path.parent / "images"
    images_dir.mkdir(parents=True, exist_ok=True)

    drawio_file = images_dir / f"{svg_base}.drawio"
    svg_file = images_dir / f"{svg_base}.svg"

    drawio_file.write_text(xml, encoding="utf-8")

    runner = _detect_drawio_runner(args.drawio_app)
    _run_export(runner, input_drawio=drawio_file, output_svg=svg_file, border=args.margin)

    svg_text = _clean_svg(svg_file.read_text(encoding="utf-8"))
    # Keep the on-disk SVG consistent with embedded content.
    svg_file.write_text(svg_text, encoding="utf-8")

    if args.embed == "inline":
        payload = svg_text
    else:
        rel = Path("images") / svg_file.name
        if args.embed == "obsidian":
            payload = f"![[{rel.as_posix()}]]"
        elif args.embed == "markdown":
            payload = f"![]({rel.as_posix()})"
        else:
            raise ScriptError(f"Unknown embed mode: {args.embed!r}")

    md_text = md_path.read_text(encoding="utf-8")
    new_md = _insert_payload(md_text, payload, args.position, args.placeholder, args.heading)
    md_path.write_text(new_md, encoding="utf-8")

    print(f"OK: wrote {drawio_file}")
    print(f"OK: exported {svg_file}")
    print(f"OK: embedded ({args.embed}) into {md_path}")
    return 0


if __name__ == "__main__":
    try:
        raise SystemExit(main(sys.argv[1:]))
    except ScriptError as ex:
        eprint(f"ERROR: {ex}")
        raise SystemExit(2)
