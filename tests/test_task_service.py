import pytest

from services.task_service import add_task_to_project, create_task, get_project_tasks


def test_create_task_creates_valid_task():
    task = create_task(
        "  Add user login  ",
        "  Users should be able to sign in and sign out.  ",
    )

    assert task["id"]
    assert task["title"] == "Add user login"
    assert task["description"] == "Users should be able to sign in and sign out."
    assert task["human_status"] == "not_started"
    assert task["subtasks"] == []
    assert task["acceptance_criteria"] == []
    assert task["relevant_files"] == []


@pytest.mark.parametrize("title", ["", "   "])
def test_create_task_rejects_empty_title(title):
    with pytest.raises(ValueError, match="title"):
        create_task(title)


def test_create_task_generates_unique_ids():
    first_task = create_task("First task")
    second_task = create_task("Second task")

    assert first_task["id"] != second_task["id"]


def test_add_task_to_project_adds_task_and_creates_task_list():
    project = {"name": "Codebase Compass"}
    task = create_task("Add user login")

    updated_project = add_task_to_project(project, task)

    assert updated_project is project
    assert project["tasks"] == [task]


def test_add_task_to_project_preserves_existing_tasks():
    existing_task = create_task("Existing task")
    project = {"name": "Codebase Compass", "tasks": [existing_task]}
    new_task = create_task("New task")

    add_task_to_project(project, new_task)

    assert project["tasks"] == [existing_task, new_task]


def test_add_task_to_project_rejects_duplicate_task_title():
    project = {"name": "Codebase Compass", "tasks": [create_task("Add Login")]}
    duplicate_task = create_task("  add login  ")

    with pytest.raises(ValueError, match="already exists"):
        add_task_to_project(project, duplicate_task)


def test_get_project_tasks_returns_existing_tasks():
    tasks = [create_task("Existing task")]
    project = {"name": "Codebase Compass", "tasks": tasks}

    assert get_project_tasks(project) is tasks


def test_get_project_tasks_returns_empty_list_when_missing():
    project = {"name": "Codebase Compass"}

    assert get_project_tasks(project) == []


def test_get_project_tasks_does_not_mutate_project_when_missing():
    project = {"name": "Codebase Compass"}

    get_project_tasks(project)

    assert "tasks" not in project
