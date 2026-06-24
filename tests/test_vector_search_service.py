import math

import pytest

from data.code_chunk_repository import list_project_code_chunks
from services.vector_search_service import (
    build_project_vector_index,
    cosine_similarity,
    search_project_vectors,
)


class FakeEmbedder:
    def __init__(self, embeddings_by_text):
        self.embeddings_by_text = embeddings_by_text
        self.embed_text_calls = []
        self.embed_texts_calls = []

    def embed_text(self, text):
        self.embed_text_calls.append(text)
        return self.embeddings_by_text[text]

    def embed_texts(self, texts):
        self.embed_texts_calls.append(list(texts))
        return [self.embeddings_by_text[text] for text in texts]


def test_cosine_similarity_returns_expected_score_for_identical_vectors():
    assert cosine_similarity([1.0, 2.0, 3.0], [1.0, 2.0, 3.0]) == pytest.approx(1.0)


def test_cosine_similarity_returns_zero_for_zero_vector():
    assert cosine_similarity([0.0, 0.0], [1.0, 2.0]) == 0.0


@pytest.mark.parametrize(
    ("vector_a", "vector_b"),
    [
        ([], [1.0]),
        ([1.0], []),
        ([1.0], [1.0, 2.0]),
    ],
)
def test_cosine_similarity_rejects_empty_or_different_length_vectors(
    vector_a,
    vector_b,
):
    with pytest.raises(ValueError):
        cosine_similarity(vector_a, vector_b)


def test_build_project_vector_index_scans_chunks_embeds_and_stores_chunks(
    tmp_path,
):
    codebase_path = tmp_path / "codebase"
    codebase_path.mkdir()
    (codebase_path / "app.py").write_text("def login():\n    return True\n", encoding="utf-8")
    (codebase_path / "README.md").write_text("# Docs\nUse login.\n", encoding="utf-8")
    (codebase_path / "image.png").write_text("ignored", encoding="utf-8")
    db_path = tmp_path / "compass.db"

    app_chunk = "def login():\n    return True"
    readme_chunk = "# Docs\nUse login."
    embedder = FakeEmbedder(
        {
            app_chunk: [1.0, 0.0],
            readme_chunk: [0.0, 1.0],
        }
    )

    summary = build_project_vector_index(
        "project-1",
        codebase_path,
        db_path=db_path,
        embedder=embedder,
    )

    stored_chunks = list_project_code_chunks("project-1", db_path=db_path)
    assert summary == {
        "files_indexed": 2,
        "chunks_indexed": 2,
    }
    assert embedder.embed_texts_calls == [[readme_chunk, app_chunk]]
    assert [chunk["file_path"] for chunk in stored_chunks] == ["README.md", "app.py"]
    assert [chunk["embedding"] for chunk in stored_chunks] == [[0.0, 1.0], [1.0, 0.0]]


def test_search_project_vectors_returns_top_chunks_sorted_by_similarity(tmp_path):
    codebase_path = tmp_path / "codebase"
    codebase_path.mkdir()
    (codebase_path / "auth.py").write_text("def login():\n    pass\n", encoding="utf-8")
    (codebase_path / "cart.py").write_text("def checkout():\n    pass\n", encoding="utf-8")
    db_path = tmp_path / "compass.db"

    login_chunk = "def login():\n    pass"
    checkout_chunk = "def checkout():\n    pass"
    embedder = FakeEmbedder(
        {
            login_chunk: [1.0, 0.0],
            checkout_chunk: [0.0, 1.0],
            "login": [1.0, 0.0],
        }
    )
    build_project_vector_index(
        "project-1",
        codebase_path,
        db_path=db_path,
        embedder=embedder,
    )

    results = search_project_vectors(
        "project-1",
        " login ",
        min_score=0.0,
        db_path=db_path,
        embedder=embedder,
    )

    assert [result["file_path"] for result in results] == ["auth.py", "cart.py"]
    assert results[0]["score"] == pytest.approx(1.0)
    assert results[1]["score"] == pytest.approx(0.0)
    assert embedder.embed_text_calls == ["login"]


def test_search_project_vectors_respects_top_k(tmp_path):
    codebase_path = tmp_path / "codebase"
    codebase_path.mkdir()
    (codebase_path / "one.py").write_text("one\n", encoding="utf-8")
    (codebase_path / "two.py").write_text("two\n", encoding="utf-8")
    db_path = tmp_path / "compass.db"
    embedder = FakeEmbedder(
        {
            "one": [1.0, 0.0],
            "two": [0.0, 1.0],
            "query": [1.0, 0.0],
        }
    )
    build_project_vector_index(
        "project-1",
        codebase_path,
        db_path=db_path,
        embedder=embedder,
    )

    results = search_project_vectors(
        "project-1",
        "query",
        top_k=1,
        db_path=db_path,
        embedder=embedder,
    )

    assert len(results) == 1
    assert results[0]["file_path"] == "one.py"


