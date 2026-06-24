import copy

import pytest

from services import llm_service
from services.llm_service import (
    answer_codebase_question,
    build_codebase_overview_prompt,
    build_file_explanation_prompt,
    build_codebase_prompt,
    build_subtask_status_prompt,
    build_task_plan_prompt,
    generate_codebase_overview,
    generate_file_explanations,
    generate_subtask_status,
    generate_task_plan,
)


class FakeResponse:
    def __init__(self, output_text):
        self.output_text = output_text


class FakeResponses:
    def __init__(self, response=None, error=None):
        self.response = response
        self.error = error
        self.calls = []

    def create(self, **kwargs):
        self.calls.append(kwargs)

        if self.error is not None:
            raise self.error

        return self.response


class FakeClient:
    def __init__(self, response=None, error=None):
        self.responses = FakeResponses(response=response, error=error)


@pytest.fixture(autouse=True)
def prevent_real_dotenv_loading(monkeypatch):
    monkeypatch.setattr(llm_service, "load_dotenv", lambda *args, **kwargs: None)


def make_retrieved_chunk(
    file_path: str = "services/auth_service.py",
    start_line: int = 10,
    end_line: int = 20,
    content: str = "def login_user():\n    return True",
) -> dict:
    return {
        "file_path": file_path,
        "start_line": start_line,
        "end_line": end_line,
        "content": content,
        "score": 99,
        "matching_terms": ["secret_metadata_value"],
    }


def test_build_codebase_prompt_includes_stripped_question():
    prompt = build_codebase_prompt("  Where is login handled?  ", [make_retrieved_chunk()])

    assert "Where is login handled?" in prompt
    assert "  Where is login handled?  " not in prompt


def test_build_codebase_prompt_includes_source_information():
    chunk = make_retrieved_chunk(
        file_path="services/auth_service.py",
        start_line=12,
        end_line=35,
        content="def login_user(username, password):\n    return True",
    )

    prompt = build_codebase_prompt("Where is login handled?", [chunk])

    assert "File: services/auth_service.py" in prompt
    assert "Lines: 12-35" in prompt
    assert "def login_user(username, password):" in prompt


def test_build_codebase_prompt_includes_multiple_chunks_in_order():
    chunks = [
        make_retrieved_chunk("first.py", 1, 5, "first_content"),
        make_retrieved_chunk("second.py", 10, 15, "second_content"),
    ]

    prompt = build_codebase_prompt("Explain this code.", chunks)

    assert prompt.index("SOURCE 1") < prompt.index("SOURCE 2")
    assert prompt.index("File: first.py") < prompt.index("File: second.py")
    assert "first_content" in prompt
    assert "second_content" in prompt


def test_build_codebase_prompt_preserves_code_formatting():
    content = "def login_user():\n\n    if True:\n        return 'ok'\n"
    prompt = build_codebase_prompt("Explain login.", [make_retrieved_chunk(content=content)])

    assert content in prompt


def test_build_codebase_prompt_includes_grounding_instructions():
    prompt = build_codebase_prompt("Explain login.", [make_retrieved_chunk()])
    prompt_lower = prompt.lower()

    assert "using only the supplied code context" in prompt_lower
    assert "do not answer from general knowledge" in prompt_lower
    assert "question is unrelated to the codebase" in prompt_lower
    assert "do not invent" in prompt_lower
    assert "files, functions, classes" in prompt_lower
    assert "available code context does not contain enough information" in prompt_lower
    assert "file paths and line ranges" in prompt_lower


def test_build_codebase_prompt_excludes_retrieval_metadata():
    prompt = build_codebase_prompt("Explain login.", [make_retrieved_chunk()])

    assert "99" not in prompt
    assert "secret_metadata_value" not in prompt
    assert "matching_terms" not in prompt
    assert "score" not in prompt


def test_build_codebase_prompt_does_not_mutate_input_chunks():
    chunks = [make_retrieved_chunk()]
    original_chunks = copy.deepcopy(chunks)

    build_codebase_prompt("Explain login.", chunks)

    assert chunks == original_chunks


@pytest.mark.parametrize("question", ["", "   "])
def test_build_codebase_prompt_rejects_empty_question(question):
    with pytest.raises(ValueError, match="Question"):
        build_codebase_prompt(question, [make_retrieved_chunk()])


def test_build_codebase_prompt_rejects_empty_retrieved_chunks():
    with pytest.raises(ValueError, match="retrieved code chunk"):
        build_codebase_prompt("Explain login.", [])


@pytest.mark.parametrize(
    "missing_field",
    [
        "file_path",
        "start_line",
        "end_line",
        "content",
    ],
)
def test_build_codebase_prompt_rejects_missing_required_fields(missing_field):
    chunk = make_retrieved_chunk()
    del chunk[missing_field]

    with pytest.raises(ValueError, match=missing_field):
        build_codebase_prompt("Explain login.", [chunk])


def test_build_codebase_overview_prompt_includes_project_name():
    prompt = build_codebase_overview_prompt("Compass", "", ["app.py"])

    assert "Compass" in prompt


def test_build_codebase_overview_prompt_includes_project_description_when_provided():
    prompt = build_codebase_overview_prompt(
        "Compass",
        "A tool for exploring codebases.",
        ["app.py"],
    )

    assert "A tool for exploring codebases." in prompt


def test_build_codebase_overview_prompt_includes_file_paths():
    prompt = build_codebase_overview_prompt(
        "Compass",
        "",
        ["app.py", "services/llm_service.py"],
    )

    assert "- app.py" in prompt
    assert "- services/llm_service.py" in prompt


def test_build_codebase_overview_prompt_includes_readme_content_when_provided():
    prompt = build_codebase_overview_prompt(
        "Compass",
        "",
        ["README.md"],
        readme_content="# Compass\nExplore codebases.",
    )

    assert "# Compass" in prompt
    assert "Explore codebases." in prompt


def test_build_codebase_overview_prompt_works_without_readme_content():
    prompt = build_codebase_overview_prompt("Compass", "", ["app.py"])

    assert "No README content provided." in prompt


