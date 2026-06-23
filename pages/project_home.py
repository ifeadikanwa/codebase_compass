from datetime import datetime, timezone
from pathlib import Path

import streamlit as st

from data.project_ai_output_repository import (
    CODEBASE_OVERVIEW_OUTPUT_TYPE,
    get_project_ai_output,
    save_project_ai_output,
)
from data.project_repository import get_project_record_by_id, get_project_record_by_name
from data.task_repository import (
    create_task_record,
    delete_task_record,
    list_task_records_for_project,
    update_task_record,
)
from services.llm_service import (
    answer_codebase_question,
    generate_codebase_overview,
    generate_subtask_status,
    generate_task_plan,
)
from services.retrieval_service import search_codebase
from services.task_service import (
    apply_ai_status_to_subtask,
    apply_task_plan_to_task,
    create_task,
    set_subtask_completion,
)
from utils.file_reader import read_code_file
from utils.file_scanner import scan_supported_files
from utils.markdown_formatter import normalize_generated_markdown
from utils.time_formatter import format_relative_time


LANGUAGE_BY_EXTENSION = {
    ".py": "python",
    ".js": "javascript",
    ".jsx": "javascript",
    ".ts": "typescript",
    ".tsx": "typescript",
    ".java": "java",
    ".cs": "csharp",
    ".cpp": "cpp",
    ".c": "c",
    ".h": "c",
    ".html": "html",
    ".css": "css",
    ".sql": "sql",
    ".json": "json",
    ".toml": "toml",
    ".yaml": "yaml",
    ".yml": "yaml",
    ".md": "markdown",
}

PROJECT_HOME_SECTION_KEY = "project_home_section"
CODEBASE_SECTION = "Codebase"
TASKS_SECTION = "Tasks"
CODEBASE_SUBSECTION_KEY = "codebase_subsection"
CODEBASE_OVERVIEW_SUBSECTION = "Overview"
CODEBASE_FILES_SUBSECTION = "Files"
CODEBASE_ASK_SUBSECTION = "Ask"
CODEBASE_EXPLAIN_SUBSECTION = "Explain"
CODEBASE_SUBSECTIONS = [
    CODEBASE_OVERVIEW_SUBSECTION,
    CODEBASE_FILES_SUBSECTION,
    CODEBASE_ASK_SUBSECTION,
    CODEBASE_EXPLAIN_SUBSECTION,
]

AI_STATUS_BADGE_STYLES = {
    "done": ("✓ Done", "#22C55E"),
    "partial": ("◐ Partial", "#F59E0B"),
    "missing": ("✕ Missing", "#EF4444"),
    "unclear": ("? Unclear", "#94A3B8"),
}


def format_file_size(size_bytes: int) -> str:
    if size_bytes < 1024:
        return f"{size_bytes} bytes"

    size_kb = size_bytes / 1024
    if size_kb < 1024:
        return f"{size_kb:.1f} KB"

    size_mb = size_kb / 1024
    return f"{size_mb:.1f} MB"


def render_workspace_heading(heading: str) -> None:
    st.markdown(
        f"<h2 style='color: #4DA3FF; margin-bottom: 0.75rem;'>{heading}</h2>",
        unsafe_allow_html=True,
    )


def get_selected_project() -> dict | None:
    selected_project_id = st.session_state.get("selected_project_id")
    selected_project_name = st.session_state.get("selected_project_name")

    try:
        if selected_project_id:
            project = get_project_record_by_id(selected_project_id)
            if project is not None:
                st.session_state["selected_project_name"] = project["name"]
                return project

        if selected_project_name:
            project = get_project_record_by_name(selected_project_name)
            if project is not None:
                st.session_state["selected_project_id"] = project["id"]
                return project
    except Exception:
        st.error("The selected project could not be loaded. Please return to My Projects.")
        return None

    return None


def return_to_projects() -> None:
    st.session_state.pop("selected_project_id", None)
    st.session_state.pop("selected_project_name", None)
    st.switch_page("pages/projects.py")


def get_language_for_file(file_path: str) -> str | None:
    return LANGUAGE_BY_EXTENSION.get(Path(file_path).suffix.lower())


def render_code_content(file_path: str, content: str) -> None:
    language = get_language_for_file(file_path)
    if language:
        st.code(content, language=language)
    else:
        st.code(content)


