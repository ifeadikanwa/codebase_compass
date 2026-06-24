import html

import streamlit as st

from data.project_repository import (
    create_project_record,
    delete_project_record,
    get_project_record_by_name,
    list_project_records,
    update_project_record,
)
from data.task_repository import list_task_records_for_project
from services.codebase_service import delete_project_storage, extract_project_zip, save_project_zip
from utils.time_formatter import format_relative_time


def format_file_size(size_bytes: int) -> str:
    if size_bytes < 1024:
        return f"{size_bytes} bytes"

    size_kb = size_bytes / 1024
    if size_kb < 1024:
        return f"{size_kb:.1f} KB"

    size_mb = size_kb / 1024
    return f"{size_mb:.1f} MB"


def render_muted_meta(text) -> None:
    safe_text = html.escape(str(text))
    st.markdown(
        f"""
        <p style="
            color: #A0A7B4;
            font-size: 0.85rem;
            line-height: 1.3;
            margin: 0.25rem 0 0.75rem 0;
        ">
            {safe_text}
        </p>
        """,
        unsafe_allow_html=True,
    )


def render_project_detail(label: str, value) -> None:
    safe_label = html.escape(str(label))
    safe_value = html.escape(str(value or "Unknown"))
    st.markdown(
        f"""
        <p style="margin: 0.75rem 0 0.15rem 0;"><strong>{safe_label}</strong></p>
        <p style="color: #A0A7B4; margin: 0;">{safe_value}</p>
        """,
        unsafe_allow_html=True,
    )


def initialize_session_state() -> None:
    if "projects" not in st.session_state:
        st.session_state["projects"] = []


def load_projects() -> list[dict]:
    try:
        projects = list_project_records()
    except Exception:
        st.error("Projects could not be loaded. Please try again.")
        return []

    st.session_state["projects"] = projects
    return projects


def project_name_exists(project_name: str) -> bool:
    return get_project_record_by_name(project_name) is not None


def get_project_task_count(project: dict) -> str:
    try:
        return str(len(list_task_records_for_project(project["id"])))
    except Exception:
        return "unavailable"


def get_project_file_size(project: dict) -> str:
    zip_file_size = project.get("zip_file_size")
    return format_file_size(zip_file_size) if isinstance(zip_file_size, int) else "Unknown"


def open_project(project: dict) -> None:
    st.session_state["selected_project_id"] = project["id"]
    st.session_state["selected_project_name"] = project["name"]
    st.switch_page("pages/project_home.py")


def render_project_card_title(project: dict) -> None:
    safe_project_name = html.escape(project.get("name") or "Untitled Project")
    st.markdown(f"### {safe_project_name}", unsafe_allow_html=True)


def render_project_card_summary(project: dict) -> None:
    description = project.get("description") or "No description provided."
    task_count = get_project_task_count(project)
    updated_time = format_relative_time(project.get("updated_at"))

    safe_description = html.escape(description)
    safe_task_count = html.escape(task_count)
    safe_updated_time = html.escape(updated_time)

    st.markdown(
        f"""
        <div>
            <p style="margin: 0.35rem 0 0.75rem 0;">
                {safe_description}
            </p>
            <p style="
                color: #A0A7B4;
                font-size: 0.85rem;
                line-height: 1.3;
                margin: 0.25rem 0 0.75rem 0;
            ">
                Tasks: {safe_task_count} &nbsp;•&nbsp; Updated {safe_updated_time}
            </p>
        </div>
        """,
        unsafe_allow_html=True,
    )


def clear_pending_project_delete() -> None:
    st.session_state.pop("pending_delete_project_id", None)


def clear_project_editing() -> None:
    st.session_state.pop("editing_project_id", None)


def clear_selected_project_if_deleted(project: dict) -> None:
    if st.session_state.get("selected_project_id") == project["id"]:
        st.session_state.pop("selected_project_id", None)

    if st.session_state.get("selected_project_name") == project["name"]:
        st.session_state.pop("selected_project_name", None)


def delete_project(project: dict) -> None:
    try:
        deleted = delete_project_record(project["id"])
    except ValueError as error:
        st.error(f"Could not delete project: {error}")
        return
    except Exception:
        st.error("Project could not be deleted. Please try again.")
        return

    clear_pending_project_delete()
    clear_selected_project_if_deleted(project)

    if not deleted:
        st.warning("This project was already deleted.")
        st.rerun()
        return

    try:
        storage_deleted = delete_project_storage(project)
    except Exception:
        st.warning("Project was deleted, but storage cleanup may not have completed.")
        st.rerun()
        return

    if storage_deleted:
        st.success("Project deleted.")
    else:
        st.warning("Project deleted. No saved project folder was found to remove.")

    st.rerun()


def update_selected_project_if_edited(project: dict, updated_project: dict) -> None:
    if st.session_state.get("selected_project_id") == project["id"]:
        st.session_state["selected_project_id"] = updated_project["id"]
        st.session_state["selected_project_name"] = updated_project["name"]


