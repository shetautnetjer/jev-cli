from __future__ import annotations

import glob
import os
import stat
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


@dataclass(frozen=True)
class DiscoveredFile:
    path: Path
    root: Path | None = None
    relative_path: Path | None = None

    @property
    def is_explicit(self) -> bool:
        return self.root is None


def _read_regular_bytes_no_follow(path: Path, *, max_bytes: int) -> bytes | None:
    """Read one regular file without following a final-component symlink."""
    try:
        if path.is_symlink():
            return None
        flags = os.O_RDONLY | getattr(os, "O_NOFOLLOW", 0)
        fd = os.open(path, flags)
        try:
            info = os.fstat(fd)
            if not stat.S_ISREG(info.st_mode) or info.st_size > max_bytes:
                return None
            with os.fdopen(fd, "rb", closefd=False) as handle:
                raw = handle.read(max_bytes + 1)
            if len(raw) > max_bytes:
                return None
            return raw
        finally:
            os.close(fd)
    except OSError:
        return None


def _read_relative_regular_bytes_no_follow(
    root: Path,
    relative_path: Path,
    *,
    max_bytes: int,
) -> bytes | None:
    """Read a file beneath root without following symlinks in any path component."""
    if relative_path.is_absolute() or ".." in relative_path.parts or not relative_path.parts:
        return None

    directory_flags = os.O_RDONLY | getattr(os, "O_DIRECTORY", 0) | getattr(os, "O_NOFOLLOW", 0)
    file_flags = os.O_RDONLY | getattr(os, "O_NOFOLLOW", 0)
    opened: list[int] = []
    try:
        current_fd = os.open(root, directory_flags)
        opened.append(current_fd)
        for part in relative_path.parts[:-1]:
            next_fd = os.open(part, directory_flags, dir_fd=current_fd)
            opened.append(next_fd)
            current_fd = next_fd

        file_fd = os.open(relative_path.parts[-1], file_flags, dir_fd=current_fd)
        opened.append(file_fd)
        info = os.fstat(file_fd)
        if not stat.S_ISREG(info.st_mode) or info.st_size > max_bytes:
            return None
        with os.fdopen(file_fd, "rb", closefd=False) as handle:
            raw = handle.read(max_bytes + 1)
        if len(raw) > max_bytes:
            return None
        return raw
    except (OSError, NotImplementedError):
        return None
    finally:
        for fd in reversed(opened):
            try:
                os.close(fd)
            except OSError:
                pass


def _gitignore_spec(root: Path) -> pathspec.PathSpec | None:
    raw = _read_relative_regular_bytes_no_follow(
        root,
        Path(".gitignore"),
        max_bytes=1_000_000,
    )
    if raw is None:
        return None
    try:
        text = raw.decode("utf-8")
    except UnicodeDecodeError:
        return None
    return pathspec.PathSpec.from_lines("gitwildmatch", text.splitlines())


def _allowed(path: Path, root: Path, spec: pathspec.PathSpec | None) -> bool:
    try:
        rel = path.relative_to(root)
    except ValueError:
        return False
    if any(part in COMMON_IGNORES for part in rel.parts):
        return False
    return spec is None or not spec.match_file(rel.as_posix())


def discover_file_records(
    inputs: Iterable[str],
    *,
    respect_gitignore: bool = True,
) -> list[DiscoveredFile]:
    found: dict[Path, DiscoveredFile] = {}
    for raw in inputs:
        has_magic = glob.has_magic(raw)
        expanded = [Path(p) for p in glob.glob(raw, recursive=True)] if has_magic else [Path(raw)]
        for item in expanded:
            if item.is_file():
                if has_magic and item.is_symlink():
                    continue
                resolved = item.resolve()
                found[resolved] = DiscoveredFile(path=resolved)
                continue
            if not item.is_dir():
                continue
            root = item.resolve()
            spec = _gitignore_spec(root) if respect_gitignore else None
            for candidate in root.rglob("*"):
                # Directory scans never follow file symlinks. A caller may still
                # explicitly select a literal symlink as a direct file input.
                if candidate.is_symlink() or not candidate.is_file():
                    continue
                resolved = candidate.resolve()
                if not _allowed(candidate, root, spec):
                    continue
                if not _allowed(resolved, root, spec):
                    continue
                relative_path = candidate.relative_to(root)
                found[resolved] = DiscoveredFile(
                    path=resolved,
                    root=root,
                    relative_path=relative_path,
                )
    return [found[path] for path in sorted(found)]


def discover_files(inputs: Iterable[str], *, respect_gitignore: bool = True) -> list[Path]:
    """Compatibility wrapper returning only resolved paths."""
    return [
        record.path for record in discover_file_records(inputs, respect_gitignore=respect_gitignore)
    ]


def _decode_text(raw: bytes | None) -> str | None:
    if raw is None or b"\x00" in raw:
        return None
    try:
        return raw.decode("utf-8")
    except UnicodeDecodeError:
        return None


def read_text(path: Path, *, max_bytes: int = 2_000_000) -> str | None:
    return _decode_text(_read_regular_bytes_no_follow(path, max_bytes=max_bytes))


def read_discovered_text(
    discovered: DiscoveredFile,
    *,
    max_bytes: int = 2_000_000,
) -> str | None:
    if discovered.root is not None and discovered.relative_path is not None:
        raw = _read_relative_regular_bytes_no_follow(
            discovered.root,
            discovered.relative_path,
            max_bytes=max_bytes,
        )
        return _decode_text(raw)
    return read_text(discovered.path, max_bytes=max_bytes)


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