def render_selected_file(codebase_path: str, selected_file_path: str) -> None:
    try:
        file_contents = read_code_file(codebase_path, selected_file_path)
    except RuntimeError as error:
        st.error(f"Could not read selected file: {error}")
        return

    st.subheader(selected_file_path)
    render_code_content(selected_file_path, file_contents)


def find_readme_file(file_paths: list[str]) -> str | None:
    for file_path in file_paths:
        if Path(file_path).name.lower() in {"readme", "readme.md", "readme.txt"}:
            return file_path

    return None


def parse_iso_timestamp(timestamp: str | None):
    if not timestamp:
        return None

    try:
        normalized_timestamp = timestamp.replace("Z", "+00:00")
        parsed_timestamp = datetime.fromisoformat(normalized_timestamp)
    except ValueError:
        return None

    if parsed_timestamp.tzinfo is None:
        parsed_timestamp = parsed_timestamp.replace(tzinfo=timezone.utc)

    return parsed_timestamp


def is_overview_stale(selected_project: dict, saved_overview: dict) -> bool:
    project_updated_at = parse_iso_timestamp(selected_project.get("updated_at"))
    overview_updated_at = parse_iso_timestamp(saved_overview.get("updated_at"))

    if project_updated_at is None or overview_updated_at is None:
        return False

    return project_updated_at > overview_updated_at


def render_codebase_overview(selected_project: dict) -> None:
    st.subheader("Codebase Overview")
    st.write(
        "Generate a high-level summary of this project from the visible files and README."
    )

    codebase_path = selected_project.get("codebase_path")

    if not codebase_path:
        st.error("This project does not have a valid extracted codebase path.")
        return

    try:
        saved_overview = get_project_ai_output(
            selected_project["id"],
            CODEBASE_OVERVIEW_OUTPUT_TYPE,
        )
    except Exception:
        st.error("The saved codebase overview could not be loaded.")
        saved_overview = None

    try:
        supported_files = scan_supported_files(codebase_path)
    except RuntimeError as error:
        st.error(f"Could not scan codebase files: {error}")
        return

    if not supported_files:
        st.info(
            "No supported code files found.\n\n"
            "Make sure your ZIP contains files like .py, .js, .ts, .java, "
            ".md, .json, .sql, or other supported text/code files."
        )
        return

    overview_button_label = "Regenerate Overview" if saved_overview else "Generate Overview"

    if saved_overview:
        st.write(f"Generated {format_relative_time(saved_overview.get('updated_at'))}")

        if is_overview_stale(selected_project, saved_overview):
            st.warning(
                "This overview may be outdated because the project name or description "
                "was updated after it was generated. Regenerate the overview to refresh it."
            )

    if st.button(overview_button_label):
        readme_content = None
        readme_file_path = find_readme_file(supported_files)

        try:
            if readme_file_path:
                readme_content = read_code_file(codebase_path, readme_file_path)

            with st.spinner("Generating codebase overview..."):
                generated_overview = generate_codebase_overview(
                    selected_project["name"],
                    selected_project.get("description", ""),
                    supported_files,
                    readme_content=readme_content,
                )
        except Exception:
            st.error(
                "The codebase overview could not be generated. Please check your API key or try again."
            )
            return

        try:
            save_project_ai_output(
                selected_project["id"],
                CODEBASE_OVERVIEW_OUTPUT_TYPE,
                generated_overview,
            )
        except Exception:
            st.error("The codebase overview was generated but could not be saved. Please try again.")
            return

        st.rerun()

    if saved_overview:
        st.markdown(normalize_generated_markdown(saved_overview["content"]))
    else:
        st.info(
            "No overview generated yet.\n\n"
            "Generate an overview to summarize the project structure, important files, "
            "and how the codebase fits together."
        )


def render_codebase_files(selected_project: dict) -> None:
    st.subheader("Codebase Files")

    codebase_path = selected_project.get("codebase_path")

    if not codebase_path:
        st.error("This project does not have a valid extracted codebase path.")
        return

    try:
        supported_files = scan_supported_files(codebase_path)
    except RuntimeError as error:
        st.error(f"Could not scan codebase files: {error}")
        return

    if not supported_files:
        st.info(
            "No supported code files found.\n\n"
            "Make sure your ZIP contains files like .py, .js, .ts, .java, "
            ".md, .json, .sql, or other supported text/code files."
        )
        return

    st.write(f"{len(supported_files)} supported files found")

    file_options = ["Choose a file", *supported_files]
    selected_file_path = st.selectbox("Select a file", file_options)

    if selected_file_path == "Choose a file":
        return

    render_selected_file(codebase_path, selected_file_path)


