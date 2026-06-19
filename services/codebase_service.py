import re
import zipfile
from pathlib import Path


PROJECTS_STORAGE_DIR = Path("storage/projects")


def create_safe_project_folder_name(project_name: str) -> str:
    safe_name = project_name.strip().lower()
    safe_name = re.sub(r"[^a-z0-9]+", "_", safe_name)
    safe_name = safe_name.strip("_")

    if not safe_name:
        raise ValueError("Project name must contain at least one letter or number.")

    return safe_name


def save_project_zip(project_name: str, uploaded_file) -> str:
    safe_project_name = create_safe_project_folder_name(project_name)
    project_folder = PROJECTS_STORAGE_DIR / safe_project_name
    zip_path = project_folder / "codebase.zip"

    try:
        project_folder.mkdir(parents=True, exist_ok=True)
        zip_path.write_bytes(uploaded_file.getvalue())
    except OSError as error:
        raise RuntimeError(f"Could not save uploaded ZIP file: {error}") from error

    return str(zip_path)


def extract_project_zip(saved_zip_path: str) -> str:
    zip_path = Path(saved_zip_path)

    if not zip_path.exists():
        raise RuntimeError(f"ZIP file does not exist: {zip_path}")

    if not zipfile.is_zipfile(zip_path):
        raise RuntimeError("Uploaded file is not a valid ZIP file.")

    extraction_folder = zip_path.parent / "codebase"

    try:
        extraction_folder.mkdir(parents=True, exist_ok=True)
        extraction_root = extraction_folder.resolve()

        with zipfile.ZipFile(zip_path) as zip_file:
            for zip_entry in zip_file.infolist():
                destination_path = extraction_folder / zip_entry.filename
                resolved_destination_path = destination_path.resolve()

                if (
                    resolved_destination_path != extraction_root
                    and extraction_root not in resolved_destination_path.parents
                ):
                    raise RuntimeError(f"ZIP file contains an unsafe path: {zip_entry.filename}")

            zip_file.extractall(extraction_folder)
    except zipfile.BadZipFile as error:
        raise RuntimeError("Uploaded file is not a valid ZIP file.") from error
    except OSError as error:
        raise RuntimeError(f"Could not extract uploaded ZIP file: {error}") from error

    return str(extraction_folder)
