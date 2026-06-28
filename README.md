# Codebase Compass

Codebase Compass is a GenAI-powered project assistant for small uploaded codebases. It helps users understand project structure, ask questions about code, generate file explanations, and create code-aware development tasks.

The app is built with Python and Streamlit. It uses SQLite for persistence and the OpenAI API for GenAI features such as codebase overviews, semantic search, file explanations, task planning, and AI subtask status checks.

## Features

### Project Management

Users can create projects by uploading a ZIP file containing a small codebase. Codebase Compass extracts the ZIP file, scans supported files, and stores project metadata in SQLite.

### Codebase Overview

The Overview section generates a brief summary of the uploaded codebase using the project name, project description, file paths, and code context.

### Files Viewer

The Files section lets users browse uploaded project files and view source code directly inside the app.

### Ask with Semantic Search

The Ask section allows users to ask natural language questions about the uploaded codebase.

Codebase Compass uses OpenAI embeddings for semantic search. When the semantic search index is built, the app:

1. Scans the uploaded codebase.
2. Splits code files into smaller chunks.
3. Sends those chunks to OpenAI embeddings.
4. Stores the resulting vectors in SQLite.
5. Converts user questions into embeddings.
6. Compares question embeddings to code chunk embeddings using cosine similarity.
7. Sends the most relevant code chunks to the OpenAI model as context.

This allows the app to retrieve code based on meaning instead of only exact keyword matches.

### File Explanations

The Explain section lets users select a file and generate a structured explanation. The app sends the selected file to the LLM once and asks for a JSON response containing:

* a file summary
* important classes
* functions
* methods
* variables
* sections
* explanations for each element

The app then displays the explanation in organized expandable sections.

### Task Management

The Tasks section helps users plan development work based on the actual codebase.

Users can:

* create tasks
* generate task goals
* generate subtasks
* generate acceptance criteria
* view relevant files
* add and edit subtasks manually
* track human progress with checkboxes
* request AI opinions on whether subtasks appear done, partial, missing, or unclear

The human checkbox status is the official task progress. AI opinions are advisory.

## Tools and Technologies

* **Python** for backend logic and application development
* **Streamlit** for the user interface
* **SQLite** for project, task, AI output, code chunk, and semantic search storage
* **OpenAI API** for generated summaries, explanations, task plans, and answers
* **OpenAI embeddings** for semantic code search
* **pytest** for automated testing
* **Local file scanning and chunking utilities** for reading and preparing uploaded codebases

## Project Structure

```text
codebase_compass/
├── app.py
├── pages/
│   ├── projects.py
│   └── project_home.py
├── services/
│   ├── codebase_service.py
│   ├── embedding_service.py
│   ├── llm_service.py
│   ├── retrieval_service.py
│   ├── task_service.py
│   └── vector_search_service.py
├── data/
│   ├── database.py
│   ├── project_repository.py
│   ├── task_repository.py
│   ├── project_ai_output_repository.py
│   └── code_chunk_repository.py
├── utils/
│   ├── file_scanner.py
│   ├── file_reader.py
│   ├── code_chunker.py
│   ├── markdown_formatter.py
│   ├── time_formatter.py
│   └── code_element_locator.py
├── tests/
├── storage/
├── .env.example
├── requirements.txt
└── README.md
```

## Running the Deployed App

A deployed version of the app is available here:

```text
[insert deployed Streamlit app link here]
```

The deployed version uses Streamlit secrets to store the OpenAI API key securely. The API key is not included in the repository.

## Local Setup

### 1. Clone the Repository

```bash
git clone [insert GitHub repository link here]
cd [project-folder-name]
```

### 2. Create a Virtual Environment

On macOS or Linux:

```bash
python -m venv .venv
source .venv/bin/activate
```

On Windows:

```bash
python -m venv .venv
.venv\Scripts\activate
```

### 3. Install Dependencies

```bash
pip install -r requirements.txt
```

### 4. Create a `.env` File

Create a `.env` file in the project root.

```env
OPENAI_API_KEY=your-api-key-here
OPENAI_MODEL=gpt-4o-mini
OPENAI_EMBEDDING_MODEL=text-embedding-3-small
```

The `.env` file is required for GenAI features when running locally.

Do not commit `.env` to GitHub.

### 5. Run the App

```bash
streamlit run app.py
```

Streamlit will start the app and provide a local URL, usually:

```text
http://localhost:8501
```

Open that URL in your browser.

## Streamlit Deployment Notes

For Streamlit Community Cloud, add the following values to the app’s Secrets settings in TOML format:

```toml
OPENAI_API_KEY = "your-api-key-here"
OPENAI_MODEL = "gpt-4o-mini"
OPENAI_EMBEDDING_MODEL = "text-embedding-3-small"
```

Do not put real API keys in GitHub.

## Running Tests

Run the test suite with:

```bash
pytest -q
```

The tests cover backend logic including:

* file scanning
* file reading
* code chunking
* project persistence
* task persistence
* task service behavior
* AI output persistence
* embedding support
* vector search
* LLM prompt construction
* code element location

## Demo Workflow

A typical demo flow is:

1. Open Codebase Compass.
2. Show saved projects.
3. Create a new project by uploading a ZIP codebase.
4. Generate a Codebase Overview.
5. Browse files in the Files section.
6. Build the semantic search index.
7. Ask a codebase question.
8. Generate a file explanation.
9. Create a development task.
10. Generate a task plan.
11. Refresh an AI opinion for a subtask.
12. Check off a subtask manually.

## Notes About Storage

Codebase Compass uses SQLite and local storage for uploaded projects, generated outputs, code chunks, and semantic search data.

When running locally, data is stored in the `storage/` folder.

For deployment, runtime storage is intended for demo use. If the deployed app restarts or resets, uploaded projects may need to be recreated.

## Security Notes

* Do not commit `.env`.
* Do not commit OpenAI API keys.
* Do not commit local runtime storage or uploaded project files.
* Use Streamlit secrets for deployment.
* Use `.env.example` to show required environment variables without exposing real credentials.

## Status

This project was built as a GenAI class project to demonstrate codebase-aware retrieval, summarization, task planning, and semantic search over uploaded source code.
