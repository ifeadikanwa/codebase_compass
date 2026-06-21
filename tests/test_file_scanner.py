from pathlib import Path

import pytest

from utils.file_scanner import scan_supported_files


def write_file(path: Path, content: str = "") -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(content)


def test_scan_supported_files_returns_supported_files(tmp_path):
    write_file(tmp_path / "app.py")
    write_file(tmp_path / "README.md")
    write_file(tmp_path / "services/auth_service.py")
    write_file(tmp_path / "config/settings.json")
    write_file(tmp_path / "Dockerfile")
    write_file(tmp_path / "Makefile")

    assert scan_supported_files(tmp_path) == [
        "Dockerfile",
        "Makefile",
        "README.md",
        "app.py",
        "config/settings.json",
        "services/auth_service.py",
    ]


def test_scan_supported_files_excludes_unsupported_files(tmp_path):
    write_file(tmp_path / "app.py")
    write_file(tmp_path / "image.png")
    write_file(tmp_path / "archive.zip")
    write_file(tmp_path / "database.db")
    write_file(tmp_path / "compiled.pyc")

    assert scan_supported_files(tmp_path) == ["app.py"]


def test_scan_supported_files_excludes_ignored_directories(tmp_path):
    write_file(tmp_path / "app.py")
    write_file(tmp_path / ".git/config")
    write_file(tmp_path / ".venv/lib/site.py")
    write_file(tmp_path / "node_modules/package/index.js")
    write_file(tmp_path / "__pycache__/app.py")
    write_file(tmp_path / "dist/bundle.js")
    write_file(tmp_path / "src/node_modules/package/index.js")

    assert scan_supported_files(tmp_path) == ["app.py"]


def test_scan_supported_files_excludes_macosx_metadata_directories(tmp_path):
    write_file(tmp_path / "app.py")
    write_file(tmp_path / "__MACOSX/._app.py")
    write_file(tmp_path / "__MACOSX/project/._service.java")
    write_file(tmp_path / "nested/__MACOSX/._README.md")

    assert scan_supported_files(tmp_path) == ["app.py"]


def test_scan_supported_files_excludes_macos_metadata_files(tmp_path):
    write_file(tmp_path / "app.py")
    write_file(tmp_path / "._app.py")
    write_file(tmp_path / "src/._service.java")
    write_file(tmp_path / "tests/._test_app.py")

    assert scan_supported_files(tmp_path) == ["app.py"]


def test_scan_supported_files_excludes_ds_store_files(tmp_path):
    write_file(tmp_path / "app.py")
    write_file(tmp_path / ".DS_Store")
    write_file(tmp_path / "src/.DS_Store")

    assert scan_supported_files(tmp_path) == ["app.py"]


def test_scan_supported_files_keeps_legitimate_underscore_filenames(tmp_path):
    write_file(tmp_path / "__init__.py")
    write_file(tmp_path / "_helpers.py")
    write_file(tmp_path / "src/user_service.py")

    assert scan_supported_files(tmp_path) == [
        "__init__.py",
        "_helpers.py",
        "src/user_service.py",
    ]


def test_scan_supported_files_returns_relative_forward_slash_sorted_paths(tmp_path):
    write_file(tmp_path / "zeta.py")
    write_file(tmp_path / "alpha.py")
    write_file(tmp_path / "services/auth_service.py")

    assert scan_supported_files(tmp_path) == [
        "alpha.py",
        "services/auth_service.py",
        "zeta.py",
    ]


def test_scan_supported_files_matches_extensions_case_insensitively(tmp_path):
    write_file(tmp_path / "SCRIPT.PY")
    write_file(tmp_path / "README.MD")

    assert scan_supported_files(tmp_path) == [
        "README.MD",
        "SCRIPT.PY",
    ]


def test_scan_supported_files_rejects_missing_path(tmp_path):
    missing_path = tmp_path / "missing"

    with pytest.raises(RuntimeError, match="does not exist"):
        scan_supported_files(missing_path)


def test_scan_supported_files_rejects_file_path(tmp_path):
    file_path = tmp_path / "app.py"
    write_file(file_path)

    with pytest.raises(RuntimeError, match="not a directory"):
        scan_supported_files(file_path)
