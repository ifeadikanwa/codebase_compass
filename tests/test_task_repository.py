import time

import pytest

from data.project_repository import create_project_record
from data.task_repository import (
    create_task_record,
    delete_task_record,
    get_task_record_by_id,
    list_task_records_for_project,
    update_task_record,
)


def create_sample_project(db_path, name="Good Shop"):
    return create_project_record(
        name=name,
        description="Command-line grocery shopping app",
        original_zip_filename="good_shop.zip",
        zip_file_size=12345,
        zip_path="storage/projects/good_shop/codebase.zip",
        codebase_path="storage/projects/good_shop/codebase",
        db_path=db_path,
    )


def make_task(task_id="task-1", title="Add login"):
    return {
        "id": task_id,
        "title": title,
        "description": " Users should be able to sign in. ",
    }


def make_full_task(task_id="task-1", title="Add login"):
    return {
        "id": task_id,
        "title": title,
        "description": " Users should be able to sign in. ",
        "human_status": "in_progress",
        "goal": "Clear goal text",
        "subtasks": ["Create login form"],
        "completed_subtasks": [0],
        "acceptance_criteria": ["User can log in"],
        "relevant_files": ["app.py"],
        "ai_subtask_statuses": {
            0: {
                "status": "missing",
                "reason": "No login form was found.",
                "relevant_files": [],
                "checked_at": "2026-06-21T18:42:00+00:00",
            }
        },
    }


def test_create_task_record_returns_saved_task_with_defaults(tmp_path):
    db_path = tmp_path / "test.db"
    project = create_sample_project(db_path)

    task = create_task_record(
        project["id"],
        {
            "id": "task-1",
            "title": "  Add login  ",
            "description": " Users should be able to sign in. ",
        },
        db_path=db_path,
    )

    assert task["id"] == "task-1"
    assert task["project_id"] == project["id"]
    assert task["title"] == "Add login"
    assert task["description"] == "Users should be able to sign in."
    assert task["human_status"] == "not_started"
    assert task["goal"] == ""
    assert task["subtasks"] == []
    assert task["completed_subtasks"] == []
    assert task["acceptance_criteria"] == []
    assert task["relevant_files"] == []
    assert task["ai_subtask_statuses"] == {}
    assert task["created_at"]
    assert task["updated_at"]


def test_create_task_record_saves_and_loads_json_fields(tmp_path):
    db_path = tmp_path / "test.db"
    project = create_sample_project(db_path)

    created_task = create_task_record(project["id"], make_full_task(), db_path=db_path)
    loaded_task = get_task_record_by_id(created_task["id"], db_path=db_path)

    assert loaded_task["subtasks"] == ["Create login form"]
    assert loaded_task["completed_subtasks"] == [0]
    assert loaded_task["acceptance_criteria"] == ["User can log in"]
    assert loaded_task["relevant_files"] == ["app.py"]
    assert loaded_task["ai_subtask_statuses"] == {
        0: {
            "status": "missing",
            "reason": "No login form was found.",
            "relevant_files": [],
            "checked_at": "2026-06-21T18:42:00+00:00",
        }
    }


@pytest.mark.parametrize("project_id", ["", "   "])
def test_create_task_record_rejects_empty_project_id(tmp_path, project_id):
    with pytest.raises(ValueError, match="Project ID"):
        create_task_record(project_id, make_task(), db_path=tmp_path / "test.db")


def test_create_task_record_rejects_missing_task_id(tmp_path):
    db_path = tmp_path / "test.db"
    project = create_sample_project(db_path)
    task = make_task()
    del task["id"]

    with pytest.raises(ValueError, match="id"):
        create_task_record(project["id"], task, db_path=db_path)


def test_create_task_record_rejects_missing_task_title(tmp_path):
    db_path = tmp_path / "test.db"
    project = create_sample_project(db_path)
    task = make_task()
    del task["title"]

    with pytest.raises(ValueError, match="title"):
        create_task_record(project["id"], task, db_path=db_path)


@pytest.mark.parametrize("title", ["", "   "])
def test_create_task_record_rejects_empty_task_title(tmp_path, title):
    db_path = tmp_path / "test.db"
    project = create_sample_project(db_path)

    with pytest.raises(ValueError, match="title"):
        create_task_record(project["id"], make_task(title=title), db_path=db_path)


