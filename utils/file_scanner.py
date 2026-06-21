from pathlib import Path


SUPPORTED_EXTENSIONS = {
    ".py",
    ".js",
    ".jsx",
    ".ts",
    ".tsx",
    ".java",
    ".cs",
    ".cpp",
    ".c",
    ".h",
    ".html",
    ".css",
    ".sql",
    ".json",
    ".toml",
    ".yaml",
    ".yml",
    ".md",
    ".txt",
}

SUPPORTED_EXTENSIONLESS_FILENAMES = {
    "Dockerfile",
    "Makefile",
}

IGNORED_DIRECTORIES = {
    ".git",
    ".venv",
    "venv",
    "env",
    "node_modules",
    "__pycache__",
    "__MACOSX",
    ".pytest_cache",
    ".mypy_cache",
    ".idea",
    ".vscode",
    "dist",
    "build",
}


def scan_supported_files(codebase_path: str | Path) -> list[str]:
    codebase_root = Path(codebase_path)

    if not codebase_root.exists():
        raise RuntimeError(f"Codebase path does not exist: {codebase_root}")

    if not codebase_root.is_dir():
        raise RuntimeError(f"Codebase path is not a directory: {codebase_root}")

    supported_files = []

    for path in codebase_root.rglob("*"):
        relative_path = path.relative_to(codebase_root)

        if any(part in IGNORED_DIRECTORIES for part in relative_path.parts):
            continue

        if not path.is_file():
            continue

        if path.name.startswith("._") or path.name == ".DS_Store":
            continue

        if path.suffix.lower() in SUPPORTED_EXTENSIONS:
            supported_files.append(relative_path.as_posix())
            continue

        if path.name in SUPPORTED_EXTENSIONLESS_FILENAMES:
            supported_files.append(relative_path.as_posix())

    return sorted(supported_files)
