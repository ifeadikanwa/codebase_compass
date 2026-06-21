from uuid import uuid4


def create_task(title, description=""):
    stripped_title = title.strip()
    stripped_description = description.strip()

    if not stripped_title:
        raise ValueError("Task title must not be empty.")

    return {
        "id": str(uuid4()),
        "title": stripped_title,
        "description": stripped_description,
        "human_status": "not_started",
        "subtasks": [],
        "completed_subtasks": [],
        "acceptance_criteria": [],
        "relevant_files": [],
    }


def normalize_task_title(title):
    return title.strip().lower()


def add_task_to_project(project, task):
    tasks = project.setdefault("tasks", [])
    new_task_title = normalize_task_title(task["title"])

    for existing_task in tasks:
        if normalize_task_title(existing_task["title"]) == new_task_title:
            raise ValueError("A task with this title already exists.")

    tasks.append(task)
    return project


def get_project_tasks(project):
    return project.get("tasks", [])


def apply_task_plan_to_task(task, task_plan):
    required_fields = [
        "goal",
        "subtasks",
        "acceptance_criteria",
        "relevant_files",
    ]

    for field in required_fields:
        if field not in task_plan:
            raise ValueError(f"Task plan is missing required field: {field}")

    task["goal"] = task_plan["goal"]
    task["subtasks"] = task_plan["subtasks"]
    task.setdefault("completed_subtasks", [])
    task["acceptance_criteria"] = task_plan["acceptance_criteria"]
    task["relevant_files"] = task_plan["relevant_files"]

    return task


def set_subtask_completion(task, subtask_index, is_complete):
    if "subtasks" not in task:
        raise ValueError("Task is missing subtasks.")

    if not isinstance(task["subtasks"], list):
        raise ValueError("Task subtasks must be a list.")

    if subtask_index < 0 or subtask_index >= len(task["subtasks"]):
        raise ValueError("Subtask index is invalid.")

    completed_subtasks = task.setdefault("completed_subtasks", [])

    if is_complete:
        if subtask_index not in completed_subtasks:
            completed_subtasks.append(subtask_index)
    elif subtask_index in completed_subtasks:
        completed_subtasks.remove(subtask_index)

    completed_subtasks.sort()

    completed_count = len(completed_subtasks)
    total_count = len(task["subtasks"])

    if completed_count == 0:
        task["human_status"] = "not_started"
    elif completed_count == total_count:
        task["human_status"] = "complete"
    else:
        task["human_status"] = "in_progress"

    return task
