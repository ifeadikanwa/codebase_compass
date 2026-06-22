import re
import shutil
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


def get_project_storage_folder(project: dict) -> Path | None:
    if project.get("zip_path"):
        return Path(project["zip_path"]).parent

    if project.get("codebase_path"):
        codebase_path = Path(project["codebase_path"])
        if codebase_path.name == "codebase":
            return codebase_path.parent
        return codebase_path

    return None


def is_safe_project_storage_folder(project_folder: Path | None) -> bool:
    if project_folder is None:
        return False

    resolved_folder = project_folder.resolve()
    resolved_projects_dir = PROJECTS_STORAGE_DIR.resolve()
    resolved_storage_dir = resolved_projects_dir.parent

    if resolved_folder in {resolved_folder.parent, resolved_storage_dir, resolved_projects_dir}:
        return False

    return resolved_projects_dir in resolved_folder.parents


def delete_project_storage(project: dict) -> bool:
    project_folder = get_project_storage_folder(project)

    if not is_safe_project_storage_folder(project_folder):
        return False

    if not project_folder.exists():
        return False

    shutil.rmtree(project_folder)
    return True
