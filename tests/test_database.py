import sqlite3

import pytest

from data.database import get_connection, initialize_database


def get_table_columns(db_path, table_name):
    with get_connection(db_path) as connection:
        rows = connection.execute(f"PRAGMA table_info({table_name});").fetchall()

    return {row["name"] for row in rows}


def insert_project(connection, project_id="project-1", name="Codebase Compass"):
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
            name,
            "Project description",
            "project.zip",
            123,
            "storage/uploads/project.zip",
            "storage/extracted/project",
            "2026-06-21T00:00:00+00:00",
            "2026-06-21T00:00:00+00:00",
        ),
    )


def insert_task(connection, task_id="task-1", project_id="project-1", title="Add login"):
    connection.execute(
        """
        INSERT INTO tasks (
            id,
            project_id,
            title,
            description,
            created_at,
            updated_at
        )
        VALUES (?, ?, ?, ?, ?, ?);
        """,
        (
            task_id,
            project_id,
            title,
            "Task description",
            "2026-06-21T00:00:00+00:00",
            "2026-06-21T00:00:00+00:00",
        ),
    )


def insert_project_ai_output(
    connection,
    output_id="output-1",
    project_id="project-1",
    output_type="codebase_overview",
):
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
            project_id,
            output_type,
            "Generated output",
            "2026-06-21T00:00:00+00:00",
            "2026-06-21T00:00:00+00:00",
        ),
    )


def test_initialize_database_creates_database_file(tmp_path):
    db_path = tmp_path / "test.db"

    initialize_database(db_path)

    assert db_path.exists()


def test_initialize_database_creates_parent_folder(tmp_path):
    db_path = tmp_path / "nested" / "test.db"

    initialize_database(db_path)

    assert db_path.parent.exists()
    assert db_path.exists()


def test_projects_table_has_expected_columns(tmp_path):
    db_path = tmp_path / "test.db"

    initialize_database(db_path)

    assert get_table_columns(db_path, "projects") == {
        "id",
        "name",
        "description",
        "original_zip_filename",
        "zip_file_size",
        "zip_path",
        "codebase_path",
        "created_at",
        "updated_at",
    }


def test_tasks_table_has_expected_columns(tmp_path):
    db_path = tmp_path / "test.db"

    initialize_database(db_path)

    assert get_table_columns(db_path, "tasks") == {
        "id",
        "project_id",
        "title",
        "description",
        "human_status",
        "goal",
        "subtasks_json",
        "subtask_sources_json",
        "completed_subtasks_json",
        "acceptance_criteria_json",
        "relevant_files_json",
        "ai_subtask_statuses_json",
        "created_at",
        "updated_at",
    }


def test_project_ai_outputs_table_has_expected_columns(tmp_path):
    db_path = tmp_path / "test.db"

    initialize_database(db_path)

    assert get_table_columns(db_path, "project_ai_outputs") == {
        "id",
        "project_id",
        "output_type",
        "content",
        "created_at",
        "updated_at",
    }


def test_initialize_database_is_idempotent(tmp_path):
    db_path = tmp_path / "test.db"

    initialize_database(db_path)
    initialize_database(db_path)

    assert db_path.exists()


def test_initialize_database_migrates_existing_tasks_table_with_subtask_sources(tmp_path):
    db_path = tmp_path / "test.db"

    with get_connection(db_path) as connection:
        connection.executescript(
            """
            CREATE TABLE tasks (
                id TEXT PRIMARY KEY,
                project_id TEXT NOT NULL,
                title TEXT NOT NULL,
                description TEXT NOT NULL DEFAULT '',
                human_status TEXT NOT NULL DEFAULT 'not_started',
                goal TEXT NOT NULL DEFAULT '',
                subtasks_json TEXT NOT NULL DEFAULT '[]',
                completed_subtasks_json TEXT NOT NULL DEFAULT '[]',
                acceptance_criteria_json TEXT NOT NULL DEFAULT '[]',
                relevant_files_json TEXT NOT NULL DEFAULT '[]',
                ai_subtask_statuses_json TEXT NOT NULL DEFAULT '{}',
                created_at TEXT NOT NULL,
                updated_at TEXT NOT NULL
            );
            """
        )

    initialize_database(db_path)

    assert "subtask_sources_json" in get_table_columns(db_path, "tasks")


def test_tasks_table_has_project_foreign_key(tmp_path):
    db_path = tmp_path / "test.db"
    initialize_database(db_path)

    with get_connection(db_path) as connection:
        foreign_keys = connection.execute("PRAGMA foreign_key_list(tasks);").fetchall()

    assert any(
        foreign_key["table"] == "projects"
        and foreign_key["from"] == "project_id"
        and foreign_key["to"] == "id"
        for foreign_key in foreign_keys
    )


