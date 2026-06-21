import json
import os

from dotenv import load_dotenv
from openai import APIError, OpenAI


DEFAULT_OPENAI_MODEL = "gpt-4o-mini"

REQUIRED_RETRIEVED_CHUNK_FIELDS = {
    "file_path",
    "start_line",
    "end_line",
    "content",
}


def validate_retrieved_chunk(retrieved_chunk: dict) -> None:
    for field in REQUIRED_RETRIEVED_CHUNK_FIELDS:
        if field not in retrieved_chunk:
            raise ValueError(f"Retrieved chunk is missing required field: {field}")


def build_codebase_prompt(question: str, retrieved_chunks: list[dict]) -> str:
    cleaned_question = question.strip()

    if not cleaned_question:
        raise ValueError("Question must not be empty.")

    if not retrieved_chunks:
        raise ValueError("At least one retrieved code chunk is required.")

    prompt_sections = [
        "You are Codebase Compass, a project assistant that answers questions about code.",
        "",
        "Instructions:",
        "- Answer the user's question using only the supplied code context.",
        "- Do not invent files, functions, behavior, or implementation details not present in the context.",
        "- If the supplied context is insufficient, say that clearly.",
        "- Explain the code in plain English.",
        "- Cite relevant source locations using file paths and line ranges.",
        "",
        "User question:",
        cleaned_question,
        "",
        "Code context:",
    ]

    for index, chunk in enumerate(retrieved_chunks, start=1):
        validate_retrieved_chunk(chunk)

        prompt_sections.extend(
            [
                "",
                f"SOURCE {index}",
                f"File: {chunk['file_path']}",
                f"Lines: {chunk['start_line']}-{chunk['end_line']}",
                "",
                chunk["content"],
            ]
        )

    return "\n".join(prompt_sections)


def build_codebase_overview_prompt(
    project_name: str,
    project_description: str,
    file_paths: list[str],
    readme_content: str | None = None,
) -> str:
    cleaned_project_name = project_name.strip()
    cleaned_project_description = project_description.strip()
    cleaned_readme_content = readme_content.strip() if readme_content else ""

    if not cleaned_project_name:
        raise ValueError("Project name must not be empty.")

    if not file_paths:
        raise ValueError("At least one supported file path is required.")

    prompt_sections = [
        "You are Codebase Compass, a project assistant that summarizes codebases.",
        "",
        "Instructions:",
        "- Generate a concise codebase overview using only the provided project information.",
        "- Do not invent files, features, behavior, or implementation details not present in the project information.",
        "- If the information is limited, say the overview is based only on the visible files and README.",
        "- Include what the project appears to do.",
        "- Include main folders/files.",
        "- Include likely technologies or languages used.",
        "- Include important entry points.",
        '- Include a short "what to look at first" section.',
        "",
        "Project name:",
        cleaned_project_name,
        "",
        "Project description:",
        cleaned_project_description or "No description provided.",
        "",
        "Supported file list:",
    ]

    prompt_sections.extend(f"- {file_path}" for file_path in file_paths)

    if cleaned_readme_content:
        prompt_sections.extend(
            [
                "",
                "README content:",
                cleaned_readme_content,
            ]
        )
    else:
        prompt_sections.extend(
            [
                "",
                "README content:",
                "No README content provided.",
            ]
        )

    return "\n".join(prompt_sections)


def build_task_plan_prompt(
    project_name,
    project_description,
    task_title,
    task_description,
    retrieved_chunks,
):
    cleaned_project_name = project_name.strip()
    cleaned_project_description = project_description.strip()
    cleaned_task_title = task_title.strip()
    cleaned_task_description = task_description.strip()

    if not cleaned_project_name:
        raise ValueError("Project name must not be empty.")

    if not cleaned_task_title:
        raise ValueError("Task title must not be empty.")

    if not retrieved_chunks:
        raise ValueError("At least one retrieved code chunk is required.")

    prompt_sections = [
        "You are Codebase Compass, a project assistant that plans development tasks.",
        "",
        "Instructions:",
        "- Generate a practical implementation plan using only the supplied project information and code context.",
        "- Do not invent files that are not included in the provided sources.",
        "- If the context is limited, make a reasonable plan but say so in the goal.",
        "- Keep subtasks practical and implementation-focused.",
        "- Keep acceptance criteria testable.",
        "- Return valid JSON only, with no Markdown and no code fences.",
        "- The JSON must use exactly these keys: goal, subtasks, acceptance_criteria, relevant_files.",
        "",
        "Expected JSON structure:",
        "{",
        '  "goal": "Clear one-paragraph goal for the task.",',
        '  "subtasks": [',
        '    "First implementation step",',
        '    "Second implementation step"',
        "  ],",
        '  "acceptance_criteria": [',
        '    "Specific condition that proves the task is complete",',
        '    "Another completion condition"',
        "  ],",
        '  "relevant_files": [',
        '    "path/to/file.py"',
        "  ]",
        "}",
        "",
        "Project name:",
        cleaned_project_name,
        "",
        "Project description:",
        cleaned_project_description or "No description provided.",
        "",
        "Task title:",
        cleaned_task_title,
        "",
        "Task description:",
        cleaned_task_description or "No description provided.",
        "",
        "Code context:",
    ]

    for index, chunk in enumerate(retrieved_chunks, start=1):
        validate_retrieved_chunk(chunk)

        prompt_sections.extend(
            [
                "",
                f"SOURCE {index}",
                f"File: {chunk['file_path']}",
                f"Lines: {chunk['start_line']}-{chunk['end_line']}",
                "",
                chunk["content"],
            ]
        )

    return "\n".join(prompt_sections)


