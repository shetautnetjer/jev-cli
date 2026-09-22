from pathlib import Path

from jev_cli.discovery import (
    chunk_text,
    discover_file_records,
    discover_files,
    read_discovered_text,
    read_text,
)
from jev_cli.retrieval.lexical import LexicalRetriever
from jev_cli.search import rank_chunks


def test_discovery_respects_common_ignored_dirs(tmp_path: Path) -> None:
    (tmp_path / "a.txt").write_text("decision contract", encoding="utf-8")
    hidden = tmp_path / "node_modules"
    hidden.mkdir()
    (hidden / "b.txt").write_text("decision contract", encoding="utf-8")
    files = discover_files([str(tmp_path)])
    assert [p.name for p in files] == ["a.txt"]


def test_directory_discovery_rejects_file_symlink_escape(tmp_path: Path) -> None:
    root = tmp_path / "repo"
    root.mkdir()
    outside = tmp_path / "private.txt"
    outside.write_text("private material", encoding="utf-8")
    (root / "alias.txt").symlink_to(outside)

    assert discover_files([str(root)]) == []


def test_directory_discovery_rejects_symlink_to_ignored_target(tmp_path: Path) -> None:
    root = tmp_path / "repo"
    root.mkdir()
    ignored = root / "node_modules"
    ignored.mkdir()
    secret = ignored / "secret.txt"
    secret.write_text("ignored private material", encoding="utf-8")
    (root / "alias.txt").symlink_to(secret)

    assert discover_files([str(root)]) == []


def test_explicit_symlink_file_input_remains_explicitly_allowed(tmp_path: Path) -> None:
    target = tmp_path / "target.txt"
    target.write_text("explicit input", encoding="utf-8")
    link = tmp_path / "link.txt"
    link.symlink_to(target)

    assert discover_files([str(link)]) == [target.resolve()]


def test_symlinked_gitignore_is_not_followed(tmp_path: Path) -> None:
    root = tmp_path / "repo"
    root.mkdir()
    visible = root / "visible.txt"
    visible.write_text("visible", encoding="utf-8")
    outside_ignore = tmp_path / "outside-ignore"
    outside_ignore.write_text("visible.txt\n", encoding="utf-8")
    (root / ".gitignore").symlink_to(outside_ignore)

    files = discover_files([str(root)])

    assert visible.resolve() in files


def test_read_text_rejects_file_replaced_by_symlink(tmp_path: Path) -> None:
    root = tmp_path / "repo"
    root.mkdir()
    discovered = root / "candidate.txt"
    discovered.write_text("safe", encoding="utf-8")
    files = discover_files([str(root)])
    assert files == [discovered.resolve()]

    outside = tmp_path / "private.txt"
    outside.write_text("private material", encoding="utf-8")
    discovered.unlink()
    discovered.symlink_to(outside)

    assert read_text(files[0]) is None


def test_read_discovered_text_rejects_parent_directory_swap(tmp_path: Path) -> None:
    root = tmp_path / "repo"
    original_dir = root / "nested"
    original_dir.mkdir(parents=True)
    candidate = original_dir / "candidate.txt"
    candidate.write_text("safe", encoding="utf-8")

    records = discover_file_records([str(root)])
    assert len(records) == 1

    moved = root / "nested-original"
    original_dir.rename(moved)
    outside_dir = tmp_path / "outside"
    outside_dir.mkdir()
    (outside_dir / "candidate.txt").write_text("private material", encoding="utf-8")
    original_dir.symlink_to(outside_dir, target_is_directory=True)

    assert read_discovered_text(records[0]) is None


def test_glob_discovery_rejects_file_symlink(tmp_path: Path) -> None:
    root = tmp_path / "repo"
    root.mkdir()
    outside = tmp_path / "private.txt"
    outside.write_text("private material", encoding="utf-8")
    (root / "alias.txt").symlink_to(outside)

    assert discover_file_records([str(root / "*.txt")]) == []


def test_lexical_search_ranks_matching_chunk_first(tmp_path: Path) -> None:
    a = tmp_path / "a.txt"
    b = tmp_path / "b.txt"
    a.write_text("Choice needs an unknown no match option", encoding="utf-8")
    b.write_text("unrelated gardening notes", encoding="utf-8")
    chunks = []
    for path in [a, b]:
        text = read_text(path)
        assert text is not None
        chunks.extend(chunk_text(path, text))
    hits = rank_chunks("unknown option", chunks, LexicalRetriever())
    assert hits[0].chunk.path == a
    assert hits[0].retrieval_score > hits[1].retrieval_score
