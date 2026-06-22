import sqlite3
import uuid
from datetime import datetime, timezone

from data.database import DEFAULT_DB_PATH, get_connection, initialize_database


CODEBASE_OVERVIEW_OUTPUT_TYPE = "codebase_overview"


def _current_timestamp():
    return datetime.now(timezone.utc).isoformat()


def _validate_required_text(value, field_name):
    cleaned_value = value.strip()
    if not cleaned_value:
        raise ValueError(f"{field_name} is required.")

    return cleaned_value


def row_to_project_ai_output(row):
    if row is None:
        return None

    return {
        "id": row["id"],
        "project_id": row["project_id"],
        "output_type": row["output_type"],
        "content": row["content"],
        "created_at": row["created_at"],
        "updated_at": row["updated_at"],
    }


def save_project_ai_output(
    project_id,
    output_type,
    content,
    db_path=DEFAULT_DB_PATH,
):
    cleaned_project_id = _validate_required_text(project_id, "Project ID")
    cleaned_output_type = _validate_required_text(output_type, "Output type")
    if not content.strip():
        raise ValueError("Content is required.")

    initialize_database(db_path)

    existing_output = get_project_ai_output(
        cleaned_project_id,
        cleaned_output_type,
        db_path=db_path,
    )
    timestamp = _current_timestamp()

    try:
        with get_connection(db_path) as connection:
            if existing_output:
                connection.execute(
                    """
                    UPDATE project_ai_outputs
                    SET content = ?,
                        updated_at = ?
                    WHERE id = ?;
                    """,
                    (content, timestamp, existing_output["id"]),
                )
                output_id = existing_output["id"]
            else:
                output_id = str(uuid.uuid4())
                connection.execute(
                    """
                    INSERT INTO project_ai_outputs (
                        id,
                        project_id,
                        output_type,
                        content,
                        created_at,
                        updated_at
                    )
                    VALUES (?, ?, ?, ?, ?, ?);
                    """,
                    (
                        output_id,
                        cleaned_project_id,
                        cleaned_output_type,
                        content,
                        timestamp,
                        timestamp,
                    ),
                )
    except sqlite3.IntegrityError as error:
        if "FOREIGN KEY" in str(error):
            raise ValueError("Project does not exist.") from error
        raise

    return get_project_ai_output(
        cleaned_project_id,
        cleaned_output_type,
        db_path=db_path,
    )


def get_project_ai_output(
    project_id,
    output_type,
    db_path=DEFAULT_DB_PATH,
):
    cleaned_project_id = _validate_required_text(project_id, "Project ID")
    cleaned_output_type = _validate_required_text(output_type, "Output type")

    initialize_database(db_path)

    with get_connection(db_path) as connection:
        row = connection.execute(
            """
            SELECT * FROM project_ai_outputs
            WHERE project_id = ?
            AND output_type = ?;
            """,
            (cleaned_project_id, cleaned_output_type),
        ).fetchone()

    return row_to_project_ai_output(row)


def list_project_ai_outputs(project_id, db_path=DEFAULT_DB_PATH):
    cleaned_project_id = _validate_required_text(project_id, "Project ID")
    initialize_database(db_path)

    with get_connection(db_path) as connection:
        rows = connection.execute(
            """
            SELECT * FROM project_ai_outputs
            WHERE project_id = ?
            ORDER BY updated_at ASC, output_type ASC;
            """,
            (cleaned_project_id,),
        ).fetchall()

    return [row_to_project_ai_output(row) for row in rows]