def test_project_ai_outputs_table_has_project_foreign_key(tmp_path):
    db_path = tmp_path / "test.db"
    initialize_database(db_path)

    with get_connection(db_path) as connection:
        foreign_keys = connection.execute(
            "PRAGMA foreign_key_list(project_ai_outputs);"
        ).fetchall()

    assert any(
        foreign_key["table"] == "projects"
        and foreign_key["from"] == "project_id"
        and foreign_key["to"] == "id"
        for foreign_key in foreign_keys
    )


def test_project_names_must_be_unique(tmp_path):
    db_path = tmp_path / "test.db"
    initialize_database(db_path)

    with get_connection(db_path) as connection:
        insert_project(connection, project_id="project-1", name="Duplicate")
        with pytest.raises(sqlite3.IntegrityError):
            insert_project(connection, project_id="project-2", name="Duplicate")


def test_task_titles_must_be_unique_per_project(tmp_path):
    db_path = tmp_path / "test.db"
    initialize_database(db_path)

    with get_connection(db_path) as connection:
        insert_project(connection)
        insert_task(connection, task_id="task-1", project_id="project-1", title="Add login")

        with pytest.raises(sqlite3.IntegrityError):
            insert_task(connection, task_id="task-2", project_id="project-1", title="Add login")


def test_same_task_title_can_exist_under_different_projects(tmp_path):
    db_path = tmp_path / "test.db"
    initialize_database(db_path)

    with get_connection(db_path) as connection:
        insert_project(connection, project_id="project-1", name="First")
        insert_project(connection, project_id="project-2", name="Second")

        insert_task(connection, task_id="task-1", project_id="project-1", title="Add login")
        insert_task(connection, task_id="task-2", project_id="project-2", title="Add login")

        rows = connection.execute("SELECT id FROM tasks;").fetchall()

    assert len(rows) == 2


def test_project_ai_output_types_must_be_unique_per_project(tmp_path):
    db_path = tmp_path / "test.db"
    initialize_database(db_path)

    with get_connection(db_path) as connection:
        insert_project(connection)
        insert_project_ai_output(
            connection,
            output_id="output-1",
            project_id="project-1",
            output_type="codebase_overview",
        )

        with pytest.raises(sqlite3.IntegrityError):
            insert_project_ai_output(
                connection,
                output_id="output-2",
                project_id="project-1",
                output_type="codebase_overview",
            )


def test_same_project_can_have_multiple_ai_output_types(tmp_path):
    db_path = tmp_path / "test.db"
    initialize_database(db_path)

    with get_connection(db_path) as connection:
        insert_project(connection)
        insert_project_ai_output(
            connection,
            output_id="output-1",
            project_id="project-1",
            output_type="codebase_overview",
        )
        insert_project_ai_output(
            connection,
            output_id="output-2",
            project_id="project-1",
            output_type="setup_instructions",
        )

        rows = connection.execute("SELECT id FROM project_ai_outputs;").fetchall()

    assert len(rows) == 2


def test_same_ai_output_type_can_exist_under_different_projects(tmp_path):
    db_path = tmp_path / "test.db"
    initialize_database(db_path)

    with get_connection(db_path) as connection:
        insert_project(connection, project_id="project-1", name="First")
        insert_project(connection, project_id="project-2", name="Second")
        insert_project_ai_output(
            connection,
            output_id="output-1",
            project_id="project-1",
            output_type="codebase_overview",
        )
        insert_project_ai_output(
            connection,
            output_id="output-2",
            project_id="project-2",
            output_type="codebase_overview",
        )

        rows = connection.execute("SELECT id FROM project_ai_outputs;").fetchall()

    assert len(rows) == 2


def test_task_foreign_keys_are_enforced(tmp_path):
    db_path = tmp_path / "test.db"
    initialize_database(db_path)

    with get_connection(db_path) as connection:
        with pytest.raises(sqlite3.IntegrityError):
            insert_task(
                connection,
                task_id="task-1",
                project_id="missing-project",
                title="Add login",
            )


def test_project_ai_output_foreign_keys_are_enforced(tmp_path):
    db_path = tmp_path / "test.db"
    initialize_database(db_path)

    with get_connection(db_path) as connection:
        with pytest.raises(sqlite3.IntegrityError):
            insert_project_ai_output(
                connection,
                output_id="output-1",
                project_id="missing-project",
                output_type="codebase_overview",
            )
