import pytest

from services.retrieval_service import search_codebase


def write_file(path, content):
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(content, encoding="utf-8")


def test_search_codebase_searches_across_multiple_files(tmp_path):
    write_file(tmp_path / "app.py", "def main(): pass")
    write_file(tmp_path / "services/auth_service.py", "def login_user(username, password): pass")
    write_file(tmp_path / "data/database.py", "database_connection = None")
    write_file(tmp_path / "README.md", "Project docs")

    results = search_codebase(tmp_path, "user login")

    assert results
    assert results[0]["file_path"] == "services/auth_service.py"
    assert set(results[0]["matching_terms"]) == {"login", "user"}
    assert "login_user" in results[0]["content"]


def test_search_codebase_finds_nested_files(tmp_path):
    write_file(tmp_path / "src/services/auth/login_service.py", "def login_user(): pass")

    results = search_codebase(tmp_path, "login user")

    assert results[0]["file_path"] == "src/services/auth/login_service.py"


def test_search_codebase_returns_results_from_multiple_files_ordered_by_score(tmp_path):
    write_file(tmp_path / "auth.py", "login user")
    write_file(tmp_path / "session.py", "login")

    results = search_codebase(tmp_path, "login user")

    assert [result["file_path"] for result in results] == ["auth.py", "session.py"]
    assert [result["score"] for result in results] == [2, 1]


def test_search_codebase_preserves_line_range_metadata(tmp_path):
    lines = [f"line {number}" for number in range(1, 51)]
    lines[44] = "target_login_line = True"
    write_file(tmp_path / "large.py", "\n".join(lines))

    results = search_codebase(tmp_path, "target login")

    assert results[0]["file_path"] == "large.py"
    assert results[0]["start_line"] <= 45 <= results[0]["end_line"]
    assert "target_login_line" in results[0]["content"]


def test_search_codebase_ignores_ignored_directories(tmp_path):
    write_file(tmp_path / "node_modules/auth.js", "login user")
    write_file(tmp_path / "__MACOSX/._auth.py", "login user")
    write_file(tmp_path / ".venv/auth.py", "login user")

    assert search_codebase(tmp_path, "login user") == []


def test_search_codebase_ignores_unsupported_files(tmp_path):
    write_file(tmp_path / "image.png", "login user")
    write_file(tmp_path / "archive.zip", "login user")

    assert search_codebase(tmp_path, "login user") == []


@pytest.mark.parametrize("query", ["", "   "])
def test_search_codebase_returns_empty_list_for_empty_queries(tmp_path, query):
    write_file(tmp_path / "app.py", "login user")

    assert search_codebase(tmp_path, query) == []


def test_search_codebase_returns_empty_list_for_no_matches(tmp_path):
    write_file(tmp_path / "app.py", "database connection")

    assert search_codebase(tmp_path, "login") == []


def test_search_codebase_returns_empty_list_for_empty_codebase(tmp_path):
    assert search_codebase(tmp_path, "login") == []


def test_search_codebase_raises_for_missing_codebase_folder(tmp_path):
    with pytest.raises(RuntimeError, match="does not exist"):
        search_codebase(tmp_path / "missing", "login")


def test_search_codebase_respects_top_k(tmp_path):
    write_file(tmp_path / "one.py", "login")
    write_file(tmp_path / "two.py", "login")
    write_file(tmp_path / "three.py", "login")

    results = search_codebase(tmp_path, "login", top_k=2)

    assert len(results) == 2


@pytest.mark.parametrize("top_k", [0, -1])
def test_search_codebase_rejects_invalid_top_k(tmp_path, top_k):
    write_file(tmp_path / "app.py", "login")

    with pytest.raises(ValueError, match="top_k"):
        search_codebase(tmp_path, "login", top_k=top_k)
