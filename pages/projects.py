import streamlit as st

from services.codebase_service import extract_project_zip, save_project_zip


def format_file_size(size_bytes: int) -> str:
    if size_bytes < 1024:
        return f"{size_bytes} bytes"

    size_kb = size_bytes / 1024
    if size_kb < 1024:
        return f"{size_kb:.1f} KB"

    size_mb = size_kb / 1024
    return f"{size_mb:.1f} MB"


def initialize_session_state() -> None:
    if "projects" not in st.session_state:
        st.session_state["projects"] = []


def project_name_exists(project_name: str) -> bool:
    normalized_project_name = project_name.strip().casefold()

    return any(
        project["name"].casefold() == normalized_project_name
        for project in st.session_state["projects"]
    )


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

        if cleaned_project_name and project_name_exists(cleaned_project_name):
            errors.append("A project with this name already exists.")

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

        st.session_state["projects"].append(
            {
                "name": cleaned_project_name,
                "description": project_description.strip(),
                "zip_filename": uploaded_file.name,
                "zip_size": uploaded_file.size,
                "zip_path": zip_path,
                "codebase_path": codebase_path,
            }
        )
        st.rerun()


def render_projects() -> None:
    st.header("My Projects")

    if not st.session_state["projects"]:
        st.write("No projects have been created yet.")
        return

    for index, project in enumerate(st.session_state["projects"]):
        with st.container(border=True):
            st.subheader(project["name"])

            if project["description"]:
                st.write(project["description"])
            else:
                st.write("No description provided.")

            st.write(f"Uploaded ZIP: {project['zip_filename']}")
            st.write(f"File size: {format_file_size(project['zip_size'])}")

            if st.button("Open Project", key=f"open_project_{index}"):
                st.session_state.selected_project_name = project["name"]
                st.switch_page("pages/project_home.py")


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
