from io import BytesIO
from pathlib import Path
import zipfile

import pytest

from services.codebase_service import (
    create_safe_project_folder_name,
    delete_project_storage,
    extract_project_zip,
    save_project_zip,
)


class UploadedFileStub:
    def __init__(self, content: bytes) -> None:
        self._content = content

    def getvalue(self) -> bytes:
        return self._content


def create_zip_file(zip_path: Path, files: dict[str, str]) -> None:
    with zipfile.ZipFile(zip_path, "w") as zip_file:
        for filename, content in files.items():
            zip_file.writestr(filename, content)


def create_zip_bytes(files: dict[str, str]) -> bytes:
    buffer = BytesIO()

    with zipfile.ZipFile(buffer, "w") as zip_file:
        for filename, content in files.items():
            zip_file.writestr(filename, content)

    return buffer.getvalue()


@pytest.mark.parametrize(
    ("project_name", "expected_folder_name"),
    [
        ("My Grocery App", "my_grocery_app"),
        ("Budget Planner!! 2026", "budget_planner_2026"),
    ],
)
def test_create_safe_project_folder_name(project_name, expected_folder_name):
    assert create_safe_project_folder_name(project_name) == expected_folder_name


def test_save_project_zip_creates_project_folder_and_saves_uploaded_bytes(tmp_path, monkeypatch):
    monkeypatch.chdir(tmp_path)
    uploaded_bytes = create_zip_bytes({"app.py": "print('hello')"})
    uploaded_file = UploadedFileStub(uploaded_bytes)

    saved_path = save_project_zip("My Grocery App", uploaded_file)

    saved_zip_path = Path(saved_path)
    assert saved_zip_path == Path("storage/projects/my_grocery_app/codebase.zip")
    assert saved_zip_path.exists()
    assert saved_zip_path.read_bytes() == uploaded_bytes


def test_extract_project_zip_extracts_valid_zip_with_nested_files(tmp_path):
    project_folder = tmp_path / "storage/projects/my_project"
    project_folder.mkdir(parents=True)
    zip_path = project_folder / "codebase.zip"

    create_zip_file(
        zip_path,
        {
            "app.py": "print('hello')",
            "services/auth_service.py": "def login(): pass",
            "README.md": "# Example",
        },
    )

    extraction_path = extract_project_zip(str(zip_path))

    extraction_folder = Path(extraction_path)
    assert extraction_folder == project_folder / "codebase"
    assert extraction_folder.exists()
    assert (extraction_folder / "app.py").read_text() == "print('hello')"
    assert (extraction_folder / "services/auth_service.py").read_text() == "def login(): pass"
    assert (extraction_folder / "README.md").read_text() == "# Example"


def test_extract_project_zip_rejects_missing_zip_path(tmp_path):
    missing_zip_path = tmp_path / "missing.zip"

    with pytest.raises(RuntimeError, match="ZIP file does not exist"):
        extract_project_zip(str(missing_zip_path))


def test_extract_project_zip_rejects_non_zip_file(tmp_path):
    invalid_zip_path = tmp_path / "codebase.zip"
    invalid_zip_path.write_text("not a zip file")

    with pytest.raises(RuntimeError, match="not a valid ZIP"):
        extract_project_zip(str(invalid_zip_path))


@pytest.mark.parametrize(
    "unsafe_filename",
    [
        "../outside.txt",
        "folder/../../outside.txt",
    ],
)
def test_extract_project_zip_rejects_unsafe_paths_before_extracting(tmp_path, unsafe_filename):
    project_folder = tmp_path / "storage/projects/my_project"
    project_folder.mkdir(parents=True)
    zip_path = project_folder / "codebase.zip"

    create_zip_file(
        zip_path,
        {
            "safe.txt": "safe content",
            unsafe_filename: "unsafe content",
        },
    )

    with pytest.raises(RuntimeError, match="unsafe path"):
        extract_project_zip(str(zip_path))

    assert not (tmp_path / "storage/projects/outside.txt").exists()
    assert not (tmp_path / "storage/outside.txt").exists()
    assert not (tmp_path / "outside.txt").exists()
    assert not (project_folder / "codebase/safe.txt").exists()


def test_delete_project_storage_deletes_existing_project_folder(tmp_path, monkeypatch):
    monkeypatch.chdir(tmp_path)
    project_folder = tmp_path / "storage" / "projects" / "sample_project"
    project_folder.mkdir(parents=True)
    zip_path = project_folder / "codebase.zip"
    codebase_path = project_folder / "codebase"
    codebase_path.mkdir()
    zip_path.write_bytes(b"zip bytes")

    deleted = delete_project_storage(
        {
            "zip_path": str(zip_path),
            "codebase_path": str(codebase_path),
        }
    )

    assert deleted is True
    assert not project_folder.exists()


def test_delete_project_storage_returns_false_when_folder_is_missing(tmp_path, monkeypatch):
    monkeypatch.chdir(tmp_path)
    project_folder = tmp_path / "storage" / "projects" / "sample_project"

    deleted = delete_project_storage(
        {
            "zip_path": str(project_folder / "codebase.zip"),
            "codebase_path": str(project_folder / "codebase"),
        }
    )

    assert deleted is False


@pytest.mark.parametrize(
    "unsafe_path_factory",
    [
        lambda tmp_path: tmp_path,
        lambda tmp_path: tmp_path / "storage",
        lambda tmp_path: tmp_path / "storage" / "projects",
    ],
)
def test_delete_project_storage_refuses_unsafe_broad_paths(
    tmp_path,
    monkeypatch,
    unsafe_path_factory,
):
    monkeypatch.chdir(tmp_path)
    unsafe_path = unsafe_path_factory(tmp_path)
    unsafe_path.mkdir(parents=True, exist_ok=True)
    marker_file = unsafe_path / "keep.txt"
    marker_file.write_text("keep")

    deleted = delete_project_storage({"zip_path": str(unsafe_path / "codebase.zip")})

    assert deleted is False
    assert marker_file.exists()
