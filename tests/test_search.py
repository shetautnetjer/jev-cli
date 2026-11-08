import os
from pathlib import Path

import pytest

import jev_cli.discovery as discovery
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


def test_glob_discovery_rejects_symlinked_directory_match(tmp_path: Path) -> None:
    root = tmp_path / "repo"
    root.mkdir()
    outside = tmp_path / "outside"
    outside.mkdir()
    (outside / "secret.txt").write_text("private material", encoding="utf-8")
    (root / "alias").symlink_to(outside, target_is_directory=True)

    assert discover_file_records([str(root / "*")]) == []


def test_glob_read_rejects_parent_directory_swap(tmp_path: Path) -> None:
    root = tmp_path / "repo"
    nested = root / "nested"
    nested.mkdir(parents=True)
    candidate = nested / "candidate.txt"
    candidate.write_text("safe", encoding="utf-8")

    records = discover_file_records([str(root / "**" / "*.txt")])
    assert len(records) == 1
    assert records[0].root == root.resolve()

    moved = root / "nested-original"
    nested.rename(moved)
    outside = tmp_path / "outside"
    outside.mkdir()
    (outside / "candidate.txt").write_text("private material", encoding="utf-8")
    nested.symlink_to(outside, target_is_directory=True)

    assert read_discovered_text(records[0]) is None


def test_directory_read_rejects_selected_root_ancestor_swap(tmp_path: Path) -> None:
    holder = tmp_path / "holder"
    root = holder / "repo"
    root.mkdir(parents=True)
    candidate = root / "candidate.txt"
    candidate.write_text("safe", encoding="utf-8")

    records = discover_file_records([str(root)])
    assert len(records) == 1

    original_holder = tmp_path / "holder-original"
    holder.rename(original_holder)
    outside_holder = tmp_path / "outside-holder"
    outside_root = outside_holder / "repo"
    outside_root.mkdir(parents=True)
    (outside_root / "candidate.txt").write_text("private material", encoding="utf-8")
    holder.symlink_to(outside_holder, target_is_directory=True)

    assert read_discovered_text(records[0]) is None


@pytest.mark.skipif(not hasattr(os, "mkfifo"), reason="mkfifo unavailable")
def test_fifo_gitignore_fails_closed_without_blocking(tmp_path: Path) -> None:
    root = tmp_path / "repo"
    root.mkdir()
    visible = root / "visible.txt"
    visible.write_text("visible", encoding="utf-8")
    os.mkfifo(root / ".gitignore")

    assert discover_files([str(root)]) == [visible.resolve()]


@pytest.mark.skipif(not hasattr(os, "mkfifo"), reason="mkfifo unavailable")
def test_direct_fifo_text_read_is_rejected(tmp_path: Path) -> None:
    fifo = tmp_path / "pipe.txt"
    os.mkfifo(fifo)

    assert read_text(fifo) is None


def test_absolute_root_open_closes_descriptors_on_intermediate_failure(monkeypatch) -> None:
    opened = 41
    calls = 0
    closed: list[int] = []

    def fake_open(path, flags, mode=0o777, *, dir_fd=None):
        nonlocal calls
        calls += 1
        if calls == 1:
            return opened
        raise OSError("synthetic ancestor failure")

    monkeypatch.setattr(discovery, "SECURE_NOFOLLOW_AVAILABLE", True)
    monkeypatch.setattr(discovery.os, "open", fake_open)
    monkeypatch.setattr(discovery.os, "close", closed.append)

    with pytest.raises(OSError):
        discovery._open_absolute_directory_no_follow(Path("/a/b"))

    assert closed == [opened]


def test_protected_discovery_read_fails_closed_without_secure_primitives(
    tmp_path: Path, monkeypatch
) -> None:
    root = tmp_path / "repo"
    root.mkdir()
    candidate = root / "candidate.txt"
    candidate.write_text("safe", encoding="utf-8")
    records = discover_file_records([str(root)])
    assert len(records) == 1

    monkeypatch.setattr(discovery, "SECURE_NOFOLLOW_AVAILABLE", False)

    assert read_discovered_text(records[0]) is None