def validate_task_plan(task_plan):
    if not isinstance(task_plan, dict):
        raise RuntimeError("OpenAI returned a task plan that is not a JSON object.")

    required_keys = {
        "goal",
        "subtasks",
        "acceptance_criteria",
        "relevant_files",
    }

    missing_keys = required_keys - task_plan.keys()
    if missing_keys:
        missing_key_list = ", ".join(sorted(missing_keys))
        raise RuntimeError(f"OpenAI returned a task plan missing keys: {missing_key_list}")

    goal = task_plan["goal"]
    if not isinstance(goal, str):
        raise RuntimeError("OpenAI returned a task plan with an invalid goal.")

    cleaned_goal = goal.strip()
    if not cleaned_goal:
        raise RuntimeError("OpenAI returned a task plan with an empty goal.")

    cleaned_task_plan = {"goal": cleaned_goal}

    for key in ("subtasks", "acceptance_criteria", "relevant_files"):
        value = task_plan[key]
        if not isinstance(value, list) or not all(isinstance(item, str) for item in value):
            raise RuntimeError(f"OpenAI returned a task plan with invalid {key}.")

        cleaned_task_plan[key] = [
            cleaned_item
            for item in value
            if (cleaned_item := item.strip())
        ]

    return cleaned_task_plan


def generate_task_plan(
    project_name,
    project_description,
    task_title,
    task_description,
    retrieved_chunks,
    client=None,
    model=None,
):
    prompt = build_task_plan_prompt(
        project_name,
        project_description,
        task_title,
        task_description,
        retrieved_chunks,
    )

    load_dotenv()

    selected_model = model or os.getenv("OPENAI_MODEL") or DEFAULT_OPENAI_MODEL

    if client is None:
        api_key = os.getenv("OPENAI_API_KEY")
        if not api_key:
            raise ValueError("OPENAI_API_KEY environment variable must be configured.")

        client = OpenAI(api_key=api_key)

    try:
        response = client.responses.create(
            model=selected_model,
            input=prompt,
        )
    except APIError as error:
        raise RuntimeError("Could not generate a task plan from OpenAI.") from error

    output_text = getattr(response, "output_text", None)

    if output_text is None or not output_text.strip():
        raise RuntimeError("OpenAI returned an empty task plan.")

    try:
        task_plan = json.loads(output_text.strip())
    except json.JSONDecodeError as error:
        raise RuntimeError("OpenAI returned an invalid JSON task plan.") from error

    return validate_task_plan(task_plan)


def generate_codebase_overview(
    project_name: str,
    project_description: str,
    file_paths: list[str],
    readme_content: str | None = None,
    client=None,
    model: str | None = None,
) -> str:
    prompt = build_codebase_overview_prompt(
        project_name,
        project_description,
        file_paths,
        readme_content=readme_content,
    )

    load_dotenv()

    selected_model = model or os.getenv("OPENAI_MODEL") or DEFAULT_OPENAI_MODEL

    if client is None:
        api_key = os.getenv("OPENAI_API_KEY")
        if not api_key:
            raise ValueError("OPENAI_API_KEY environment variable must be configured.")

        client = OpenAI(api_key=api_key)

    try:
        response = client.responses.create(
            model=selected_model,
            input=prompt,
        )
    except APIError as error:
        raise RuntimeError("Could not generate a codebase overview from OpenAI.") from error

    overview = getattr(response, "output_text", None)

    if overview is None or not overview.strip():
        raise RuntimeError("OpenAI returned an empty codebase overview.")

    return overview.strip()


def answer_codebase_question(
    question: str,
    retrieved_chunks: list[dict],
    client=None,
    model: str | None = None,
) -> str:
    prompt = build_codebase_prompt(question, retrieved_chunks)

    load_dotenv()

    selected_model = model or os.getenv("OPENAI_MODEL") or DEFAULT_OPENAI_MODEL

    if client is None:
        api_key = os.getenv("OPENAI_API_KEY")
        if not api_key:
            raise ValueError("OPENAI_API_KEY environment variable must be configured.")

        client = OpenAI(api_key=api_key)

    try:
        response = client.responses.create(
            model=selected_model,
            input=prompt,
        )
    except APIError as error:
        raise RuntimeError("Could not generate an answer from OpenAI.") from error

    answer = getattr(response, "output_text", None)

    if answer is None or not answer.strip():
        raise RuntimeError("OpenAI returned an empty answer.")

    return answer.strip()