def render_search_result(result: dict) -> None:
    with st.container(border=True):
        st.subheader(
            f"{result['file_path']} - Lines {result['start_line']}-{result['end_line']}"
        )
        st.write(f"Matching terms: {', '.join(result['matching_terms'])}")
        st.write(f"Score: {result['score']}")
        render_code_content(result["file_path"], result["content"])


def render_codebase_search(selected_project: dict) -> None:
    st.subheader("Ask Codebase")
    st.write("Search for relevant code sections using keywords.")
    st.caption(
        "Ask about project structure, files, functions, or where a feature should be added. "
        "Examples: Where is the cart logic? How does checkout work? Which files are relevant for adding login?"
    )

    codebase_path = selected_project.get("codebase_path")

    if not codebase_path:
        st.error("This project does not have a valid extracted codebase path.")
        return

    with st.form("search_codebase_form"):
        query = st.text_input(
            "Search query",
            placeholder="Where is user login handled?",
        )
        submitted = st.form_submit_button("Search")

    if not submitted:
        return

    cleaned_query = query.strip()

    if not cleaned_query:
        st.warning("Enter a search query.")
        return

    try:
        results = search_codebase(codebase_path, cleaned_query, top_k=5)
    except RuntimeError as error:
        st.error(f"Could not search codebase: {error}")
        return
    except ValueError as error:
        st.error(f"Could not search codebase: {error}")
        return

    if not results:
        st.info(
            "No relevant code sections found.\n\n"
            "Try using a filename, function name, class name, or more specific feature description."
        )
        return

    st.subheader("AI Answer")

    try:
        with st.spinner("Generating answer..."):
            answer = answer_codebase_question(cleaned_query, results)
    except Exception:
        st.error(
            "The AI answer could not be generated. Please check your API key or try again."
        )
    else:
        st.markdown(answer)

    st.subheader("Supporting Code Sections")
    st.write(f"{len(results)} matching code sections found")

    for result in results:
        render_search_result(result)


def render_codebase_explain_section() -> None:
    st.subheader("File Explanations")
    st.info(
        "File explanations will appear here.\n\n"
        "Next, this section will let you select a file, generate explanations for its "
        "classes, functions, variables, and important sections, then view those "
        "explanations in expandable cards."
    )


def render_project_home_section_switcher() -> str:
    if PROJECT_HOME_SECTION_KEY not in st.session_state:
        st.session_state[PROJECT_HOME_SECTION_KEY] = CODEBASE_SECTION

    selected_section = st.segmented_control(
        "Project section",
        [CODEBASE_SECTION, TASKS_SECTION],
        key=PROJECT_HOME_SECTION_KEY,
        label_visibility="collapsed",
    )

    if selected_section is None:
        selected_section = CODEBASE_SECTION

    return selected_section


def render_codebase_subsection_switcher() -> str:
    if CODEBASE_SUBSECTION_KEY not in st.session_state:
        st.session_state[CODEBASE_SUBSECTION_KEY] = CODEBASE_OVERVIEW_SUBSECTION

    if st.session_state[CODEBASE_SUBSECTION_KEY] not in CODEBASE_SUBSECTIONS:
        st.session_state[CODEBASE_SUBSECTION_KEY] = CODEBASE_OVERVIEW_SUBSECTION

    selected_subsection = st.segmented_control(
        "Codebase tool",
        CODEBASE_SUBSECTIONS,
        key=CODEBASE_SUBSECTION_KEY,
        label_visibility="collapsed",
    )

    if selected_subsection is None:
        selected_subsection = CODEBASE_OVERVIEW_SUBSECTION

    return selected_subsection


def render_codebase_section(selected_project: dict) -> None:
    render_workspace_heading("Codebase Workspace")

    active_subsection = render_codebase_subsection_switcher()

    if active_subsection == CODEBASE_FILES_SUBSECTION:
        render_codebase_files(selected_project)
    elif active_subsection == CODEBASE_ASK_SUBSECTION:
        render_codebase_search(selected_project)
    elif active_subsection == CODEBASE_EXPLAIN_SUBSECTION:
        render_codebase_explain_section()
    else:
        render_codebase_overview(selected_project)