def test_create_task_record_rejects_duplicate_title_for_same_project(tmp_path):
    db_path = tmp_path / "test.db"
    project = create_sample_project(db_path)
    create_task_record(project["id"], make_task(task_id="task-1", title="Add login"), db_path=db_path)

    with pytest.raises(ValueError, match="already exists"):
        create_task_record(
            project["id"],
            make_task(task_id="task-2", title="Add login"),
            db_path=db_path,
        )


def test_create_task_record_allows_same_title_for_different_projects(tmp_path):
    db_path = tmp_path / "test.db"
    first_project = create_sample_project(db_path, name="First")
    second_project = create_sample_project(db_path, name="Second")

    first_task = create_task_record(
        first_project["id"],
        make_task(task_id="task-1", title="Add login"),
        db_path=db_path,
    )
    second_task = create_task_record(
        second_project["id"],
        make_task(task_id="task-2", title="Add login"),
        db_path=db_path,
    )

    assert first_task["title"] == "Add login"
    assert second_task["title"] == "Add login"


def test_create_task_record_rejects_missing_project(tmp_path):
    with pytest.raises(ValueError, match="Project does not exist"):
        create_task_record(
            "missing-project",
            make_task(),
            db_path=tmp_path / "test.db",
        )


def test_list_task_records_for_project_returns_empty_list(tmp_path):
    db_path = tmp_path / "test.db"
    project = create_sample_project(db_path)

    assert list_task_records_for_project(project["id"], db_path=db_path) == []


def test_list_task_records_for_project_returns_only_project_tasks_in_order(tmp_path):
    db_path = tmp_path / "test.db"
    first_project = create_sample_project(db_path, name="First")
    second_project = create_sample_project(db_path, name="Second")
    first_task = create_task_record(
        first_project["id"],
        make_task(task_id="task-1", title="First task"),
        db_path=db_path,
    )
    second_task = create_task_record(
        first_project["id"],
        make_task(task_id="task-2", title="Second task"),
        db_path=db_path,
    )
    create_task_record(
        second_project["id"],
        make_task(task_id="task-3", title="Other project task"),
        db_path=db_path,
    )

    tasks = list_task_records_for_project(first_project["id"], db_path=db_path)

    assert tasks == [first_task, second_task]
    assert all(isinstance(task, dict) for task in tasks)


@pytest.mark.parametrize("project_id", ["", "   "])
def test_list_task_records_for_project_rejects_empty_project_id(tmp_path, project_id):
    with pytest.raises(ValueError, match="Project ID"):
        list_task_records_for_project(project_id, db_path=tmp_path / "test.db")


def test_get_task_record_by_id_returns_existing_task(tmp_path):
    db_path = tmp_path / "test.db"
    project = create_sample_project(db_path)
    task = create_task_record(project["id"], make_task(), db_path=db_path)

    assert get_task_record_by_id(task["id"], db_path=db_path) == task


def test_get_task_record_by_id_returns_none_for_missing_task(tmp_path):
    assert get_task_record_by_id("missing", db_path=tmp_path / "test.db") is None


@pytest.mark.parametrize("task_id", ["", "   "])
def test_get_task_record_by_id_rejects_empty_id(tmp_path, task_id):
    with pytest.raises(ValueError, match="Task ID"):
        get_task_record_by_id(task_id, db_path=tmp_path / "test.db")


def test_update_task_record_updates_task_fields(tmp_path):
    db_path = tmp_path / "test.db"
    project = create_sample_project(db_path)
    task = create_task_record(project["id"], make_task(), db_path=db_path)
    time.sleep(0.001)

    updated_task = update_task_record(
        {
            **task,
            "title": "Updated login",
            "description": "Updated description",
            "human_status": "complete",
            "goal": "Updated goal",
            "subtasks": ["Update login form"],
            "completed_subtasks": [0],
            "acceptance_criteria": ["User can sign in"],
            "relevant_files": ["app.py"],
            "ai_subtask_statuses": {
                0: {
                    "status": "done",
                    "reason": "Login form exists.",
                    "relevant_files": ["app.py"],
                    "checked_at": "2026-06-21T18:42:00+00:00",
                }
            },
        },
        db_path=db_path,
    )

    assert updated_task["title"] == "Updated login"
    assert updated_task["description"] == "Updated description"
    assert updated_task["human_status"] == "complete"
    assert updated_task["goal"] == "Updated goal"
    assert updated_task["subtasks"] == ["Update login form"]
    assert updated_task["completed_subtasks"] == [0]
    assert updated_task["acceptance_criteria"] == ["User can sign in"]
    assert updated_task["relevant_files"] == ["app.py"]
    assert updated_task["ai_subtask_statuses"] == {
        0: {
            "status": "done",
            "reason": "Login form exists.",
            "relevant_files": ["app.py"],
            "checked_at": "2026-06-21T18:42:00+00:00",
        }
    }
    assert updated_task["updated_at"] > task["updated_at"]