def test_directory_and_glob_discovery_fail_explicitly_without_secure_primitives(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    root = tmp_path / "repo"
    root.mkdir()
    (root / "a.txt").write_text("safe", encoding="utf-8")
    monkeypatch.setattr(discovery, "SECURE_NOFOLLOW_AVAILABLE", False)

    with pytest.raises(discovery.SecureTraversalUnavailableError, match="unavailable"):
        discover_file_records([str(root)])
    with pytest.raises(discovery.SecureTraversalUnavailableError, match="unavailable"):
        discover_file_records([str(root / "*.txt")])
    # Even a glob without matches is not reported as an ordinary empty result.
    with pytest.raises(discovery.SecureTraversalUnavailableError):
        discover_file_records([str(root / "*.nomatch")])


def test_explicit_file_discovery_still_works_without_directory_primitives(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    target = tmp_path / "target.txt"
    target.write_text("explicit input", encoding="utf-8")
    link = tmp_path / "link.txt"
    link.symlink_to(target)
    monkeypatch.setattr(discovery, "SECURE_NOFOLLOW_AVAILABLE", False)

    records = discover_file_records([str(target), str(link), str(tmp_path / "absent.txt")])

    assert [record.path for record in records] == [target.resolve()]
    assert read_discovered_text(records[0]) == "explicit input"


def test_explicit_file_discovery_fails_explicitly_without_file_nofollow(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    target = tmp_path / "target.txt"
    target.write_text("explicit input", encoding="utf-8")
    monkeypatch.setattr(discovery, "FILE_NOFOLLOW_AVAILABLE", False)

    with pytest.raises(discovery.SecureTraversalUnavailableError):
        discover_file_records([str(target)])
    # A path that is not a file stays an ordinary non-match.
    assert discover_file_records([str(tmp_path / "absent.txt")]) == []


def test_search_cli_reports_unavailable_secure_traversal(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    from typer.testing import CliRunner

    from jev_cli.cli import app

    (tmp_path / "a.txt").write_text("decision", encoding="utf-8")
    monkeypatch.setattr(discovery, "SECURE_NOFOLLOW_AVAILABLE", False)

    result = CliRunner().invoke(app, ["search", "decision", str(tmp_path)])

    assert result.exit_code == 1, result.output
    assert isinstance(result.exception, SystemExit), repr(result.exception)
    assert "unavailable" in result.output
    assert "files_discovered" not in result.output


def test_glob_with_parent_relative_prefix_finds_siblings(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    work = tmp_path / "work"
    sibling = tmp_path / "sibling"
    work.mkdir()
    sibling.mkdir()
    (sibling / "a.txt").write_text("sibling text", encoding="utf-8")
    monkeypatch.chdir(work)

    records = discover_file_records(["../sibling/*.txt"])

    assert [record.path for record in records] == [(sibling / "a.txt").resolve()]
    assert records[0].root == sibling.resolve()
    assert records[0].relative_path == Path("a.txt")
    assert read_discovered_text(records[0]) == "sibling text"


def test_glob_with_symlinked_prefix_finds_files(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    real = tmp_path / "real"
    real.mkdir()
    (real / "nested").mkdir()
    (real / "nested" / "b.txt").write_text("nested text", encoding="utf-8")
    (real / "a.txt").write_text("top text", encoding="utf-8")
    (tmp_path / "link").symlink_to(real, target_is_directory=True)

    absolute = discover_file_records([str(tmp_path / "link" / "**" / "*.txt")])
    monkeypatch.chdir(tmp_path)
    relative = discover_file_records(["link/*.txt"])

    assert [record.path for record in absolute] == [
        (real / "a.txt").resolve(),
        (real / "nested" / "b.txt").resolve(),
    ]
    assert {record.root for record in absolute} == {real.resolve()}
    assert [record.relative_path for record in absolute] == [Path("a.txt"), Path("nested/b.txt")]
    assert [read_discovered_text(record) for record in absolute] == ["top text", "nested text"]
    assert [record.path for record in relative] == [(real / "a.txt").resolve()]
    assert read_discovered_text(relative[0]) == "top text"


@pytest.mark.parametrize("alias_first", [True, False])
def test_glob_internal_symlink_alias_cannot_replace_canonical_candidate(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch, alias_first: bool
) -> None:
    root = tmp_path / "repo"
    real_dir = root / "real_dir"
    real_dir.mkdir(parents=True)
    candidate = real_dir / "f.txt"
    candidate.write_text("canonical text", encoding="utf-8")
    (root / "alias").symlink_to(real_dir, target_is_directory=True)
    ordered = [str(root / "alias" / "f.txt"), str(candidate)]
    if not alias_first:
        ordered.reverse()
    monkeypatch.setattr(discovery.glob, "glob", lambda raw, recursive=True: list(ordered))

    records = discover_file_records([str(root / "*" / "f.txt")])

    assert [record.path for record in records] == [candidate.resolve()]
    assert records[0].relative_path == Path("real_dir/f.txt")
    assert read_discovered_text(records[0]) == "canonical text"


def test_glob_matching_only_an_internal_symlink_alias_is_rejected(tmp_path: Path) -> None:
    root = tmp_path / "repo"
    real_dir = root / "real_dir"
    real_dir.mkdir(parents=True)
    (real_dir / "f.txt").write_text("canonical text", encoding="utf-8")
    (root / "alias").symlink_to(real_dir, target_is_directory=True)

    assert discover_file_records([str(root / "a*" / "f.txt")]) == []


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