def save_task_update(task: dict, success_message: str | None = None) -> bool:
    try:
        updated_task = update_task_record(task)
    except ValueError as error:
        st.error(f"Could not save task: {error}")
        return False
    except Exception:
        st.error("Task changes could not be saved. Please try again.")
        return False

    if updated_task is None:
        st.error("Task changes could not be saved because the task no longer exists.")
        return False

    if success_message:
        st.success(success_message)

    return True


def clear_pending_task_delete() -> None:
    st.session_state.pop("pending_delete_task_id", None)


def clear_task_editing() -> None:
    st.session_state.pop("editing_task_id", None)


def task_has_generated_content(task: dict) -> bool:
    return any(
        [
            task.get("goal"),
            task.get("subtasks"),
            task.get("acceptance_criteria"),
            task.get("relevant_files"),
            task.get("ai_subtask_statuses"),
        ]
    )


def reset_generated_task_fields(task: dict) -> dict:
    task["human_status"] = "not_started"
    task["goal"] = ""
    task["subtasks"] = []
    task["completed_subtasks"] = []
    task["acceptance_criteria"] = []
    task["relevant_files"] = []
    task["ai_subtask_statuses"] = {}
    return task


def delete_task(task: dict) -> None:
    try:
        deleted = delete_task_record(task["id"])
    except ValueError as error:
        st.error(f"Could not delete task: {error}")
        return
    except Exception:
        st.error("Task could not be deleted. Please try again.")
        return

    clear_pending_task_delete()

    if deleted:
        st.success("Task deleted.")
    else:
        st.warning("This task was already deleted.")

    st.rerun()


def render_task_edit_form(task: dict) -> None:
    st.write("Editing task")

    if task_has_generated_content(task):
        st.warning(
            "Changing the title or description will clear the generated plan, "
            "checkbox progress, and AI status for this task."
        )

    with st.form(f"edit_task_form_{task['id']}"):
        edited_title = st.text_input("Task Title", value=task["title"])
        edited_description = st.text_area(
            "Task Description",
            value=task.get("description", ""),
        )
        save_submitted = st.form_submit_button("Save Changes")
        cancel_submitted = st.form_submit_button("Cancel")

    if cancel_submitted:
        clear_task_editing()
        st.rerun()

    if not save_submitted:
        return

    cleaned_title = edited_title.strip()
    cleaned_description = edited_description.strip()

    if not cleaned_title:
        st.error("Task title is required.")
        return

    if cleaned_title == task["title"] and cleaned_description == task.get("description", ""):
        clear_task_editing()
        st.info("No task changes were made.")
        st.rerun()

    updated_task = {
        **task,
        "title": cleaned_title,
        "description": cleaned_description,
    }
    reset_generated_task_fields(updated_task)

    if not save_task_update(updated_task, success_message="Task updated."):
        return

    clear_task_editing()
    st.rerun()


def render_ai_status_badge(status_result: dict | None, relative_time: str | None = None) -> None:
    if status_result is None:
        label = "AI opinion: Not checked"
        color = "#94A3B8"
    else:
        status = status_result["status"]
        status_label, color = AI_STATUS_BADGE_STYLES.get(
            status,
            (status.title(), "#94A3B8"),
        )
        label = f"AI opinion: {status_label}"

    time_text = (
        f"<span style='margin-left:8px; color:#CBD5E1; font-size:0.85rem;'>{relative_time}</span>"
        if relative_time
        else ""
    )

    st.markdown(
        (
            f"<span style='display:inline-block; padding:2px 8px; "
            f"border-radius:999px; background:{color}; color:#0F172A; "
            f"font-size:0.8rem; font-weight:700;'>{label}</span>"
            f"{time_text}"
        ),
        unsafe_allow_html=True,
    )


