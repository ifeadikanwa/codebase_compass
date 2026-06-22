import sqlite3
import uuid
from datetime import datetime, timezone

from data.database import DEFAULT_DB_PATH, get_connection, initialize_database


def row_to_project(row):
    if row is None:
        return None

    return {
        "id": row["id"],
        "name": row["name"],
        "description": row["description"],
        "original_zip_filename": row["original_zip_filename"],
        "zip_file_size": row["zip_file_size"],
        "zip_path": row["zip_path"],
        "codebase_path": row["codebase_path"],
        "created_at": row["created_at"],
        "updated_at": row["updated_at"],
    }


def create_project_record(
    name,
    description,
    original_zip_filename,
    zip_file_size,
    zip_path,
    codebase_path,
    db_path=DEFAULT_DB_PATH,
):
    cleaned_name = name.strip()
    cleaned_description = description.strip()
    cleaned_original_zip_filename = original_zip_filename.strip()
    cleaned_zip_path = str(zip_path).strip()
    cleaned_codebase_path = str(codebase_path).strip()

    if not cleaned_name:
        raise ValueError("Project name is required.")
    if not cleaned_original_zip_filename:
        raise ValueError("Original ZIP filename is required.")
    if not cleaned_zip_path:
        raise ValueError("ZIP path is required.")
    if not cleaned_codebase_path:
        raise ValueError("Codebase path is required.")
    if zip_file_size < 0:
        raise ValueError("ZIP file size cannot be negative.")

    initialize_database(db_path)

    project_id = str(uuid.uuid4())
    timestamp = datetime.now(timezone.utc).isoformat()

    try:
        with get_connection(db_path) as connection:
            connection.execute(
                """
                INSERT INTO projects (
                    id,
                    name,
                    description,
                    original_zip_filename,
                    zip_file_size,
                    zip_path,
                    codebase_path,
                    created_at,
                    updated_at
                )
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?);
                """,
                (
                    project_id,
                    cleaned_name,
                    cleaned_description,
                    cleaned_original_zip_filename,
                    zip_file_size,
                    cleaned_zip_path,
                    cleaned_codebase_path,
                    timestamp,
                    timestamp,
                ),
            )
    except sqlite3.IntegrityError as error:
        raise ValueError("A project with this name already exists.") from error

    return get_project_record_by_id(project_id, db_path=db_path)


def list_project_records(db_path=DEFAULT_DB_PATH):
    initialize_database(db_path)

    with get_connection(db_path) as connection:
        rows = connection.execute(
            "SELECT * FROM projects ORDER BY created_at ASC, name ASC;"
        ).fetchall()

    return [row_to_project(row) for row in rows]


def get_project_record_by_id(project_id, db_path=DEFAULT_DB_PATH):
    cleaned_project_id = project_id.strip()
    if not cleaned_project_id:
        raise ValueError("Project ID is required.")

    initialize_database(db_path)

    with get_connection(db_path) as connection:
        row = connection.execute(
            "SELECT * FROM projects WHERE id = ?;",
            (cleaned_project_id,),
        ).fetchone()

    return row_to_project(row)


def get_project_record_by_name(name, db_path=DEFAULT_DB_PATH):
    cleaned_name = name.strip()
    if not cleaned_name:
        raise ValueError("Project name is required.")

    initialize_database(db_path)

    with get_connection(db_path) as connection:
        row = connection.execute(
            "SELECT * FROM projects WHERE name = ?;",
            (cleaned_name,),
        ).fetchone()

    return row_to_project(row)


def update_project_record(project, db_path=DEFAULT_DB_PATH):
    if "id" not in project:
        raise ValueError("Project ID is required.")

    cleaned_project_id = project["id"].strip()
    if not cleaned_project_id:
        raise ValueError("Project ID is required.")

    if "name" not in project:
        raise ValueError("Project name is required.")

    cleaned_name = project["name"].strip()
    if not cleaned_name:
        raise ValueError("Project name is required.")

    cleaned_description = project.get("description", "").strip()
    existing_project = get_project_record_by_id(cleaned_project_id, db_path=db_path)
    if existing_project is None:
        return None

    timestamp = datetime.now(timezone.utc).isoformat()

    try:
        with get_connection(db_path) as connection:
            connection.execute(
                """
                UPDATE projects
                SET name = ?,
                    description = ?,
                    updated_at = ?
                WHERE id = ?;
                """,
                (cleaned_name, cleaned_description, timestamp, cleaned_project_id),
            )
    except sqlite3.IntegrityError as error:
        raise ValueError("A project with this name already exists.") from error

    return get_project_record_by_id(cleaned_project_id, db_path=db_path)


def delete_project_record(project_id, db_path=DEFAULT_DB_PATH):
    cleaned_project_id = project_id.strip()
    if not cleaned_project_id:
        raise ValueError("Project ID is required.")

    initialize_database(db_path)

    with get_connection(db_path) as connection:
        cursor = connection.execute(
            "DELETE FROM projects WHERE id = ?;",
            (cleaned_project_id,),
        )

    return cursor.rowcount > 0
