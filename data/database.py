import sqlite3
from pathlib import Path


DEFAULT_DB_PATH = Path("storage/codebase_compass.db")


def get_connection(db_path=DEFAULT_DB_PATH):
    db_path = Path(db_path)
    db_path.parent.mkdir(parents=True, exist_ok=True)

    connection = sqlite3.connect(db_path)
    connection.execute("PRAGMA foreign_keys = ON;")
    connection.row_factory = sqlite3.Row
    return connection


def initialize_database(db_path=DEFAULT_DB_PATH):
    connection = get_connection(db_path)

    try:
        connection.executescript(
            """
            CREATE TABLE IF NOT EXISTS projects (
                id TEXT PRIMARY KEY,
                name TEXT NOT NULL UNIQUE,
                description TEXT NOT NULL DEFAULT '',
                original_zip_filename TEXT NOT NULL,
                zip_file_size INTEGER NOT NULL,
                zip_path TEXT NOT NULL,
                codebase_path TEXT NOT NULL,
                created_at TEXT NOT NULL,
                updated_at TEXT NOT NULL
            );

            CREATE TABLE IF NOT EXISTS tasks (
                id TEXT PRIMARY KEY,
                project_id TEXT NOT NULL,
                title TEXT NOT NULL,
                description TEXT NOT NULL DEFAULT '',
                human_status TEXT NOT NULL DEFAULT 'not_started',
                goal TEXT NOT NULL DEFAULT '',
                subtasks_json TEXT NOT NULL DEFAULT '[]',
                subtask_sources_json TEXT NOT NULL DEFAULT '[]',
                completed_subtasks_json TEXT NOT NULL DEFAULT '[]',
                acceptance_criteria_json TEXT NOT NULL DEFAULT '[]',
                relevant_files_json TEXT NOT NULL DEFAULT '[]',
                ai_subtask_statuses_json TEXT NOT NULL DEFAULT '{}',
                created_at TEXT NOT NULL,
                updated_at TEXT NOT NULL,
                FOREIGN KEY (project_id) REFERENCES projects(id) ON DELETE CASCADE,
                UNIQUE(project_id, title)
            );

            CREATE TABLE IF NOT EXISTS project_ai_outputs (
                id TEXT PRIMARY KEY,
                project_id TEXT NOT NULL,
                output_type TEXT NOT NULL,
                content TEXT NOT NULL,
                created_at TEXT NOT NULL,
                updated_at TEXT NOT NULL,
                FOREIGN KEY (project_id) REFERENCES projects(id) ON DELETE CASCADE,
                UNIQUE(project_id, output_type)
            );
            """
        )
        _ensure_column(
            connection,
            "tasks",
            "subtask_sources_json",
            "TEXT NOT NULL DEFAULT '[]'",
        )
        connection.commit()
    finally:
        connection.close()


def _ensure_column(connection, table_name, column_name, column_definition):
    rows = connection.execute(f"PRAGMA table_info({table_name});").fetchall()
    existing_columns = {row["name"] for row in rows}

    if column_name not in existing_columns:
        connection.execute(
            f"ALTER TABLE {table_name} ADD COLUMN {column_name} {column_definition};"
        )
