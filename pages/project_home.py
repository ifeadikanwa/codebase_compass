from pathlib import Path

import streamlit as st

from services.llm_service import answer_codebase_question, generate_codebase_overview
from services.retrieval_service import search_codebase
from utils.file_reader import read_code_file
from utils.file_scanner import scan_supported_files


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


def render_codebase_overview(selected_project: dict) -> None:
    st.header("Codebase Overview")
    st.write(
        "Generate a high-level summary of this project from the visible files and README."
    )

    codebase_path = selected_project.get("codebase_path")
    overview_key = f"overview_{selected_project['name']}"

    if not codebase_path:
        st.error("This project does not have a valid extracted codebase path.")
        return

    try:
        supported_files = scan_supported_files(codebase_path)
    except RuntimeError as error:
        st.error(f"Could not scan codebase files: {error}")
        return

    if not supported_files:
        st.info("No supported source-code or text files were found in this project.")
        return

    if st.button("Generate Overview"):
        readme_content = None
        readme_file_path = find_readme_file(supported_files)

        try:
            if readme_file_path:
                readme_content = read_code_file(codebase_path, readme_file_path)

            with st.spinner("Generating codebase overview..."):
                st.session_state[overview_key] = generate_codebase_overview(
                    selected_project["name"],
                    selected_project.get("description", ""),
                    supported_files,
                    readme_content=readme_content,
                )
        except Exception:
            st.error(
                "The codebase overview could not be generated. Please check your API key or try again."
            )

    if overview_key in st.session_state:
        st.markdown(st.session_state[overview_key])


def render_codebase_files(selected_project: dict) -> None:
    st.header("Codebase Files")

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
        st.info("No supported source-code or text files were found in this project.")
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
    st.header("Search Codebase")
    st.write("Search for relevant code sections using keywords.")

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
        st.info("No matching code sections were found.")
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

    render_codebase_overview(selected_project)
    render_codebase_files(selected_project)
    render_codebase_search(selected_project)


main()
