from pathlib import Path

from jev_cli.discovery import chunk_text, discover_files, read_text
from jev_cli.retrieval.lexical import LexicalRetriever
from jev_cli.search import rank_chunks


def test_discovery_respects_common_ignored_dirs(tmp_path: Path) -> None:
    (tmp_path / "a.txt").write_text("decision contract", encoding="utf-8")
    hidden = tmp_path / "node_modules"
    hidden.mkdir()
    (hidden / "b.txt").write_text("decision contract", encoding="utf-8")
    files = discover_files([str(tmp_path)])
    assert [p.name for p in files] == ["a.txt"]


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
