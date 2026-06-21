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