def test_build_codebase_overview_prompt_includes_grounding_instructions():
    prompt = build_codebase_overview_prompt("Compass", "", ["app.py"])
    prompt_lower = prompt.lower()

    assert "using only the provided project information" in prompt_lower
    assert "do not invent files" in prompt_lower
    assert "visible files and readme" in prompt_lower


def test_build_codebase_overview_prompt_requests_compact_markdown_formatting():
    prompt = build_codebase_overview_prompt("Compass", "", ["app.py"])
    prompt_lower = prompt.lower()

    assert "compact markdown" in prompt_lower
    assert "#### section headings" in prompt_lower
    assert "do not use #, ##, or ###" in prompt_lower
    assert "bullet lists" in prompt_lower
    assert "wrap filenames in backticks" in prompt_lower


def test_build_codebase_overview_prompt_preserves_file_order():
    prompt = build_codebase_overview_prompt(
        "Compass",
        "",
        ["first.py", "second.py", "third.py"],
    )

    assert prompt.index("- first.py") < prompt.index("- second.py")
    assert prompt.index("- second.py") < prompt.index("- third.py")


def test_build_codebase_overview_prompt_does_not_mutate_file_paths():
    file_paths = ["first.py", "second.py"]
    original_file_paths = copy.deepcopy(file_paths)

    build_codebase_overview_prompt("Compass", "", file_paths)

    assert file_paths == original_file_paths


@pytest.mark.parametrize("project_name", ["", "   "])
def test_build_codebase_overview_prompt_rejects_empty_project_name(project_name):
    with pytest.raises(ValueError, match="Project name"):
        build_codebase_overview_prompt(project_name, "", ["app.py"])


def test_build_codebase_overview_prompt_rejects_empty_file_list():
    with pytest.raises(ValueError, match="supported file path"):
        build_codebase_overview_prompt("Compass", "", [])


def test_generate_codebase_overview_calls_responses_api_with_prompt():
    client = FakeClient(response=FakeResponse("Overview"))

    generate_codebase_overview(
        "Compass",
        "A code explorer.",
        ["app.py"],
        readme_content="# Compass",
        client=client,
        model="test-model",
    )

    assert len(client.responses.calls) == 1
    call = client.responses.calls[0]
    assert call["model"] == "test-model"
    assert "Compass" in call["input"]
    assert "A code explorer." in call["input"]
    assert "- app.py" in call["input"]
    assert "# Compass" in call["input"]


def test_generate_codebase_overview_returns_stripped_generated_text():
    client = FakeClient(response=FakeResponse("  This is the overview.  "))

    overview = generate_codebase_overview("Compass", "", ["app.py"], client=client)

    assert overview == "This is the overview."


def test_generate_codebase_overview_uses_supplied_model():
    client = FakeClient(response=FakeResponse("Overview"))

    generate_codebase_overview("Compass", "", ["app.py"], client=client, model="custom-model")

    assert client.responses.calls[0]["model"] == "custom-model"


def test_generate_codebase_overview_uses_openai_model_environment_variable(monkeypatch):
    monkeypatch.setenv("OPENAI_MODEL", "env-model")
    client = FakeClient(response=FakeResponse("Overview"))

    generate_codebase_overview("Compass", "", ["app.py"], client=client)

    assert client.responses.calls[0]["model"] == "env-model"


def test_generate_codebase_overview_uses_fallback_model(monkeypatch):
    monkeypatch.setattr(llm_service, "load_dotenv", lambda *args, **kwargs: None)
    monkeypatch.delenv("OPENAI_MODEL", raising=False)
    client = FakeClient(response=FakeResponse("Overview"))

    generate_codebase_overview("Compass", "", ["app.py"], client=client)

    assert client.responses.calls[0]["model"] == "gpt-4o-mini"


def test_generate_codebase_overview_with_injected_client_does_not_require_api_key(monkeypatch):
    monkeypatch.setattr(llm_service, "load_dotenv", lambda *args, **kwargs: None)
    monkeypatch.delenv("OPENAI_API_KEY", raising=False)
    client = FakeClient(response=FakeResponse("Overview"))

    overview = generate_codebase_overview("Compass", "", ["app.py"], client=client)

    assert overview == "Overview"


@pytest.mark.parametrize("output_text", ["", "   ", None])
def test_generate_codebase_overview_rejects_empty_output(output_text):
    client = FakeClient(response=FakeResponse(output_text))

    with pytest.raises(RuntimeError, match="empty codebase overview"):
        generate_codebase_overview("Compass", "", ["app.py"], client=client)


def test_generate_codebase_overview_does_not_make_real_api_call_without_api_key(monkeypatch):
    def fail_if_openai_client_is_constructed(*args, **kwargs):
        raise AssertionError("OpenAI client should not be constructed without an API key.")

    monkeypatch.setattr(llm_service, "load_dotenv", lambda *args, **kwargs: None)
    monkeypatch.setattr(llm_service, "OpenAI", fail_if_openai_client_is_constructed)
    monkeypatch.delenv("OPENAI_API_KEY", raising=False)
    monkeypatch.delenv("OPENAI_MODEL", raising=False)

    with pytest.raises(ValueError, match="OPENAI_API_KEY"):
        generate_codebase_overview("Compass", "", ["app.py"])


def test_generate_codebase_overview_wraps_openai_api_errors(monkeypatch):
    class FakeAPIError(Exception):
        pass

    original_error = FakeAPIError("boom")
    monkeypatch.setattr(llm_service, "APIError", FakeAPIError)
    client = FakeClient(error=original_error)

    with pytest.raises(
        RuntimeError,
        match="Could not generate a codebase overview",
    ) as error_info:
        generate_codebase_overview("Compass", "", ["app.py"], client=client)

    assert error_info.value.__cause__ is original_error


def make_file_explanation_json(
    file_path="  cart.py  ",
    summary="  This file defines shopping cart behavior.  ",
    elements=None,
):
    import json

    return json.dumps(
        {
            "file_path": file_path,
            "summary": summary,
            "elements": elements
            if elements is not None
            else [
                {
                    "name": "  ShoppingCart  ",
                    "kind": "class",
                    "start_line": 5,
                    "end_line": 42,
                    "explanation": "  Stores cart items.  ",
                }
            ],
        }
    )