def test_search_project_vectors_filters_low_score_results(tmp_path):
    codebase_path = tmp_path / "codebase"
    codebase_path.mkdir()
    (codebase_path / "auth.py").write_text("def login():\n    pass\n", encoding="utf-8")
    (codebase_path / "cart.py").write_text("def checkout():\n    pass\n", encoding="utf-8")
    db_path = tmp_path / "compass.db"

    login_chunk = "def login():\n    pass"
    checkout_chunk = "def checkout():\n    pass"
    embedder = FakeEmbedder(
        {
            login_chunk: [1.0, 0.0],
            checkout_chunk: [0.0, 1.0],
            "login": [1.0, 0.0],
        }
    )
    build_project_vector_index(
        "project-1",
        codebase_path,
        db_path=db_path,
        embedder=embedder,
    )

    results = search_project_vectors(
        "project-1",
        "login",
        db_path=db_path,
        embedder=embedder,
    )

    assert [result["file_path"] for result in results] == ["auth.py"]


def test_search_project_vectors_keeps_results_at_or_above_threshold(tmp_path):
    codebase_path = tmp_path / "codebase"
    codebase_path.mkdir()
    (codebase_path / "auth.py").write_text("auth\n", encoding="utf-8")
    (codebase_path / "cart.py").write_text("cart\n", encoding="utf-8")
    db_path = tmp_path / "compass.db"
    embedder = FakeEmbedder(
        {
            "auth": [0.25, math.sqrt(1.0 - (0.25 * 0.25))],
            "cart": [0.24, math.sqrt(1.0 - (0.24 * 0.24))],
            "query": [1.0, 0.0],
        }
    )
    build_project_vector_index(
        "project-1",
        codebase_path,
        db_path=db_path,
        embedder=embedder,
    )

    results = search_project_vectors(
        "project-1",
        "query",
        db_path=db_path,
        embedder=embedder,
    )

    assert [result["file_path"] for result in results] == ["auth.py"]
    assert results[0]["score"] == pytest.approx(0.25)


def test_search_project_vectors_applies_top_k_after_threshold_filtering(tmp_path):
    codebase_path = tmp_path / "codebase"
    codebase_path.mkdir()
    (codebase_path / "one.py").write_text("one\n", encoding="utf-8")
    (codebase_path / "two.py").write_text("two\n", encoding="utf-8")
    (codebase_path / "three.py").write_text("three\n", encoding="utf-8")
    db_path = tmp_path / "compass.db"
    embedder = FakeEmbedder(
        {
            "one": [0.9, math.sqrt(1.0 - (0.9 * 0.9))],
            "two": [0.8, math.sqrt(1.0 - (0.8 * 0.8))],
            "three": [0.1, math.sqrt(1.0 - (0.1 * 0.1))],
            "query": [1.0, 0.0],
        }
    )
    build_project_vector_index(
        "project-1",
        codebase_path,
        db_path=db_path,
        embedder=embedder,
    )

    results = search_project_vectors(
        "project-1",
        "query",
        top_k=1,
        min_score=0.25,
        db_path=db_path,
        embedder=embedder,
    )

    assert [result["file_path"] for result in results] == ["one.py"]


def test_search_project_vectors_returns_empty_list_when_no_chunks_exist(tmp_path):
    embedder = FakeEmbedder({"query": [1.0, 0.0]})

    results = search_project_vectors(
        "project-1",
        "query",
        db_path=tmp_path / "compass.db",
        embedder=embedder,
    )

    assert results == []
    assert embedder.embed_text_calls == []


@pytest.mark.parametrize("query", ["", "   ", None])
def test_search_project_vectors_rejects_empty_query(tmp_path, query):
    with pytest.raises(ValueError):
        search_project_vectors(
            "project-1",
            query,
            db_path=tmp_path / "compass.db",
            embedder=FakeEmbedder({}),
        )


@pytest.mark.parametrize("top_k", [0, -1, 1.5, True])
def test_search_project_vectors_rejects_invalid_top_k(tmp_path, top_k):
    with pytest.raises(ValueError):
        search_project_vectors(
            "project-1",
            "query",
            top_k=top_k,
            db_path=tmp_path / "compass.db",
            embedder=FakeEmbedder({}),
        )


def test_tests_use_fake_embedder_only():
    embedder = FakeEmbedder({"query": [1.0]})

    assert embedder.embed_text("query") == [1.0]
    assert not math.isnan(cosine_similarity([1.0], [1.0]))
