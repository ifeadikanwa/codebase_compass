import json
import sqlite3
from datetime import datetime, timezone

from data.database import DEFAULT_DB_PATH, get_connection, initialize_database


def _current_timestamp():
    return datetime.now(timezone.utc).isoformat()


def _require_text(value, field_name):
    if field_name not in value:
        raise ValueError(f"Task is missing required field: {field_name}")

    cleaned_value = value[field_name].strip()
    if not cleaned_value:
        raise ValueError(f"Task {field_name} is required.")

    return cleaned_value


def _validate_project_id(project_id):
    cleaned_project_id = project_id.strip()
    if not cleaned_project_id:
        raise ValueError("Project ID is required.")

    return cleaned_project_id


def _json_dumps(value):
    return json.dumps(value)


def _json_loads(value, default):
    if not value:
        return default

    return json.loads(value)


def _restore_ai_status_keys(ai_subtask_statuses):
    restored_statuses = {}

    for key, value in ai_subtask_statuses.items():
        restored_key = int(key) if isinstance(key, str) and key.isdigit() else key
        restored_statuses[restored_key] = value

    return restored_statuses


def row_to_task(row):
    if row is None:
        return None

    ai_subtask_statuses = _json_loads(row["ai_subtask_statuses_json"], {})

    return {
        "id": row["id"],
        "project_id": row["project_id"],
        "title": row["title"],
        "description": row["description"],
        "human_status": row["human_status"],
        "goal": row["goal"],
        "subtasks": _json_loads(row["subtasks_json"], []),
        "subtask_sources": _json_loads(row["subtask_sources_json"], []),
        "completed_subtasks": _json_loads(row["completed_subtasks_json"], []),
        "acceptance_criteria": _json_loads(row["acceptance_criteria_json"], []),
        "relevant_files": _json_loads(row["relevant_files_json"], []),
        "ai_subtask_statuses": _restore_ai_status_keys(ai_subtask_statuses),
        "created_at": row["created_at"],
        "updated_at": row["updated_at"],
    }


def create_task_record(project_id, task, db_path=DEFAULT_DB_PATH):
    cleaned_project_id = _validate_project_id(project_id)
    task_id = _require_text(task, "id")
    title = _require_text(task, "title")
    description = task.get("description", "").strip()
    timestamp = _current_timestamp()

    initialize_database(db_path)

    try:
        with get_connection(db_path) as connection:
            connection.execute(
                """
                INSERT INTO tasks (
                    id,
                    project_id,
                    title,
                    description,
                    human_status,
                    goal,
                    subtasks_json,
                    subtask_sources_json,
                    completed_subtasks_json,
                    acceptance_criteria_json,
                    relevant_files_json,
                    ai_subtask_statuses_json,
                    created_at,
                    updated_at
                )
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?);
                """,
                (
                    task_id,
                    cleaned_project_id,
                    title,
                    description,
                    task.get("human_status", "not_started"),
                    task.get("goal", ""),
                    _json_dumps(task.get("subtasks", [])),
                    _json_dumps(task.get("subtask_sources", [])),
                    _json_dumps(task.get("completed_subtasks", [])),
                    _json_dumps(task.get("acceptance_criteria", [])),
                    _json_dumps(task.get("relevant_files", [])),
                    _json_dumps(task.get("ai_subtask_statuses", {})),
                    timestamp,
                    timestamp,
                ),
            )
    except sqlite3.IntegrityError as error:
        error_message = str(error)
        if "FOREIGN KEY" in error_message:
            raise ValueError("Project does not exist.") from error
        if "UNIQUE" in error_message:
            raise ValueError("A task with this title already exists for this project.") from error
        raise

    return get_task_record_by_id(task_id, db_path=db_path)


def list_task_records_for_project(project_id, db_path=DEFAULT_DB_PATH):
    cleaned_project_id = _validate_project_id(project_id)
    initialize_database(db_path)

    with get_connection(db_path) as connection:
        rows = connection.execute(
            """
            SELECT * FROM tasks
            WHERE project_id = ?
            ORDER BY created_at ASC, title ASC;
            """,
            (cleaned_project_id,),
        ).fetchall()

    return [row_to_task(row) for row in rows]


def get_task_record_by_id(task_id, db_path=DEFAULT_DB_PATH):
    cleaned_task_id = task_id.strip()
    if not cleaned_task_id:
        raise ValueError("Task ID is required.")

    initialize_database(db_path)

    with get_connection(db_path) as connection:
        row = connection.execute(
            "SELECT * FROM tasks WHERE id = ?;",
            (cleaned_task_id,),
        ).fetchone()

    return row_to_task(row)


def update_task_record(task, db_path=DEFAULT_DB_PATH):
    task_id = _require_text(task, "id")

    existing_task = get_task_record_by_id(task_id, db_path=db_path)
    if existing_task is None:
        return None

    title = task.get("title", existing_task["title"]).strip()
    if not title:
        raise ValueError("Task title is required.")

    updated_task = {
        **existing_task,
        **task,
        "id": task_id,
        "title": title,
        "description": task.get("description", existing_task["description"]).strip(),
        "updated_at": _current_timestamp(),
    }

    try:
        with get_connection(db_path) as connection:
            connection.execute(
                """
                UPDATE tasks
                SET title = ?,
                    description = ?,
                    human_status = ?,
                    goal = ?,
                    subtasks_json = ?,
                    subtask_sources_json = ?,
                    completed_subtasks_json = ?,
                    acceptance_criteria_json = ?,
                    relevant_files_json = ?,
                    ai_subtask_statuses_json = ?,
                    updated_at = ?
                WHERE id = ?;
                """,
                (
                    updated_task["title"],
                    updated_task["description"],
                    updated_task.get("human_status", "not_started"),
                    updated_task.get("goal", ""),
                    _json_dumps(updated_task.get("subtasks", [])),
                    _json_dumps(updated_task.get("subtask_sources", [])),
                    _json_dumps(updated_task.get("completed_subtasks", [])),
                    _json_dumps(updated_task.get("acceptance_criteria", [])),
                    _json_dumps(updated_task.get("relevant_files", [])),
                    _json_dumps(updated_task.get("ai_subtask_statuses", {})),
                    updated_task["updated_at"],
                    task_id,
                ),
            )
    except sqlite3.IntegrityError as error:
        if "UNIQUE" in str(error):
            raise ValueError("A task with this title already exists for this project.") from error
        raise

    return get_task_record_by_id(task_id, db_path=db_path)


def delete_task_record(task_id, db_path=DEFAULT_DB_PATH):
    cleaned_task_id = task_id.strip()
    if not cleaned_task_id:
        raise ValueError("Task ID is required.")

    initialize_database(db_path)

    with get_connection(db_path) as connection:
        cursor = connection.execute(
            "DELETE FROM tasks WHERE id = ?;",
            (cleaned_task_id,),
        )

    return cursor.rowcount > 0