def test_build_file_explanation_prompt_includes_project_and_file_information():
    prompt = build_file_explanation_prompt(
        "Compass",
        "A codebase assistant.",
        "cart.py",
        "class ShoppingCart:\n    pass",
    )

    assert "Compass" in prompt
    assert "A codebase assistant." in prompt
    assert "cart.py" in prompt
    assert "class ShoppingCart:" in prompt


def test_build_file_explanation_prompt_uses_fallback_project_name():
    prompt = build_file_explanation_prompt("", "", "cart.py", "x = 1")

    assert "Untitled Project" in prompt


def test_build_file_explanation_prompt_includes_json_and_required_field_instructions():
    prompt = build_file_explanation_prompt("Compass", "", "cart.py", "x = 1")
    prompt_lower = prompt.lower()

    assert "return valid json only" in prompt_lower
    assert "no markdown" in prompt_lower
    assert "no code fences" in prompt_lower
    assert "summary" in prompt
    assert "elements" in prompt
    assert "name" in prompt
    assert "kind" in prompt
    assert "start_line" in prompt
    assert "end_line" in prompt
    assert "explanation" in prompt


@pytest.mark.parametrize("file_path", ["", "   "])
def test_build_file_explanation_prompt_rejects_empty_file_path(file_path):
    with pytest.raises(ValueError, match="File path"):
        build_file_explanation_prompt("Compass", "", file_path, "x = 1")


@pytest.mark.parametrize("file_content", ["", "   "])
def test_build_file_explanation_prompt_rejects_empty_file_content(file_content):
    with pytest.raises(ValueError, match="File content"):
        build_file_explanation_prompt("Compass", "", "cart.py", file_content)


def test_generate_file_explanations_calls_responses_api_with_prompt():
    client = FakeClient(response=FakeResponse(make_file_explanation_json()))

    generate_file_explanations(
        "Compass",
        "A codebase assistant.",
        "cart.py",
        "class ShoppingCart:\n    pass",
        client=client,
        model="test-model",
    )

    assert len(client.responses.calls) == 1
    call = client.responses.calls[0]
    assert call["model"] == "test-model"
    assert "Compass" in call["input"]
    assert "cart.py" in call["input"]
    assert "class ShoppingCart:" in call["input"]


def test_generate_file_explanations_returns_cleaned_dictionary():
    client = FakeClient(response=FakeResponse(make_file_explanation_json()))

    file_explanations = generate_file_explanations(
        "Compass",
        "",
        "cart.py",
        "class ShoppingCart:\n    pass",
        client=client,
    )

    assert file_explanations == {
        "file_path": "cart.py",
        "summary": "This file defines shopping cart behavior.",
        "elements": [
            {
                "name": "ShoppingCart",
                "kind": "class",
                "start_line": 5,
                "end_line": 42,
                "explanation": "Stores cart items.",
            }
        ],
    }


def test_generate_file_explanations_normalizes_missing_and_invalid_values():
    elements = [
        {
            "name": "  add_item  ",
            "kind": "not-a-kind",
            "start_line": "abc",
            "end_line": None,
            "explanation": "  Adds a product to the cart.  ",
        },
        {
            "name": "checkout",
            "kind": "function",
            "start_line": 20,
            "end_line": 10,
            "explanation": "Checks out the cart.",
        },
    ]
    client = FakeClient(
        response=FakeResponse(
            make_file_explanation_json(file_path="", summary=None, elements=elements)
        )
    )

    file_explanations = generate_file_explanations(
        "Compass",
        "",
        "cart.py",
        "def add_item():\n    pass",
        client=client,
    )

    assert file_explanations == {
        "file_path": "cart.py",
        "summary": "",
        "elements": [
            {
                "name": "add_item",
                "kind": "other",
                "start_line": None,
                "end_line": None,
                "explanation": "Adds a product to the cart.",
            },
            {
                "name": "checkout",
                "kind": "function",
                "start_line": 20,
                "end_line": 20,
                "explanation": "Checks out the cart.",
            },
        ],
    }


def test_generate_file_explanations_uses_empty_elements_when_missing():
    client = FakeClient(response=FakeResponse('{"summary": "  Summary.  "}'))

    file_explanations = generate_file_explanations(
        "Compass",
        "",
        "cart.py",
        "x = 1",
        client=client,
    )

    assert file_explanations == {
        "file_path": "cart.py",
        "summary": "Summary.",
        "elements": [],
    }


def test_generate_file_explanations_removes_empty_elements():
    elements = [
        {
            "name": "   ",
            "kind": "function",
            "start_line": 1,
            "end_line": 2,
            "explanation": "Has no name.",
        },
        {
            "name": "valid",
            "kind": "function",
            "start_line": 3,
            "end_line": 4,
            "explanation": "   ",
        },
        {
            "name": "kept",
            "kind": "constant",
            "start_line": 5,
            "end_line": 5,
            "explanation": "A useful constant.",
        },
    ]
    client = FakeClient(response=FakeResponse(make_file_explanation_json(elements=elements)))

    file_explanations = generate_file_explanations(
        "Compass",
        "",
        "cart.py",
        "VALUE = 1",
        client=client,
    )

    assert file_explanations["elements"] == [
        {
            "name": "kept",
            "kind": "constant",
            "start_line": 5,
            "end_line": 5,
            "explanation": "A useful constant.",
        }
    ]


def test_generate_file_explanations_uses_supplied_model():
    client = FakeClient(response=FakeResponse(make_file_explanation_json()))

    generate_file_explanations(
        "Compass",
        "",
        "cart.py",
        "x = 1",
        client=client,
        model="custom-model",
    )

    assert client.responses.calls[0]["model"] == "custom-model"


