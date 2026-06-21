from pathlib import Path


def read_code_file(codebase_root_path: str | Path, relative_file_path: str | Path) -> str:
    codebase_root = Path(codebase_root_path)

    if not codebase_root.exists():
        raise RuntimeError(f"Codebase root does not exist: {codebase_root}")

    if not codebase_root.is_dir():
        raise RuntimeError(f"Codebase root is not a directory: {codebase_root}")

    resolved_codebase_root = codebase_root.resolve()
    resolved_file_path = (resolved_codebase_root / relative_file_path).resolve()

    if (
        resolved_file_path != resolved_codebase_root
        and resolved_codebase_root not in resolved_file_path.parents
    ):
        raise RuntimeError("Selected file path is outside the codebase.")

    if not resolved_file_path.exists():
        raise RuntimeError(f"Selected file does not exist: {relative_file_path}")

    if not resolved_file_path.is_file():
        raise RuntimeError(f"Selected path is not a file: {relative_file_path}")

    try:
        return resolved_file_path.read_text(encoding="utf-8")
    except UnicodeDecodeError as error:
        raise RuntimeError("Selected file is not readable as UTF-8 text.") from error
