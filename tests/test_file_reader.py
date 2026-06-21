from pathlib import Path

import pytest

from utils.file_reader import read_code_file


def write_text_file(path: Path, content: str = "") -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(content, encoding="utf-8")


def test_read_code_file_reads_valid_file(tmp_path):
    codebase_root = tmp_path / "codebase"
    file_path = codebase_root / "services/auth_service.py"
    write_text_file(file_path, "def login():\n    return True\n")

    assert read_code_file(codebase_root, "services/auth_service.py") == (
        "def login():\n    return True\n"
    )


def test_read_code_file_reads_nested_file(tmp_path):
    codebase_root = tmp_path / "codebase"
    file_path = codebase_root / "src/app/services/auth.py"
    write_text_file(file_path, "AUTH_ENABLED = True\n")

    assert read_code_file(codebase_root, "src/app/services/auth.py") == "AUTH_ENABLED = True\n"


def test_read_code_file_reads_empty_file(tmp_path):
    codebase_root = tmp_path / "codebase"
    file_path = codebase_root / "README.md"
    write_text_file(file_path)

    assert read_code_file(codebase_root, "README.md") == ""


def test_read_code_file_rejects_missing_codebase_root(tmp_path):
    codebase_root = tmp_path / "missing"

    with pytest.raises(RuntimeError, match="does not exist"):
        read_code_file(codebase_root, "app.py")


def test_read_code_file_rejects_root_that_is_not_directory(tmp_path):
    codebase_root = tmp_path / "codebase.txt"
    write_text_file(codebase_root, "not a directory")

    with pytest.raises(RuntimeError, match="not a directory"):
        read_code_file(codebase_root, "app.py")


def test_read_code_file_rejects_missing_selected_file(tmp_path):
    codebase_root = tmp_path / "codebase"
    codebase_root.mkdir()

    with pytest.raises(RuntimeError, match="does not exist"):
        read_code_file(codebase_root, "missing.py")


def test_read_code_file_rejects_selected_path_that_is_directory(tmp_path):
    codebase_root = tmp_path / "codebase"
    selected_directory = codebase_root / "services"
    selected_directory.mkdir(parents=True)

    with pytest.raises(RuntimeError, match="not a file"):
        read_code_file(codebase_root, "services")


@pytest.mark.parametrize(
    "unsafe_path",
    [
        "../outside.py",
        "folder/../../outside.py",
    ],
)
def test_read_code_file_rejects_parent_directory_traversal(tmp_path, unsafe_path):
    codebase_root = tmp_path / "codebase"
    codebase_root.mkdir()
    outside_file = tmp_path / "outside.py"
    write_text_file(outside_file, "SECRET = True\n")

    with pytest.raises(RuntimeError, match="outside the codebase"):
        read_code_file(codebase_root, unsafe_path)

    assert outside_file.read_text(encoding="utf-8") == "SECRET = True\n"


def test_read_code_file_rejects_absolute_path(tmp_path):
    codebase_root = tmp_path / "codebase"
    codebase_root.mkdir()
    outside_file = tmp_path / "outside.py"
    write_text_file(outside_file, "SECRET = True\n")

    with pytest.raises(RuntimeError, match="outside the codebase"):
        read_code_file(codebase_root, outside_file)


def test_read_code_file_rejects_invalid_utf8(tmp_path):
    codebase_root = tmp_path / "codebase"
    file_path = codebase_root / "bad.py"
    file_path.parent.mkdir(parents=True, exist_ok=True)
    file_path.write_bytes(b"\xff\xfe\xfa")

    with pytest.raises(RuntimeError, match="UTF-8"):
        read_code_file(codebase_root, "bad.py")