def test_generate_file_explanations_uses_openai_model_environment_variable(monkeypatch):
    monkeypatch.setenv("OPENAI_MODEL", "env-model")
    client = FakeClient(response=FakeResponse(make_file_explanation_json()))

    generate_file_explanations("Compass", "", "cart.py", "x = 1", client=client)

    assert client.responses.calls[0]["model"] == "env-model"


def test_generate_file_explanations_uses_fallback_model(monkeypatch):
    monkeypatch.delenv("OPENAI_MODEL", raising=False)
    client = FakeClient(response=FakeResponse(make_file_explanation_json()))

    generate_file_explanations("Compass", "", "cart.py", "x = 1", client=client)

    assert client.responses.calls[0]["model"] == "gpt-4o-mini"


def test_generate_file_explanations_with_injected_client_does_not_require_api_key(monkeypatch):
    monkeypatch.delenv("OPENAI_API_KEY", raising=False)
    client = FakeClient(response=FakeResponse(make_file_explanation_json()))

    file_explanations = generate_file_explanations(
        "Compass",
        "",
        "cart.py",
        "x = 1",
        client=client,
    )

    assert file_explanations["file_path"] == "cart.py"


@pytest.mark.parametrize("output_text", ["", "   ", None])
def test_generate_file_explanations_rejects_empty_output(output_text):
    client = FakeClient(response=FakeResponse(output_text))

    with pytest.raises(RuntimeError, match="empty file explanations"):
        generate_file_explanations("Compass", "", "cart.py", "x = 1", client=client)


def test_generate_file_explanations_rejects_invalid_json():
    client = FakeClient(response=FakeResponse("not json"))

    with pytest.raises(RuntimeError, match="invalid JSON file explanations"):
        generate_file_explanations("Compass", "", "cart.py", "x = 1", client=client)


def test_generate_file_explanations_rejects_non_object_json():
    client = FakeClient(response=FakeResponse("[]"))

    with pytest.raises(RuntimeError, match="not a JSON object"):
        generate_file_explanations("Compass", "", "cart.py", "x = 1", client=client)


def test_generate_file_explanations_does_not_make_real_api_call_without_api_key(monkeypatch):
    def fail_if_openai_client_is_constructed(*args, **kwargs):
        raise AssertionError("OpenAI client should not be constructed without an API key.")

    monkeypatch.setattr(llm_service, "OpenAI", fail_if_openai_client_is_constructed)
    monkeypatch.delenv("OPENAI_API_KEY", raising=False)
    monkeypatch.delenv("OPENAI_MODEL", raising=False)

    with pytest.raises(ValueError, match="OPENAI_API_KEY"):
        generate_file_explanations("Compass", "", "cart.py", "x = 1")


def test_generate_file_explanations_wraps_openai_api_errors(monkeypatch):
    class FakeAPIError(Exception):
        pass

    original_error = FakeAPIError("boom")
    monkeypatch.setattr(llm_service, "APIError", FakeAPIError)
    client = FakeClient(error=original_error)

    with pytest.raises(RuntimeError, match="Could not generate file explanations") as error_info:
        generate_file_explanations("Compass", "", "cart.py", "x = 1", client=client)

    assert error_info.value.__cause__ is original_error


def make_task_plan_json(
    goal="  Add login support.  ",
    subtasks=None,
    acceptance_criteria=None,
    relevant_files=None,
):
    import json

    return json.dumps(
        {
            "goal": goal,
            "subtasks": subtasks
            if subtasks is not None
            else ["  Update auth service  ", "", "Add tests"],
            "acceptance_criteria": acceptance_criteria
            if acceptance_criteria is not None
            else ["  Login succeeds  ", "   ", "Logout succeeds"],
            "relevant_files": relevant_files
            if relevant_files is not None
            else ["  services/auth_service.py  ", ""],
        }
    )


def test_build_task_plan_prompt_includes_project_and_task_information():
    prompt = build_task_plan_prompt(
        "Compass",
        "A codebase assistant.",
        "Add login",
        "Users can sign in.",
        [make_retrieved_chunk()],
    )

    assert "Compass" in prompt
    assert "A codebase assistant." in prompt
    assert "Add login" in prompt
    assert "Users can sign in." in prompt


def test_build_task_plan_prompt_includes_source_information():
    chunk = make_retrieved_chunk(
        file_path="services/auth_service.py",
        start_line=12,
        end_line=30,
        content="def login_user():\n    return True",
    )

    prompt = build_task_plan_prompt("Compass", "", "Add login", "", [chunk])

    assert "File: services/auth_service.py" in prompt
    assert "Lines: 12-30" in prompt
    assert "def login_user():" in prompt


def test_build_task_plan_prompt_includes_task_plan_instructions():
    prompt = build_task_plan_prompt("Compass", "", "Add login", "", [make_retrieved_chunk()])
    prompt_lower = prompt.lower()

    assert "using only the supplied project information and code context" in prompt_lower
    assert "do not invent files" in prompt_lower
    assert "return valid json only" in prompt_lower
    assert "no markdown" in prompt_lower
    assert "no code fences" in prompt_lower


def test_build_task_plan_prompt_excludes_retrieval_metadata():
    prompt = build_task_plan_prompt("Compass", "", "Add login", "", [make_retrieved_chunk()])

    assert "99" not in prompt
    assert "secret_metadata_value" not in prompt
    assert "matching_terms" not in prompt
    assert "score" not in prompt


def test_build_task_plan_prompt_preserves_chunk_order():
    chunks = [
        make_retrieved_chunk("first.py", 1, 5, "first_content"),
        make_retrieved_chunk("second.py", 10, 15, "second_content"),
    ]

    prompt = build_task_plan_prompt("Compass", "", "Add login", "", chunks)

    assert prompt.index("SOURCE 1") < prompt.index("SOURCE 2")
    assert prompt.index("File: first.py") < prompt.index("File: second.py")
    assert prompt.index("first_content") < prompt.index("second_content")


def test_build_task_plan_prompt_does_not_mutate_retrieved_chunks():
    chunks = [make_retrieved_chunk()]
    original_chunks = copy.deepcopy(chunks)

    build_task_plan_prompt("Compass", "", "Add login", "", chunks)

    assert chunks == original_chunks


