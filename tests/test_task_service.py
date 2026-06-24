import pytest

from services.task_service import (
    add_subtask_to_task,
    add_task_to_project,
    apply_ai_status_to_subtask,
    apply_task_plan_to_task,
    create_task,
    get_project_tasks,
    normalize_subtask_sources,
    set_subtask_completion,
    update_subtask_text,
)


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
    assert task["subtask_sources"] == []
    assert task["completed_subtasks"] == []
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


def test_apply_task_plan_to_task_updates_existing_task():
    task = create_task("Add login")
    task_plan = {
        "goal": "Add login support.",
        "subtasks": ["Update auth service"],
        "acceptance_criteria": ["Users can sign in"],
        "relevant_files": ["services/auth_service.py"],
    }

    updated_task = apply_task_plan_to_task(task, task_plan)

    assert updated_task is task
    assert task["goal"] == "Add login support."
    assert task["subtasks"] == ["Update auth service"]
    assert task["subtask_sources"] == ["generated"]
    assert task["acceptance_criteria"] == ["Users can sign in"]
    assert task["relevant_files"] == ["services/auth_service.py"]


@pytest.mark.parametrize(
    "missing_field",
    ["goal", "subtasks", "acceptance_criteria", "relevant_files"],
)
def test_apply_task_plan_to_task_rejects_missing_plan_fields(missing_field):
    task = create_task("Add login")
    task_plan = {
        "goal": "Add login support.",
        "subtasks": ["Update auth service"],
        "acceptance_criteria": ["Users can sign in"],
        "relevant_files": ["services/auth_service.py"],
    }
    del task_plan[missing_field]

    with pytest.raises(ValueError, match=missing_field):
        apply_task_plan_to_task(task, task_plan)


def make_task_with_subtasks():
    task = create_task("Add login")
    task["subtasks"] = ["Update auth service", "Add login form", "Add tests"]
    task["subtask_sources"] = ["generated", "generated", "generated"]
    return task


def test_add_subtask_to_task_adds_manual_subtask_and_preserves_state():
    task = make_task_with_subtasks()
    task["completed_subtasks"] = [0]
    task["ai_subtask_statuses"] = {0: make_ai_status_result()}

    add_subtask_to_task(task, "  Add password reset  ")

    assert task["subtasks"] == [
        "Update auth service",
        "Add login form",
        "Add tests",
        "Add password reset",
    ]
    assert task["subtask_sources"] == ["generated", "generated", "generated", "manual"]
    assert task["completed_subtasks"] == [0]
    assert task["ai_subtask_statuses"] == {0: make_ai_status_result()}


def test_update_subtask_text_marks_generated_subtask_manual_and_clears_ai_status():
    task = make_task_with_subtasks()
    task["ai_subtask_statuses"] = {1: make_ai_status_result(), 2: make_ai_status_result()}

    update_subtask_text(task, 1, "  Add login form and validation  ")

    assert task["subtasks"][1] == "Add login form and validation"
    assert task["subtask_sources"][1] == "manual"
    assert task["ai_subtask_statuses"] == {2: make_ai_status_result()}


def test_normalize_subtask_sources_defaults_missing_and_invalid_sources_to_generated():
    task = create_task("Add login")
    task["subtasks"] = ["First", "Second", "Third"]
    task["subtask_sources"] = ["manual", "bad-value"]

    normalize_subtask_sources(task)

    assert task["subtask_sources"] == ["manual", "generated", "generated"]


def test_set_subtask_completion_marks_one_subtask_complete():
    task = make_task_with_subtasks()

    updated_task = set_subtask_completion(task, 1, True)

    assert updated_task is task
    assert task["completed_subtasks"] == [1]
    assert task["human_status"] == "in_progress"


def test_set_subtask_completion_marks_all_subtasks_complete():
    task = make_task_with_subtasks()

    set_subtask_completion(task, 0, True)
    set_subtask_completion(task, 1, True)
    set_subtask_completion(task, 2, True)

    assert task["completed_subtasks"] == [0, 1, 2]
    assert task["human_status"] == "complete"


def test_set_subtask_completion_unchecks_completed_subtask():
    task = make_task_with_subtasks()
    set_subtask_completion(task, 0, True)
    set_subtask_completion(task, 1, True)

    set_subtask_completion(task, 1, False)

    assert task["completed_subtasks"] == [0]
    assert task["human_status"] == "in_progress"