def check_ai_status_for_subtask(
    selected_project: dict,
    task: dict,
    subtask_index: int,
    subtask: str,
) -> None:
    codebase_path = selected_project.get("codebase_path")
    if not codebase_path:
        st.error("This project does not have a valid extracted codebase path.")
        return

    query = f"{task['title']} {task.get('description', '')} {subtask}".strip()

    try:
        retrieved_chunks = search_codebase(codebase_path, query, top_k=5)
    except RuntimeError as error:
        st.error(f"Could not search codebase for AI status: {error}")
        return
    except ValueError as error:
        st.error(f"Could not search codebase for AI status: {error}")
        return

    checked_at = datetime.now(timezone.utc).isoformat()

    if not retrieved_chunks:
        status_result = {
            "status": "unclear",
            "reason": "No relevant code sections were found for this subtask.",
            "relevant_files": [],
            "checked_at": checked_at,
        }
    else:
        try:
            with st.spinner(""):
                status_result = generate_subtask_status(
                    selected_project["name"],
                    selected_project.get("description", ""),
                    task["title"],
                    task.get("description", ""),
                    subtask,
                    retrieved_chunks,
                )
        except Exception:
            st.error(
                "The AI status could not be checked. Please check your API key or try again."
            )
            return

        status_result["checked_at"] = checked_at

    try:
        apply_ai_status_to_subtask(task, subtask_index, status_result)
    except ValueError as error:
        st.error(f"Could not apply AI status: {error}")
        return

    if not save_task_update(task):
        return

    st.rerun()


def render_subtask_ai_status(
    selected_project: dict,
    task: dict,
    subtask_index: int,
    subtask: str,
) -> None:
    status_result = task.get("ai_subtask_statuses", {}).get(subtask_index)
    status_column, refresh_column = st.columns([0.88, 0.12])

    with status_column:
        relative_time = None
        if status_result and status_result.get("checked_at"):
            relative_time = format_relative_time(status_result["checked_at"])

        render_ai_status_badge(status_result, relative_time=relative_time)

    with refresh_column:
        if st.button(
            "↻",
            key=f"refresh_ai_status_{task['id']}_{subtask_index}",
            help="Refresh AI status for this subtask",
        ):
            check_ai_status_for_subtask(
                selected_project,
                task,
                subtask_index,
                subtask,
            )

    if status_result:
        with st.expander("AI details", expanded=False):
            st.write(f"Reason: {status_result['reason']}")

            if status_result["relevant_files"]:
                st.write("Relevant files:")
                for file_path in status_result["relevant_files"]:
                    st.markdown(f"- `{file_path}`")
            else:
                st.write("Relevant files: None")


def render_task_plan(selected_project: dict, task: dict) -> None:
    if "goal" in task:
        st.subheader("Goal")
        st.write(task["goal"])

    if task["subtasks"]:
        st.subheader("Subtasks")
        st.caption(
            "AI status checks each subtask against the current codebase. "
            "Refresh only the subtasks you want to re-check."
        )
        completed_subtasks = task.setdefault("completed_subtasks", [])
        for index, subtask in enumerate(task["subtasks"]):
            checked_value = st.checkbox(
                subtask,
                value=index in completed_subtasks,
                key=f"subtask_{task['id']}_{index}",
            )
            previous_completed_subtasks = list(completed_subtasks)
            previous_human_status = task["human_status"]
            set_subtask_completion(task, index, checked_value)

            if (
                task["completed_subtasks"] != previous_completed_subtasks
                or task["human_status"] != previous_human_status
            ):
                save_task_update(task)

            _, ai_column = st.columns([0.04, 0.96])
            with ai_column:
                render_subtask_ai_status(selected_project, task, index, subtask)

    if task["acceptance_criteria"]:
        st.subheader("Acceptance Criteria")
        for criterion in task["acceptance_criteria"]:
            st.markdown(f"- {criterion}")

    if task["relevant_files"]:
        st.subheader("Relevant Files")
        for file_path in task["relevant_files"]:
            st.markdown(f"- `{file_path}`")


def generate_plan_for_task(selected_project: dict, task: dict) -> None:
    codebase_path = selected_project.get("codebase_path")
    if not codebase_path:
        st.error("This project does not have a valid extracted codebase path.")
        return

    query = f"{task['title']} {task.get('description', '')}".strip()

    try:
        retrieved_chunks = search_codebase(codebase_path, query, top_k=5)
    except RuntimeError as error:
        st.error(f"Could not search codebase for task planning: {error}")
        return
    except ValueError as error:
        st.error(f"Could not search codebase for task planning: {error}")
        return

    if not retrieved_chunks:
        st.warning("No relevant code sections were found for this task.")
        return

    try:
        with st.spinner("Generating task plan..."):
            task_plan = generate_task_plan(
                selected_project["name"],
                selected_project.get("description", ""),
                task["title"],
                task.get("description", ""),
                retrieved_chunks,
            )
            apply_task_plan_to_task(task, task_plan)
    except ValueError as error:
        st.error(f"Could not apply task plan: {error}")
        return
    except Exception:
        st.error(
            "The task plan could not be generated. Please check your API key or try again."
        )
        return

    if not save_task_update(task, success_message="Task plan generated."):
        return

    st.rerun()


