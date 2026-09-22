from __future__ import annotations

import glob
from collections.abc import Iterable
from dataclasses import dataclass
from pathlib import Path

import pathspec

COMMON_IGNORES = {
    ".git",
    ".hg",
    ".svn",
    ".venv",
    "venv",
    "node_modules",
    "__pycache__",
    "dist",
    "build",
    ".mypy_cache",
    ".pytest_cache",
    ".ruff_cache",
}


@dataclass(frozen=True)
class TextChunk:
    path: Path
    start_line: int
    end_line: int
    text: str


def _gitignore_spec(root: Path) -> pathspec.PathSpec | None:
    ignore = root / ".gitignore"
    if not ignore.is_file():
        return None
    return pathspec.PathSpec.from_lines(
        "gitwildmatch", ignore.read_text(encoding="utf-8").splitlines()
    )


def _allowed(path: Path, root: Path, spec: pathspec.PathSpec | None) -> bool:
    try:
        rel = path.relative_to(root)
    except ValueError:
        return True
    if any(part in COMMON_IGNORES for part in rel.parts):
        return False
    return spec is None or not spec.match_file(rel.as_posix())


def discover_files(inputs: Iterable[str], *, respect_gitignore: bool = True) -> list[Path]:
    found: set[Path] = set()
    for raw in inputs:
        expanded = (
            [Path(p) for p in glob.glob(raw, recursive=True)]
            if glob.has_magic(raw)
            else [Path(raw)]
        )
        for item in expanded:
            if item.is_file():
                found.add(item.resolve())
                continue
            if not item.is_dir():
                continue
            root = item.resolve()
            spec = _gitignore_spec(root) if respect_gitignore else None
            for candidate in root.rglob("*"):
                if candidate.is_file() and _allowed(candidate, root, spec):
                    found.add(candidate.resolve())
    return sorted(found)


def read_text(path: Path, *, max_bytes: int = 2_000_000) -> str | None:
    try:
        if path.stat().st_size > max_bytes:
            return None
        raw = path.read_bytes()
        if b"\x00" in raw:
            return None
        return raw.decode("utf-8")
    except (OSError, UnicodeDecodeError):
        return None


def chunk_text(path: Path, text: str, *, lines: int = 80, overlap: int = 10) -> list[TextChunk]:
    if lines < 1 or overlap < 0 or overlap >= lines:
        raise ValueError("Require lines >= 1 and 0 <= overlap < lines")
    all_lines = text.splitlines()
    if not all_lines:
        return []
    chunks: list[TextChunk] = []
    step = lines - overlap
    for start in range(0, len(all_lines), step):
        stop = min(start + lines, len(all_lines))
        chunks.append(
            TextChunk(
                path=path,
                start_line=start + 1,
                end_line=stop,
                text="\n".join(all_lines[start:stop]),
            )
        )
        if stop == len(all_lines):
            break
    return chunks