def render_project_edit_form(project: dict) -> None:
    st.write("Editing project")
    st.warning(
        "Changing the project name or description may make the saved Codebase Overview "
        "outdated. You can regenerate the overview after saving."
    )

    with st.form(f"edit_project_form_{project['id']}"):
        edited_name = st.text_input("Project Name", value=project["name"])
        edited_description = st.text_area(
            "Project Description",
            value=project.get("description", ""),
        )
        save_submitted = st.form_submit_button("Save Changes")
        cancel_submitted = st.form_submit_button("Cancel")

    if cancel_submitted:
        clear_project_editing()
        st.rerun()

    if not save_submitted:
        return

    cleaned_name = edited_name.strip()
    cleaned_description = edited_description.strip()

    if not cleaned_name:
        st.error("Project name is required.")
        return

    if cleaned_name == project["name"] and cleaned_description == project.get("description", ""):
        clear_project_editing()
        st.rerun()
        return

    updated_project_payload = {
        **project,
        "name": cleaned_name,
        "description": cleaned_description,
    }

    try:
        updated_project = update_project_record(updated_project_payload)
    except ValueError as error:
        st.error(f"Could not update project: {error}")
        return
    except Exception:
        st.error("Project could not be updated. Please try again.")
        return

    if updated_project is None:
        clear_project_editing()
        st.warning("This project no longer exists.")
        st.rerun()
        return

    update_selected_project_if_edited(project, updated_project)
    clear_project_editing()
    st.success("Project updated.")
    st.rerun()


def render_project_actions_menu(project: dict) -> None:
    with st.popover("⋯"):
        render_project_detail(
            "Uploaded ZIP",
            project.get("original_zip_filename") or "Unknown",
        )
        render_project_detail("File size", get_project_file_size(project))
        render_project_detail(
            "Codebase path",
            project.get("codebase_path") or "Unknown",
        )

        if st.button("Edit project", key=f"edit_project_{project['id']}"):
            st.session_state["editing_project_id"] = project["id"]
            clear_pending_project_delete()
            st.rerun()

        if st.button("Delete project", key=f"delete_project_{project['id']}"):
            st.session_state["pending_delete_project_id"] = project["id"]
            clear_project_editing()
            st.rerun()


@st.dialog("Create Project")
def create_project_dialog() -> None:
    with st.form("create_project_form"):
        project_name = st.text_input("Project Name")
        project_description = st.text_area("Project Description")
        uploaded_file = st.file_uploader("Upload Codebase", type=["zip"])
        submitted = st.form_submit_button("Create")

    if submitted:
        cleaned_project_name = project_name.strip()
        errors = []

        if not cleaned_project_name:
            errors.append("Project name is required.")

        if uploaded_file is None:
            errors.append("A ZIP file is required.")

        if cleaned_project_name:
            try:
                if project_name_exists(cleaned_project_name):
                    errors.append("A project with this name already exists.")
            except Exception:
                errors.append("Could not check existing projects. Please try again.")

        if errors:
            for error in errors:
                st.error(error)
            return

        try:
            zip_path = save_project_zip(cleaned_project_name, uploaded_file)
            codebase_path = extract_project_zip(zip_path)
        except RuntimeError as error:
            st.error(str(error))
            return

        try:
            saved_project = create_project_record(
                name=cleaned_project_name,
                description=project_description,
                original_zip_filename=uploaded_file.name,
                zip_file_size=uploaded_file.size,
                zip_path=zip_path,
                codebase_path=codebase_path,
            )
        except ValueError as error:
            st.error(str(error))
            return
        except Exception:
            st.error("Project could not be saved. Please try again.")
            return

        st.success("Project created.")
        st.session_state["selected_project_id"] = saved_project["id"]
        st.session_state["selected_project_name"] = saved_project["name"]
        st.switch_page("pages/project_home.py")


def render_projects() -> None:
    st.header("My Projects")
    projects = load_projects()

    if not projects:
        st.info(
            "No projects yet.\n\n"
            "Create your first project by uploading a small codebase ZIP. "
            "Codebase Compass will scan the files so you can generate an overview, "
            "ask questions, and plan tasks."
        )
        return

    for project in projects:
        with st.container(border=True):
            title_col, open_col, menu_col = st.columns([0.72, 0.14, 0.14])

            with title_col:
                render_project_card_title(project)

            with open_col:
                if st.button("Open", key=f"open_project_{project['id']}"):
                    open_project(project)

            with menu_col:
                render_project_actions_menu(project)

            if st.session_state.get("editing_project_id") == project["id"]:
                render_project_edit_form(project)
                continue

            render_project_card_summary(project)

            if st.session_state.get("pending_delete_project_id") == project["id"]:
                st.warning(
                    "Delete this project? This will remove its tasks, AI outputs, "
                    "and saved codebase files. This cannot be undone."
                )
                confirm_column, cancel_column = st.columns(2)

                with confirm_column:
                    if st.button(
                        "Confirm delete",
                        key=f"confirm_delete_project_{project['id']}",
                    ):
                        delete_project(project)

                with cancel_column:
                    if st.button("Cancel", key=f"cancel_delete_project_{project['id']}"):
                        clear_pending_project_delete()
                        st.rerun()


def main() -> None:
    initialize_session_state()

    st.title("Codebase Compass")

    st.write(
        "Codebase Compass helps developers understand a codebase and plan "
        "development tasks based on the actual project files."
    )

    if st.button("Create Project"):
        create_project_dialog()

    render_projects()


main()
