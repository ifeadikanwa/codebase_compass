import json
import os

from dotenv import load_dotenv
from openai import APIError, OpenAI


DEFAULT_OPENAI_MODEL = "gpt-4o-mini"

ALLOWED_SUBTASK_STATUS_VALUES = {"done", "partial", "missing", "unclear"}
ALLOWED_FILE_EXPLANATION_KINDS = {
    "class",
    "function",
    "method",
    "variable",
    "constant",
    "section",
    "import",
    "other",
}

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
        "- Do not answer from general knowledge.",
        "- If the question is unrelated to the codebase or the supplied context is insufficient, say that the available code context does not contain enough information.",
        "- Do not invent files, functions, classes, behavior, or implementation details not present in the context.",
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
        "- Use compact Markdown with clear visual structure.",
        "- Use #### section headings such as #### Overview, #### Main Files, #### Technologies, #### Entry Points, and #### What to Look at First.",
        "- Do not use #, ##, or ### Markdown headings.",
        "- Do not create a giant title heading.",
        "- Use bullet lists where appropriate.",
        "- Wrap filenames in backticks.",
        "- Keep the overview readable, organized, and visually compact.",
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


def build_file_explanation_prompt(
    project_name,
    project_description,
    file_path,
    file_content,
):
    cleaned_project_name = project_name.strip() or "Untitled Project"
    cleaned_project_description = project_description.strip()
    cleaned_file_path = file_path.strip()
    cleaned_file_content = file_content.strip()

    if not cleaned_file_path:
        raise ValueError("File path must not be empty.")

    if not cleaned_file_content:
        raise ValueError("File content must not be empty.")

    prompt_sections = [
        "You are Codebase Compass, a project assistant that explains code files.",
        "",
        "Instructions:",
        "- Explain the selected file using only the provided file content.",
        "- Do not invent files, dependencies, behavior, or implementation details "
        "outside the file.",
        "- Return valid JSON only, with no Markdown and no code fences.",
        "- Prefer fewer, useful explanations over explaining every tiny line.",
        "- Use beginner-friendly explanations that are clear but not childish.",
        "- For each element, explain what it does, why it matters in the file, and how "
        "it relates to the project if clear.",
        "- Line numbers must be 1-based. If exact line numbers are unclear, estimate "
        "based on the visible file content.",
        "- Element kind must be one of: class, function, method, variable, constant, "
        "section, import, other.",
        "",
        "Expected JSON structure:",
        "{",
        '  "file_path": "path/to/file.py",',
        '  "summary": "Short explanation of what this file does overall.",',
        '  "elements": [',
        "    {",
        '      "name": "ElementName",',
        '      "kind": "function",',
        '      "start_line": 1,',
        '      "end_line": 10,',
        '      "explanation": "What this element does and why it matters."',
        "    }",
        "  ]",
        "}",
        "",
        "Required fields:",
        "file_path, summary, elements, name, kind, start_line, end_line, explanation",
        "",
        "Project name:",
        cleaned_project_name,
        "",
        "Project description:",
        cleaned_project_description or "No description provided.",
        "",
        "File path:",
        cleaned_file_path,
        "",
        "File content:",
        cleaned_file_content,
    ]

    return "\n".join(prompt_sections)


def normalize_file_explanation_line_number(value):
    if isinstance(value, bool):
        return None

    if isinstance(value, int):
        return value if value > 0 else None

    if isinstance(value, str):
        cleaned_value = value.strip()
        if cleaned_value.isdigit():
            parsed_value = int(cleaned_value)
            return parsed_value if parsed_value > 0 else None

    return None


def normalize_file_explanation_element(element):
    if not isinstance(element, dict):
        return None

    name = element.get("name", "")
    explanation = element.get("explanation", "")

    cleaned_name = name.strip() if isinstance(name, str) else ""
    cleaned_explanation = explanation.strip() if isinstance(explanation, str) else ""

    if not cleaned_name or not cleaned_explanation:
        return None

    kind = element.get("kind", "other")
    cleaned_kind = kind.strip() if isinstance(kind, str) else "other"
    if cleaned_kind not in ALLOWED_FILE_EXPLANATION_KINDS:
        cleaned_kind = "other"

    start_line = normalize_file_explanation_line_number(element.get("start_line"))
    end_line = normalize_file_explanation_line_number(element.get("end_line"))

    if start_line is not None and end_line is not None and end_line < start_line:
        end_line = start_line

    return {
        "name": cleaned_name,
        "kind": cleaned_kind,
        "start_line": start_line,
        "end_line": end_line,
        "explanation": cleaned_explanation,
    }


def validate_file_explanations(file_explanations, fallback_file_path):
    if not isinstance(file_explanations, dict):
        raise RuntimeError("OpenAI returned file explanations that are not a JSON object.")

    response_file_path = file_explanations.get("file_path", "")
    cleaned_file_path = (
        response_file_path.strip()
        if isinstance(response_file_path, str) and response_file_path.strip()
        else fallback_file_path.strip()
    )

    summary = file_explanations.get("summary", "")
    cleaned_summary = summary.strip() if isinstance(summary, str) else ""

    elements = file_explanations.get("elements", [])
    if not isinstance(elements, list):
        elements = []

    cleaned_elements = [
        cleaned_element
        for element in elements
        if (cleaned_element := normalize_file_explanation_element(element)) is not None
    ]

    return {
        "file_path": cleaned_file_path,
        "summary": cleaned_summary,
        "elements": cleaned_elements,
    }


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