def test_update_task_record_updates_title_to_unique_title(tmp_path):
    db_path = tmp_path / "test.db"
    project = create_sample_project(db_path)
    task = create_task_record(project["id"], make_task(), db_path=db_path)

    updated_task = update_task_record(
        {
            **task,
            "title": "Updated login",
        },
        db_path=db_path,
    )

    assert updated_task["title"] == "Updated login"
    assert get_task_record_by_id(task["id"], db_path=db_path)["title"] == "Updated login"


def test_update_task_record_rejects_duplicate_title_for_same_project(tmp_path):
    db_path = tmp_path / "test.db"
    project = create_sample_project(db_path)
    first_task = create_task_record(
        project["id"],
        make_task(task_id="task-1", title="First task"),
        db_path=db_path,
    )
    second_task = create_task_record(
        project["id"],
        make_task(task_id="task-2", title="Second task"),
        db_path=db_path,
    )

    with pytest.raises(ValueError, match="already exists"):
        update_task_record({**second_task, "title": first_task["title"]}, db_path=db_path)

    assert get_task_record_by_id(first_task["id"], db_path=db_path) == first_task
    assert get_task_record_by_id(second_task["id"], db_path=db_path) == second_task


def test_update_task_record_returns_none_for_missing_task(tmp_path):
    assert update_task_record(make_task(), db_path=tmp_path / "test.db") is None


def test_update_task_record_rejects_missing_task_id(tmp_path):
    task = make_task()
    del task["id"]

    with pytest.raises(ValueError, match="id"):
        update_task_record(task, db_path=tmp_path / "test.db")


@pytest.mark.parametrize("title", ["", "   "])
def test_update_task_record_rejects_empty_title_when_provided(tmp_path, title):
    db_path = tmp_path / "test.db"
    project = create_sample_project(db_path)
    task = create_task_record(project["id"], make_task(), db_path=db_path)

    with pytest.raises(ValueError, match="title"):
        update_task_record({**task, "title": title}, db_path=db_path)


def test_task_records_persist_across_connections(tmp_path):
    db_path = tmp_path / "test.db"
    project = create_sample_project(db_path)
    task = create_task_record(project["id"], make_full_task(), db_path=db_path)

    loaded_task = get_task_record_by_id(task["id"], db_path=db_path)

    assert loaded_task == task


def test_delete_task_record_deletes_existing_task(tmp_path):
    db_path = tmp_path / "test.db"
    project = create_sample_project(db_path)
    task = create_task_record(project["id"], make_task(), db_path=db_path)

    deleted = delete_task_record(task["id"], db_path=db_path)

    assert deleted is True
    assert get_task_record_by_id(task["id"], db_path=db_path) is None
    assert list_task_records_for_project(project["id"], db_path=db_path) == []


def test_delete_task_record_returns_false_for_missing_task(tmp_path):
    assert delete_task_record("missing-task", db_path=tmp_path / "test.db") is False


@pytest.mark.parametrize("task_id", ["", "   "])
def test_delete_task_record_rejects_empty_id(tmp_path, task_id):
    with pytest.raises(ValueError, match="Task ID"):
        delete_task_record(task_id, db_path=tmp_path / "test.db")


def test_delete_task_record_deletes_only_one_task(tmp_path):
    db_path = tmp_path / "test.db"
    project = create_sample_project(db_path)
    first_task = create_task_record(
        project["id"],
        make_task(task_id="task-1", title="First task"),
        db_path=db_path,
    )
    second_task = create_task_record(
        project["id"],
        make_task(task_id="task-2", title="Second task"),
        db_path=db_path,
    )

    assert delete_task_record(first_task["id"], db_path=db_path) is True

    assert get_task_record_by_id(first_task["id"], db_path=db_path) is None
    assert get_task_record_by_id(second_task["id"], db_path=db_path) == second_task
    assert list_task_records_for_project(project["id"], db_path=db_path) == [second_task]


def test_delete_task_record_persists_across_connections(tmp_path):
    db_path = tmp_path / "test.db"
    project = create_sample_project(db_path)
    task = create_task_record(project["id"], make_task(), db_path=db_path)

    delete_task_record(task["id"], db_path=db_path)

    assert get_task_record_by_id(task["id"], db_path=db_path) is None