@pytest.mark.parametrize("project_name", ["", "   "])
def test_build_task_plan_prompt_rejects_empty_project_name(project_name):
    with pytest.raises(ValueError, match="Project name"):
        build_task_plan_prompt(project_name, "", "Add login", "", [make_retrieved_chunk()])


@pytest.mark.parametrize("task_title", ["", "   "])
def test_build_task_plan_prompt_rejects_empty_task_title(task_title):
    with pytest.raises(ValueError, match="Task title"):
        build_task_plan_prompt("Compass", "", task_title, "", [make_retrieved_chunk()])


def test_build_task_plan_prompt_rejects_empty_retrieved_chunks():
    with pytest.raises(ValueError, match="retrieved code chunk"):
        build_task_plan_prompt("Compass", "", "Add login", "", [])


@pytest.mark.parametrize(
    "missing_field",
    [
        "file_path",
        "start_line",
        "end_line",
        "content",
    ],
)
def test_build_task_plan_prompt_rejects_missing_required_chunk_fields(missing_field):
    chunk = make_retrieved_chunk()
    del chunk[missing_field]

    with pytest.raises(ValueError, match=missing_field):
        build_task_plan_prompt("Compass", "", "Add login", "", [chunk])


def test_generate_task_plan_calls_responses_api_with_prompt():
    client = FakeClient(response=FakeResponse(make_task_plan_json()))
    chunks = [make_retrieved_chunk()]

    generate_task_plan(
        "Compass",
        "A codebase assistant.",
        "Add login",
        "Users can sign in.",
        chunks,
        client=client,
        model="test-model",
    )

    assert len(client.responses.calls) == 1
    call = client.responses.calls[0]
    assert call["model"] == "test-model"
    assert "Compass" in call["input"]
    assert "Add login" in call["input"]
    assert "File: services/auth_service.py" in call["input"]


def test_generate_task_plan_returns_cleaned_task_plan_dictionary():
    client = FakeClient(response=FakeResponse(make_task_plan_json()))

    task_plan = generate_task_plan(
        "Compass",
        "",
        "Add login",
        "",
        [make_retrieved_chunk()],
        client=client,
    )

    assert task_plan == {
        "goal": "Add login support.",
        "subtasks": ["Update auth service", "Add tests"],
        "acceptance_criteria": ["Login succeeds", "Logout succeeds"],
        "relevant_files": ["services/auth_service.py"],
    }


def test_generate_task_plan_uses_supplied_model():
    client = FakeClient(response=FakeResponse(make_task_plan_json()))

    generate_task_plan(
        "Compass",
        "",
        "Add login",
        "",
        [make_retrieved_chunk()],
        client=client,
        model="custom-model",
    )

    assert client.responses.calls[0]["model"] == "custom-model"


def test_generate_task_plan_uses_openai_model_environment_variable(monkeypatch):
    monkeypatch.setenv("OPENAI_MODEL", "env-model")
    client = FakeClient(response=FakeResponse(make_task_plan_json()))

    generate_task_plan("Compass", "", "Add login", "", [make_retrieved_chunk()], client=client)

    assert client.responses.calls[0]["model"] == "env-model"


def test_generate_task_plan_uses_fallback_model(monkeypatch):
    monkeypatch.delenv("OPENAI_MODEL", raising=False)
    client = FakeClient(response=FakeResponse(make_task_plan_json()))

    generate_task_plan("Compass", "", "Add login", "", [make_retrieved_chunk()], client=client)

    assert client.responses.calls[0]["model"] == "gpt-4o-mini"


def test_generate_task_plan_with_injected_client_does_not_require_api_key(monkeypatch):
    monkeypatch.delenv("OPENAI_API_KEY", raising=False)
    client = FakeClient(response=FakeResponse(make_task_plan_json()))

    task_plan = generate_task_plan(
        "Compass",
        "",
        "Add login",
        "",
        [make_retrieved_chunk()],
        client=client,
    )

    assert task_plan["goal"] == "Add login support."


@pytest.mark.parametrize("output_text", ["", "   ", None])
def test_generate_task_plan_rejects_empty_output(output_text):
    client = FakeClient(response=FakeResponse(output_text))

    with pytest.raises(RuntimeError, match="empty task plan"):
        generate_task_plan("Compass", "", "Add login", "", [make_retrieved_chunk()], client=client)


def test_generate_task_plan_rejects_invalid_json():
    client = FakeClient(response=FakeResponse("not json"))

    with pytest.raises(RuntimeError, match="invalid JSON task plan"):
        generate_task_plan("Compass", "", "Add login", "", [make_retrieved_chunk()], client=client)


def test_generate_task_plan_rejects_non_object_json():
    client = FakeClient(response=FakeResponse("[]"))

    with pytest.raises(RuntimeError, match="not a JSON object"):
        generate_task_plan("Compass", "", "Add login", "", [make_retrieved_chunk()], client=client)


def test_generate_task_plan_rejects_missing_required_keys():
    client = FakeClient(response=FakeResponse('{"goal": "Add login"}'))

    with pytest.raises(RuntimeError, match="missing keys"):
        generate_task_plan("Compass", "", "Add login", "", [make_retrieved_chunk()], client=client)


@pytest.mark.parametrize(
    "task_plan_json",
    [
        '{"goal": 123, "subtasks": [], "acceptance_criteria": [], "relevant_files": []}',
        '{"goal": "Goal", "subtasks": "step", "acceptance_criteria": [], "relevant_files": []}',
        '{"goal": "Goal", "subtasks": [123], "acceptance_criteria": [], "relevant_files": []}',
        '{"goal": "Goal", "subtasks": [], "acceptance_criteria": "criteria", "relevant_files": []}',
        '{"goal": "Goal", "subtasks": [], "acceptance_criteria": [123], "relevant_files": []}',
        '{"goal": "Goal", "subtasks": [], "acceptance_criteria": [], "relevant_files": "file.py"}',
        '{"goal": "Goal", "subtasks": [], "acceptance_criteria": [], "relevant_files": [123]}',
    ],
)
def test_generate_task_plan_rejects_wrong_value_types(task_plan_json):
    client = FakeClient(response=FakeResponse(task_plan_json))

    with pytest.raises(RuntimeError, match="task plan"):
        generate_task_plan("Compass", "", "Add login", "", [make_retrieved_chunk()], client=client)