def generate_file_explanations(
    project_name,
    project_description,
    file_path,
    file_content,
    client=None,
    model=None,
):
    prompt = build_file_explanation_prompt(
        project_name,
        project_description,
        file_path,
        file_content,
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
        raise RuntimeError("Could not generate file explanations from OpenAI.") from error

    output_text = getattr(response, "output_text", None)

    if output_text is None or not output_text.strip():
        raise RuntimeError("OpenAI returned empty file explanations.")

    try:
        file_explanations = json.loads(output_text.strip())
    except json.JSONDecodeError as error:
        raise RuntimeError("OpenAI returned invalid JSON file explanations.") from error

    return validate_file_explanations(file_explanations, file_path)


def build_subtask_status_prompt(
    project_name,
    project_description,
    task_title,
    task_description,
    subtask,
    retrieved_chunks,
):
    cleaned_project_name = project_name.strip()
    cleaned_project_description = project_description.strip()
    cleaned_task_title = task_title.strip()
    cleaned_task_description = task_description.strip()
    cleaned_subtask = subtask.strip()

    if not cleaned_project_name:
        raise ValueError("Project name must not be empty.")

    if not cleaned_task_title:
        raise ValueError("Task title must not be empty.")

    if not cleaned_subtask:
        raise ValueError("Subtask must not be empty.")

    if not retrieved_chunks:
        raise ValueError("At least one retrieved code chunk is required.")

    prompt_sections = [
        "You are Codebase Compass, a project assistant that checks development task progress.",
        "",
        "Instructions:",
        "- Determine whether the subtask appears completed using only the supplied code context.",
        "- Do not invent files, functions, behavior, or implementation details not present in the context.",
        "- If the code context is not enough to decide, use unclear.",
        "- If the implementation is not present, use missing.",
        "- If some evidence exists but the implementation looks incomplete, use partial.",
        "- If the subtask appears implemented, use done.",
        "- Return valid JSON only.",
        "- Do not use Markdown.",
        "- Do not wrap the JSON in code fences.",
        "- The status value must be one of: done, partial, missing, unclear.",
        "",
        "Expected JSON structure:",
        "{",
        '  "status": "done",',
        '  "reason": "Short explanation based on the provided code.",',
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
        "Subtask:",
        cleaned_subtask,
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


def validate_subtask_status_result(status_result):
    if not isinstance(status_result, dict):
        raise RuntimeError("OpenAI returned a subtask status that is not a JSON object.")

    required_keys = {
        "status",
        "reason",
        "relevant_files",
    }

    missing_keys = required_keys - status_result.keys()
    if missing_keys:
        missing_key_list = ", ".join(sorted(missing_keys))
        raise RuntimeError(
            f"OpenAI returned a subtask status missing keys: {missing_key_list}"
        )

    status = status_result["status"]
    if not isinstance(status, str):
        raise RuntimeError("OpenAI returned a subtask status with an invalid status.")

    cleaned_status = status.strip()
    if cleaned_status not in ALLOWED_SUBTASK_STATUS_VALUES:
        raise RuntimeError("OpenAI returned an unsupported subtask status.")

    reason = status_result["reason"]
    if not isinstance(reason, str):
        raise RuntimeError("OpenAI returned a subtask status with an invalid reason.")

    cleaned_reason = reason.strip()
    if not cleaned_reason:
        raise RuntimeError("OpenAI returned a subtask status with an empty reason.")

    relevant_files = status_result["relevant_files"]
    if not isinstance(relevant_files, list) or not all(
        isinstance(file_path, str) for file_path in relevant_files
    ):
        raise RuntimeError(
            "OpenAI returned a subtask status with invalid relevant_files."
        )

    return {
        "status": cleaned_status,
        "reason": cleaned_reason,
        "relevant_files": [
            cleaned_file_path
            for file_path in relevant_files
            if (cleaned_file_path := file_path.strip())
        ],
    }


def generate_subtask_status(
    project_name,
    project_description,
    task_title,
    task_description,
    subtask,
    retrieved_chunks,
    client=None,
    model=None,
):
    prompt = build_subtask_status_prompt(
        project_name,
        project_description,
        task_title,
        task_description,
        subtask,
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
        raise RuntimeError("Could not generate a subtask status from OpenAI.") from error

    output_text = getattr(response, "output_text", None)

    if output_text is None or not output_text.strip():
        raise RuntimeError("OpenAI returned an empty subtask status.")

    try:
        status_result = json.loads(output_text.strip())
    except json.JSONDecodeError as error:
        raise RuntimeError("OpenAI returned an invalid JSON subtask status.") from error

    return validate_subtask_status_result(status_result)


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
