import streamlit as st


def format_file_size(size_bytes: int) -> str:
    if size_bytes < 1024:
        return f"{size_bytes} bytes"

    size_kb = size_bytes / 1024
    if size_kb < 1024:
        return f"{size_kb:.1f} KB"

    size_mb = size_kb / 1024
    return f"{size_mb:.1f} MB"


def get_selected_project() -> dict | None:
    selected_project_name = st.session_state.get("selected_project_name")
    projects = st.session_state.get("projects", [])

    if not selected_project_name:
        return None

    for project in projects:
        if project["name"] == selected_project_name:
            return project

    return None


def return_to_projects() -> None:
    st.session_state.pop("selected_project_name", None)
    st.switch_page("pages/projects.py")


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

    st.write(f"Uploaded ZIP: {selected_project['zip_filename']}")
    st.write(f"File size: {format_file_size(selected_project['zip_size'])}")

    st.write("Codebase tools will appear here.")


main()