def test_generate_task_plan_rejects_empty_goal():
    client = FakeClient(response=FakeResponse(make_task_plan_json(goal="   ")))

    with pytest.raises(RuntimeError, match="empty goal"):
        generate_task_plan("Compass", "", "Add login", "", [make_retrieved_chunk()], client=client)


def test_generate_task_plan_does_not_make_real_api_call_without_api_key(monkeypatch):
    def fail_if_openai_client_is_constructed(*args, **kwargs):
        raise AssertionError("OpenAI client should not be constructed without an API key.")

    monkeypatch.setattr(llm_service, "OpenAI", fail_if_openai_client_is_constructed)
    monkeypatch.delenv("OPENAI_API_KEY", raising=False)
    monkeypatch.delenv("OPENAI_MODEL", raising=False)

    with pytest.raises(ValueError, match="OPENAI_API_KEY"):
        generate_task_plan("Compass", "", "Add login", "", [make_retrieved_chunk()])


def test_generate_task_plan_wraps_openai_api_errors(monkeypatch):
    class FakeAPIError(Exception):
        pass

    original_error = FakeAPIError("boom")
    monkeypatch.setattr(llm_service, "APIError", FakeAPIError)
    client = FakeClient(error=original_error)

    with pytest.raises(RuntimeError, match="Could not generate a task plan") as error_info:
        generate_task_plan("Compass", "", "Add login", "", [make_retrieved_chunk()], client=client)

    assert error_info.value.__cause__ is original_error


def make_subtask_status_json(
    status="  done  ",
    reason="  Login is implemented in the auth service.  ",
    relevant_files=None,
):
    import json

    return json.dumps(
        {
            "status": status,
            "reason": reason,
            "relevant_files": relevant_files
            if relevant_files is not None
            else ["  services/auth_service.py  ", ""],
        }
    )


def test_build_subtask_status_prompt_includes_project_task_and_subtask_information():
    prompt = build_subtask_status_prompt(
        "Compass",
        "A codebase assistant.",
        "Add login",
        "Users can sign in.",
        "Update auth service",
        [make_retrieved_chunk()],
    )

    assert "Compass" in prompt
    assert "A codebase assistant." in prompt
    assert "Add login" in prompt
    assert "Users can sign in." in prompt
    assert "Update auth service" in prompt


def test_build_subtask_status_prompt_includes_source_information():
    chunk = make_retrieved_chunk(
        file_path="services/auth_service.py",
        start_line=12,
        end_line=30,
        content="def login_user():\n    return True",
    )

    prompt = build_subtask_status_prompt(
        "Compass",
        "",
        "Add login",
        "",
        "Update auth service",
        [chunk],
    )

    assert "File: services/auth_service.py" in prompt
    assert "Lines: 12-30" in prompt
    assert "def login_user():" in prompt


def test_build_subtask_status_prompt_includes_status_instructions():
    prompt = build_subtask_status_prompt(
        "Compass",
        "",
        "Add login",
        "",
        "Update auth service",
        [make_retrieved_chunk()],
    )
    prompt_lower = prompt.lower()

    assert "using only the supplied code context" in prompt_lower
    assert "return valid json only" in prompt_lower
    assert "do not use markdown" in prompt_lower
    assert "done, partial, missing, unclear" in prompt_lower
    assert "use unclear" in prompt_lower
    assert "use missing" in prompt_lower
    assert "use partial" in prompt_lower
    assert "use done" in prompt_lower


def test_build_subtask_status_prompt_excludes_retrieval_metadata():
    prompt = build_subtask_status_prompt(
        "Compass",
        "",
        "Add login",
        "",
        "Update auth service",
        [make_retrieved_chunk()],
    )

    assert "99" not in prompt
    assert "secret_metadata_value" not in prompt
    assert "matching_terms" not in prompt
    assert "score" not in prompt


def test_build_subtask_status_prompt_preserves_chunk_order():
    chunks = [
        make_retrieved_chunk("first.py", 1, 5, "first_content"),
        make_retrieved_chunk("second.py", 10, 15, "second_content"),
    ]

    prompt = build_subtask_status_prompt(
        "Compass",
        "",
        "Add login",
        "",
        "Update auth service",
        chunks,
    )

    assert prompt.index("SOURCE 1") < prompt.index("SOURCE 2")
    assert prompt.index("File: first.py") < prompt.index("File: second.py")
    assert prompt.index("first_content") < prompt.index("second_content")


def test_build_subtask_status_prompt_does_not_mutate_retrieved_chunks():
    chunks = [make_retrieved_chunk()]
    original_chunks = copy.deepcopy(chunks)

    build_subtask_status_prompt(
        "Compass",
        "",
        "Add login",
        "",
        "Update auth service",
        chunks,
    )

    assert chunks == original_chunks


@pytest.mark.parametrize("project_name", ["", "   "])
def test_build_subtask_status_prompt_rejects_empty_project_name(project_name):
    with pytest.raises(ValueError, match="Project name"):
        build_subtask_status_prompt(
            project_name,
            "",
            "Add login",
            "",
            "Update auth service",
            [make_retrieved_chunk()],
        )


@pytest.mark.parametrize("task_title", ["", "   "])
def test_build_subtask_status_prompt_rejects_empty_task_title(task_title):
    with pytest.raises(ValueError, match="Task title"):
        build_subtask_status_prompt(
            "Compass",
            "",
            task_title,
            "",
            "Update auth service",
            [make_retrieved_chunk()],
        )


@pytest.mark.parametrize("subtask", ["", "   "])
def test_build_subtask_status_prompt_rejects_empty_subtask(subtask):
    with pytest.raises(ValueError, match="Subtask"):
        build_subtask_status_prompt(
            "Compass",
            "",
            "Add login",
            "",
            subtask,
            [make_retrieved_chunk()],
        )


