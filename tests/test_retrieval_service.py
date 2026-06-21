import copy

import pytest

from services.retrieval_service import search_chunks


def make_chunk(file_path: str, content: str, start_line: int = 1, end_line: int = 1) -> dict:
    return {
        "file_path": file_path,
        "start_line": start_line,
        "end_line": end_line,
        "content": content,
    }


def test_search_chunks_matches_basic_query_terms():
    chunks = [
        make_chunk("services/auth_service.py", "def login_user(username, password):"),
        make_chunk("README.md", "Project documentation"),
    ]

    results = search_chunks("user login", chunks)

    assert len(results) == 1
    assert results[0]["file_path"] == "services/auth_service.py"
    assert results[0]["score"] == 2
    assert results[0]["matching_terms"] == ["login", "user"]


def test_search_chunks_matches_case_insensitively():
    chunks = [make_chunk("data/database.py", "database_connection = None")]

    results = search_chunks("DATABASE", chunks)

    assert len(results) == 1
    assert results[0]["matching_terms"] == ["database"]


def test_search_chunks_ignores_query_punctuation():
    chunks = [make_chunk("services/auth_service.py", "def login(): pass")]

    results = search_chunks("Where is login handled?", chunks)

    assert len(results) == 1
    assert results[0]["matching_terms"] == ["login"]


def test_search_chunks_splits_underscores():
    chunks = [make_chunk("services/auth_service.py", "def login_user(): pass")]

    results = search_chunks("login user", chunks)

    assert len(results) == 1
    assert results[0]["score"] == 2
    assert results[0]["matching_terms"] == ["login", "user"]


def test_search_chunks_scores_unique_matching_terms():
    chunks = [
        make_chunk("services/auth_service.py", "login login login user"),
        make_chunk("services/session_service.py", "login login login"),
    ]

    results = search_chunks("login user", chunks)

    assert [result["file_path"] for result in results] == [
        "services/auth_service.py",
        "services/session_service.py",
    ]
    assert [result["score"] for result in results] == [2, 1]


def test_search_chunks_orders_by_score_then_original_order():
    chunks = [
        make_chunk("first.py", "login"),
        make_chunk("second.py", "user login"),
        make_chunk("third.py", "login"),
    ]

    results = search_chunks("login user", chunks)

    assert [result["file_path"] for result in results] == [
        "second.py",
        "first.py",
        "third.py",
    ]


def test_search_chunks_respects_top_k():
    chunks = [
        make_chunk("first.py", "login"),
        make_chunk("second.py", "login"),
        make_chunk("third.py", "login"),
    ]

    results = search_chunks("login", chunks, top_k=2)

    assert [result["file_path"] for result in results] == ["first.py", "second.py"]


def test_search_chunks_does_not_mutate_input_chunks():
    chunks = [make_chunk("app.py", "login user")]
    original_chunks = copy.deepcopy(chunks)

    search_chunks("login", chunks)

    assert chunks == original_chunks


@pytest.mark.parametrize(
    "query",
    [
        "",
        "   ",
        "where is the",
    ],
)
def test_search_chunks_returns_empty_list_for_empty_or_stop_word_queries(query):
    chunks = [make_chunk("app.py", "login user")]

    assert search_chunks(query, chunks) == []


def test_search_chunks_returns_empty_list_for_empty_chunk_list():
    assert search_chunks("login", []) == []


def test_search_chunks_returns_empty_list_when_no_chunks_match():
    chunks = [make_chunk("app.py", "database connection")]

    assert search_chunks("login", chunks) == []


@pytest.mark.parametrize("top_k", [0, -1])
def test_search_chunks_rejects_invalid_top_k(top_k):
    with pytest.raises(ValueError, match="top_k"):
        search_chunks("login", [make_chunk("app.py", "login")], top_k=top_k)