def render_task_card(selected_project: dict, task: dict) -> None:
    with st.container(border=True):
        st.subheader(task["title"])

        action_columns = st.columns([0.12, 0.12, 0.76])

        with action_columns[0]:
            if st.button("Edit", key=f"edit_task_{task['id']}"):
                st.session_state["editing_task_id"] = task["id"]
                clear_pending_task_delete()
                st.rerun()

        with action_columns[1]:
            if st.button("Delete", key=f"delete_task_{task['id']}"):
                st.session_state["pending_delete_task_id"] = task["id"]
                clear_task_editing()
                st.rerun()

        if st.session_state.get("editing_task_id") == task["id"]:
            render_task_edit_form(task)
            return

        if task["description"]:
            st.write(task["description"])

        st.write(f"Human status: {task['human_status']}")
        st.write(f"Subtasks: {len(task['subtasks'])}")
        st.write(f"Acceptance criteria: {len(task['acceptance_criteria'])}")
        st.write(f"Relevant files: {len(task['relevant_files'])}")

        if st.session_state.get("pending_delete_task_id") == task["id"]:
            st.warning("Delete this task? This cannot be undone.")
            confirm_column, cancel_column = st.columns(2)

            with confirm_column:
                if st.button(
                    "Confirm delete",
                    key=f"confirm_delete_task_{task['id']}",
                ):
                    delete_task(task)

            with cancel_column:
                if st.button("Cancel", key=f"cancel_delete_task_{task['id']}"):
                    clear_pending_task_delete()
                    st.rerun()

        st.caption(
            "Generate Plan uses the current codebase to suggest a goal, subtasks, "
            "acceptance criteria, and relevant files."
        )
        if st.button("Generate Plan", key=f"generate_plan_{task['id']}"):
            generate_plan_for_task(selected_project, task)

        render_task_plan(selected_project, task)


@st.dialog("Add Task")
def render_add_task_dialog(selected_project: dict) -> None:
    with st.form("create_task_form"):
        task_title = st.text_input("Task Title")
        task_description = st.text_area("Task Description")
        submitted = st.form_submit_button("Add Task")

    if not submitted:
        return

    try:
        task = create_task(task_title, task_description)
        create_task_record(selected_project["id"], task)
    except ValueError as error:
        st.error(f"Could not add task: {error}")
        return
    except Exception:
        st.error("Task could not be saved. Please try again.")
        return

    st.success("Task added.")
    st.rerun()


def render_tasks_section(selected_project: dict) -> None:
    render_workspace_heading("Task Workspace")
    st.subheader("Tasks")
    st.write("Create and manage development tasks for this project.")

    if st.button("Add Task"):
        render_add_task_dialog(selected_project)

    try:
        tasks = list_task_records_for_project(selected_project["id"])
    except Exception:
        st.error("Tasks could not be loaded. Please try again.")
        return

    if not tasks:
        st.info(
            "No tasks yet.\n\n"
            "Add a task you want to complete in this codebase. Codebase Compass can "
            "turn it into subtasks, acceptance criteria, and relevant files."
        )
        return

    for task in tasks:
        render_task_card(selected_project, task)


def main() -> None:
    selected_project = get_selected_project()

    if selected_project is None:
        st.write("No project is selected.")

        if st.button("Return to Projects"):
            return_to_projects()

        return

    if st.button("← My Projects"):
        return_to_projects()

    st.title(selected_project["name"])

    if selected_project["description"]:
        st.write(selected_project["description"])
    else:
        st.write("No description provided.")

    st.write(f"Uploaded ZIP: {selected_project['original_zip_filename']}")
    st.write(f"File size: {format_file_size(selected_project['zip_file_size'])}")
    st.write(f"Codebase path: {selected_project['codebase_path']}")

    active_section = render_project_home_section_switcher()

    if active_section == TASKS_SECTION:
        with st.container(border=True):
            render_tasks_section(selected_project)
    else:
        with st.container(border=True):
            render_codebase_section(selected_project)


main()