def test_build_subtask_status_prompt_rejects_empty_retrieved_chunks():
    with pytest.raises(ValueError, match="retrieved code chunk"):
        build_subtask_status_prompt("Compass", "", "Add login", "", "Update auth service", [])


@pytest.mark.parametrize(
    "missing_field",
    [
        "file_path",
        "start_line",
        "end_line",
        "content",
    ],
)
def test_build_subtask_status_prompt_rejects_missing_required_chunk_fields(missing_field):
    chunk = make_retrieved_chunk()
    del chunk[missing_field]

    with pytest.raises(ValueError, match=missing_field):
        build_subtask_status_prompt(
            "Compass",
            "",
            "Add login",
            "",
            "Update auth service",
            [chunk],
        )


def test_generate_subtask_status_calls_responses_api_with_prompt():
    client = FakeClient(response=FakeResponse(make_subtask_status_json()))

    generate_subtask_status(
        "Compass",
        "A codebase assistant.",
        "Add login",
        "Users can sign in.",
        "Update auth service",
        [make_retrieved_chunk()],
        client=client,
        model="test-model",
    )

    assert len(client.responses.calls) == 1
    call = client.responses.calls[0]
    assert call["model"] == "test-model"
    assert "Compass" in call["input"]
    assert "Add login" in call["input"]
    assert "Update auth service" in call["input"]
    assert "File: services/auth_service.py" in call["input"]


def test_generate_subtask_status_returns_cleaned_status_dictionary():
    client = FakeClient(response=FakeResponse(make_subtask_status_json()))

    status_result = generate_subtask_status(
        "Compass",
        "",
        "Add login",
        "",
        "Update auth service",
        [make_retrieved_chunk()],
        client=client,
    )

    assert status_result == {
        "status": "done",
        "reason": "Login is implemented in the auth service.",
        "relevant_files": ["services/auth_service.py"],
    }


@pytest.mark.parametrize("status", ["done", "partial", "missing", "unclear"])
def test_generate_subtask_status_accepts_allowed_status_values(status):
    client = FakeClient(response=FakeResponse(make_subtask_status_json(status=status)))

    status_result = generate_subtask_status(
        "Compass",
        "",
        "Add login",
        "",
        "Update auth service",
        [make_retrieved_chunk()],
        client=client,
    )

    assert status_result["status"] == status


def test_generate_subtask_status_uses_supplied_model():
    client = FakeClient(response=FakeResponse(make_subtask_status_json()))

    generate_subtask_status(
        "Compass",
        "",
        "Add login",
        "",
        "Update auth service",
        [make_retrieved_chunk()],
        client=client,
        model="custom-model",
    )

    assert client.responses.calls[0]["model"] == "custom-model"


def test_generate_subtask_status_uses_openai_model_environment_variable(monkeypatch):
    monkeypatch.setenv("OPENAI_MODEL", "env-model")
    client = FakeClient(response=FakeResponse(make_subtask_status_json()))

    generate_subtask_status(
        "Compass",
        "",
        "Add login",
        "",
        "Update auth service",
        [make_retrieved_chunk()],
        client=client,
    )

    assert client.responses.calls[0]["model"] == "env-model"


def test_generate_subtask_status_uses_fallback_model(monkeypatch):
    monkeypatch.delenv("OPENAI_MODEL", raising=False)
    client = FakeClient(response=FakeResponse(make_subtask_status_json()))

    generate_subtask_status(
        "Compass",
        "",
        "Add login",
        "",
        "Update auth service",
        [make_retrieved_chunk()],
        client=client,
    )

    assert client.responses.calls[0]["model"] == "gpt-4o-mini"


def test_generate_subtask_status_with_injected_client_does_not_require_api_key(monkeypatch):
    monkeypatch.delenv("OPENAI_API_KEY", raising=False)
    client = FakeClient(response=FakeResponse(make_subtask_status_json()))

    status_result = generate_subtask_status(
        "Compass",
        "",
        "Add login",
        "",
        "Update auth service",
        [make_retrieved_chunk()],
        client=client,
    )

    assert status_result["status"] == "done"


@pytest.mark.parametrize("output_text", ["", "   ", None])
def test_generate_subtask_status_rejects_empty_output(output_text):
    client = FakeClient(response=FakeResponse(output_text))

    with pytest.raises(RuntimeError, match="empty subtask status"):
        generate_subtask_status(
            "Compass",
            "",
            "Add login",
            "",
            "Update auth service",
            [make_retrieved_chunk()],
            client=client,
        )


def test_generate_subtask_status_rejects_invalid_json():
    client = FakeClient(response=FakeResponse("not json"))

    with pytest.raises(RuntimeError, match="invalid JSON subtask status"):
        generate_subtask_status(
            "Compass",
            "",
            "Add login",
            "",
            "Update auth service",
            [make_retrieved_chunk()],
            client=client,
        )


def test_generate_subtask_status_rejects_non_object_json():
    client = FakeClient(response=FakeResponse("[]"))

    with pytest.raises(RuntimeError, match="not a JSON object"):
        generate_subtask_status(
            "Compass",
            "",
            "Add login",
            "",
            "Update auth service",
            [make_retrieved_chunk()],
            client=client,
        )


def test_generate_subtask_status_rejects_missing_required_keys():
    client = FakeClient(response=FakeResponse('{"status": "done"}'))

    with pytest.raises(RuntimeError, match="missing keys"):
        generate_subtask_status(
            "Compass",
            "",
            "Add login",
            "",
            "Update auth service",
            [make_retrieved_chunk()],
            client=client,
        )


@pytest.mark.parametrize(
    "status_json",
    [
        '{"status": 123, "reason": "Done", "relevant_files": []}',
        '{"status": "done", "reason": 123, "relevant_files": []}',
        '{"status": "done", "reason": "Done", "relevant_files": "file.py"}',
        '{"status": "done", "reason": "Done", "relevant_files": [123]}',
    ],
)
def test_generate_subtask_status_rejects_wrong_value_types(status_json):
    client = FakeClient(response=FakeResponse(status_json))

    with pytest.raises(RuntimeError, match="subtask status"):
        generate_subtask_status(
            "Compass",
            "",
            "Add login",
            "",
            "Update auth service",
            [make_retrieved_chunk()],
            client=client,
        )


