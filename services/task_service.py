from uuid import uuid4


GENERATED_SUBTASK_SOURCE = "generated"
MANUAL_SUBTASK_SOURCE = "manual"
VALID_SUBTASK_SOURCES = {GENERATED_SUBTASK_SOURCE, MANUAL_SUBTASK_SOURCE}


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
        "subtask_sources": [],
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
    task["subtask_sources"] = [GENERATED_SUBTASK_SOURCE for _ in task["subtasks"]]
    task.setdefault("completed_subtasks", [])
    task["acceptance_criteria"] = task_plan["acceptance_criteria"]
    task["relevant_files"] = task_plan["relevant_files"]

    return task


def normalize_subtask_sources(task):
    subtasks = task.get("subtasks", [])
    if not isinstance(subtasks, list):
        raise ValueError("Task subtasks must be a list.")

    sources = task.get("subtask_sources", [])
    if not isinstance(sources, list):
        sources = []

    normalized_sources = []
    for index, _subtask in enumerate(subtasks):
        source = sources[index] if index < len(sources) else GENERATED_SUBTASK_SOURCE
        if source not in VALID_SUBTASK_SOURCES:
            source = GENERATED_SUBTASK_SOURCE
        normalized_sources.append(source)

    task["subtask_sources"] = normalized_sources
    return task


def add_subtask_to_task(task, text, source=MANUAL_SUBTASK_SOURCE):
    cleaned_text = text.strip()
    if not cleaned_text:
        raise ValueError("Subtask text must not be empty.")

    if source not in VALID_SUBTASK_SOURCES:
        raise ValueError("Subtask source is invalid.")

    subtasks = task.setdefault("subtasks", [])
    if not isinstance(subtasks, list):
        raise ValueError("Task subtasks must be a list.")

    normalize_subtask_sources(task)
    subtasks.append(cleaned_text)
    task["subtask_sources"].append(source)
    task.setdefault("completed_subtasks", [])
    task.setdefault("ai_subtask_statuses", {})
    return task


def update_subtask_text(task, index, text, source=MANUAL_SUBTASK_SOURCE):
    cleaned_text = text.strip()
    if not cleaned_text:
        raise ValueError("Subtask text must not be empty.")

    if source not in VALID_SUBTASK_SOURCES:
        raise ValueError("Subtask source is invalid.")

    subtasks = task.get("subtasks")
    if not isinstance(subtasks, list):
        raise ValueError("Task subtasks must be a list.")

    if index < 0 or index >= len(subtasks):
        raise ValueError("Subtask index is invalid.")

    normalize_subtask_sources(task)
    subtasks[index] = cleaned_text
    task["subtask_sources"][index] = source

    ai_subtask_statuses = task.setdefault("ai_subtask_statuses", {})
    ai_subtask_statuses.pop(index, None)
    ai_subtask_statuses.pop(str(index), None)
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


def apply_ai_status_to_subtask(task, subtask_index, status_result):
    if "subtasks" not in task:
        raise ValueError("Task is missing subtasks.")

    if not isinstance(task["subtasks"], list):
        raise ValueError("Task subtasks must be a list.")

    if subtask_index < 0 or subtask_index >= len(task["subtasks"]):
        raise ValueError("Subtask index is invalid.")

    required_fields = ["status", "reason", "relevant_files"]
    for field in required_fields:
        if field not in status_result:
            raise ValueError(f"AI status result is missing required field: {field}")

    ai_subtask_statuses = task.setdefault("ai_subtask_statuses", {})
    ai_subtask_statuses[subtask_index] = status_result

    return task
