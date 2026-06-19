import streamlit as st


projects_page = st.Page(
    "pages/projects.py",
    title="Projects",
    default=True,
)

project_home_page = st.Page(
    "pages/project_home.py",
    title="Project Home",
)

selected_page = st.navigation(
    [projects_page, project_home_page],
    position="hidden",
)

selected_page.run()