def test_generate_subtask_status_rejects_invalid_status():
    client = FakeClient(response=FakeResponse(make_subtask_status_json(status="blocked")))

    with pytest.raises(RuntimeError, match="unsupported subtask status"):
        generate_subtask_status(
            "Compass",
            "",
            "Add login",
            "",
            "Update auth service",
            [make_retrieved_chunk()],
            client=client,
        )


def test_generate_subtask_status_rejects_empty_reason():
    client = FakeClient(response=FakeResponse(make_subtask_status_json(reason="   ")))

    with pytest.raises(RuntimeError, match="empty reason"):
        generate_subtask_status(
            "Compass",
            "",
            "Add login",
            "",
            "Update auth service",
            [make_retrieved_chunk()],
            client=client,
        )


def test_generate_subtask_status_does_not_make_real_api_call_without_api_key(monkeypatch):
    def fail_if_openai_client_is_constructed(*args, **kwargs):
        raise AssertionError("OpenAI client should not be constructed without an API key.")

    monkeypatch.setattr(llm_service, "OpenAI", fail_if_openai_client_is_constructed)
    monkeypatch.delenv("OPENAI_API_KEY", raising=False)
    monkeypatch.delenv("OPENAI_MODEL", raising=False)

    with pytest.raises(ValueError, match="OPENAI_API_KEY"):
        generate_subtask_status(
            "Compass",
            "",
            "Add login",
            "",
            "Update auth service",
            [make_retrieved_chunk()],
        )


def test_generate_subtask_status_wraps_openai_api_errors(monkeypatch):
    class FakeAPIError(Exception):
        pass

    original_error = FakeAPIError("boom")
    monkeypatch.setattr(llm_service, "APIError", FakeAPIError)
    client = FakeClient(error=original_error)

    with pytest.raises(RuntimeError, match="Could not generate a subtask status") as error_info:
        generate_subtask_status(
            "Compass",
            "",
            "Add login",
            "",
            "Update auth service",
            [make_retrieved_chunk()],
            client=client,
        )

    assert error_info.value.__cause__ is original_error


def test_answer_codebase_question_calls_responses_api_with_prompt():
    client = FakeClient(response=FakeResponse("Login is handled in auth_service.py."))
    chunks = [make_retrieved_chunk()]

    answer_codebase_question("Where is login handled?", chunks, client=client, model="test-model")

    assert len(client.responses.calls) == 1
    call = client.responses.calls[0]
    assert call["model"] == "test-model"
    assert "Where is login handled?" in call["input"]
    assert "File: services/auth_service.py" in call["input"]


def test_answer_codebase_question_returns_stripped_generated_text():
    client = FakeClient(response=FakeResponse("  Login is handled in auth_service.py.  "))

    answer = answer_codebase_question("Where is login handled?", [make_retrieved_chunk()], client=client)

    assert answer == "Login is handled in auth_service.py."


def test_answer_codebase_question_uses_supplied_model():
    client = FakeClient(response=FakeResponse("Answer"))

    answer_codebase_question("Question?", [make_retrieved_chunk()], client=client, model="custom-model")

    assert client.responses.calls[0]["model"] == "custom-model"


def test_answer_codebase_question_uses_openai_model_environment_variable(monkeypatch):
    monkeypatch.setenv("OPENAI_MODEL", "env-model")
    client = FakeClient(response=FakeResponse("Answer"))

    answer_codebase_question("Question?", [make_retrieved_chunk()], client=client)

    assert client.responses.calls[0]["model"] == "env-model"


def test_answer_codebase_question_uses_fallback_model(monkeypatch):
    monkeypatch.delenv("OPENAI_MODEL", raising=False)
    client = FakeClient(response=FakeResponse("Answer"))

    answer_codebase_question("Question?", [make_retrieved_chunk()], client=client)

    assert client.responses.calls[0]["model"] == "gpt-4o-mini"


def test_answer_codebase_question_with_injected_client_does_not_require_api_key(monkeypatch):
    monkeypatch.delenv("OPENAI_API_KEY", raising=False)
    client = FakeClient(response=FakeResponse("Answer"))

    answer = answer_codebase_question("Question?", [make_retrieved_chunk()], client=client)

    assert answer == "Answer"


def test_answer_codebase_question_rejects_missing_api_key(monkeypatch):
    def fail_if_openai_client_is_constructed(*args, **kwargs):
        raise AssertionError("OpenAI client should not be constructed without an API key.")

    monkeypatch.setattr(llm_service, "load_dotenv", lambda *args, **kwargs: None)
    monkeypatch.setattr(llm_service, "OpenAI", fail_if_openai_client_is_constructed)
    monkeypatch.delenv("OPENAI_API_KEY", raising=False)
    monkeypatch.delenv("OPENAI_MODEL", raising=False)

    with pytest.raises(ValueError, match="OPENAI_API_KEY"):
        answer_codebase_question("Question?", [make_retrieved_chunk()])


@pytest.mark.parametrize("output_text", ["", "   ", None])
def test_answer_codebase_question_rejects_empty_output(output_text):
    client = FakeClient(response=FakeResponse(output_text))

    with pytest.raises(RuntimeError, match="empty answer"):
        answer_codebase_question("Question?", [make_retrieved_chunk()], client=client)


def test_answer_codebase_question_wraps_openai_api_errors(monkeypatch):
    class FakeAPIError(Exception):
        pass

    original_error = FakeAPIError("boom")
    monkeypatch.setattr(llm_service, "APIError", FakeAPIError)
    client = FakeClient(error=original_error)

    with pytest.raises(RuntimeError, match="Could not generate") as error_info:
        answer_codebase_question("Question?", [make_retrieved_chunk()], client=client)

    assert error_info.value.__cause__ is original_error