def test_set_subtask_completion_unchecks_last_completed_subtask():
    task = make_task_with_subtasks()
    set_subtask_completion(task, 0, True)

    set_subtask_completion(task, 0, False)

    assert task["completed_subtasks"] == []
    assert task["human_status"] == "not_started"


def test_set_subtask_completion_does_not_duplicate_completed_indexes():
    task = make_task_with_subtasks()

    set_subtask_completion(task, 1, True)
    set_subtask_completion(task, 1, True)

    assert task["completed_subtasks"] == [1]


def test_set_subtask_completion_keeps_completed_indexes_sorted():
    task = make_task_with_subtasks()

    set_subtask_completion(task, 2, True)
    set_subtask_completion(task, 0, True)

    assert task["completed_subtasks"] == [0, 2]


@pytest.mark.parametrize("subtask_index", [-1, 3])
def test_set_subtask_completion_rejects_invalid_index(subtask_index):
    task = make_task_with_subtasks()

    with pytest.raises(ValueError, match="index"):
        set_subtask_completion(task, subtask_index, True)


def test_set_subtask_completion_rejects_missing_subtasks():
    task = create_task("Add login")
    del task["subtasks"]

    with pytest.raises(ValueError, match="subtasks"):
        set_subtask_completion(task, 0, True)


def test_set_subtask_completion_rejects_invalid_subtasks():
    task = create_task("Add login")
    task["subtasks"] = "not a list"

    with pytest.raises(ValueError, match="list"):
        set_subtask_completion(task, 0, True)


def make_ai_status_result():
    return {
        "status": "done",
        "reason": "The code appears to implement this subtask.",
        "relevant_files": ["app.py"],
    }


def test_apply_ai_status_to_subtask_creates_statuses_and_updates_existing_task():
    task = make_task_with_subtasks()
    status_result = make_ai_status_result()

    updated_task = apply_ai_status_to_subtask(task, 1, status_result)

    assert updated_task is task
    assert task["ai_subtask_statuses"] == {1: status_result}


def test_apply_ai_status_to_subtask_preserves_checked_at():
    task = make_task_with_subtasks()
    status_result = {
        **make_ai_status_result(),
        "checked_at": "2026-06-21T18:42:00+00:00",
    }

    apply_ai_status_to_subtask(task, 0, status_result)

    assert task["ai_subtask_statuses"][0]["checked_at"] == "2026-06-21T18:42:00+00:00"


def test_apply_ai_status_to_subtask_stores_multiple_subtask_statuses():
    task = make_task_with_subtasks()
    first_status = make_ai_status_result()
    second_status = {
        "status": "missing",
        "reason": "No matching implementation was found.",
        "relevant_files": [],
    }

    apply_ai_status_to_subtask(task, 0, first_status)
    apply_ai_status_to_subtask(task, 2, second_status)

    assert task["ai_subtask_statuses"] == {
        0: first_status,
        2: second_status,
    }


def test_apply_ai_status_to_subtask_does_not_affect_human_status_or_completed_subtasks():
    task = make_task_with_subtasks()
    set_subtask_completion(task, 0, True)
    original_human_status = task["human_status"]
    original_completed_subtasks = list(task["completed_subtasks"])

    apply_ai_status_to_subtask(task, 1, make_ai_status_result())

    assert task["human_status"] == original_human_status
    assert task["completed_subtasks"] == original_completed_subtasks


@pytest.mark.parametrize("subtask_index", [-1, 3])
def test_apply_ai_status_to_subtask_rejects_invalid_index(subtask_index):
    task = make_task_with_subtasks()

    with pytest.raises(ValueError, match="index"):
        apply_ai_status_to_subtask(task, subtask_index, make_ai_status_result())


def test_apply_ai_status_to_subtask_rejects_missing_subtasks():
    task = create_task("Add login")
    del task["subtasks"]

    with pytest.raises(ValueError, match="subtasks"):
        apply_ai_status_to_subtask(task, 0, make_ai_status_result())


def test_apply_ai_status_to_subtask_rejects_invalid_subtasks():
    task = create_task("Add login")
    task["subtasks"] = "not a list"

    with pytest.raises(ValueError, match="list"):
        apply_ai_status_to_subtask(task, 0, make_ai_status_result())


@pytest.mark.parametrize("missing_field", ["status", "reason", "relevant_files"])
def test_apply_ai_status_to_subtask_rejects_missing_status_fields(missing_field):
    task = make_task_with_subtasks()
    status_result = make_ai_status_result()
    del status_result[missing_field]

    with pytest.raises(ValueError, match=missing_field):
        apply_ai_status_to_subtask(task, 0, status_result)
