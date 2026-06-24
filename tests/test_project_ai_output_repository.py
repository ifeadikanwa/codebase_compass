import json
import time

import pytest

from data.project_ai_output_repository import (
    CODEBASE_OVERVIEW_OUTPUT_TYPE,
    FILE_EXPLANATION_OUTPUT_TYPE_PREFIX,
    build_file_explanation_output_type,
    get_file_explanation,
    get_project_ai_output,
    list_file_explanations,
    list_project_ai_outputs,
    save_file_explanation,
    save_project_ai_output,
)
from data.project_repository import create_project_record


def create_sample_project(db_path, name="Good Shop"):
    return create_project_record(
        name=name,
        description="Command-line grocery shopping app",
        original_zip_filename="good_shop.zip",
        zip_file_size=12345,
        zip_path="storage/projects/good_shop/codebase.zip",
        codebase_path="storage/projects/good_shop/codebase",
        db_path=db_path,
    )


def test_save_project_ai_output_returns_saved_output(tmp_path):
    db_path = tmp_path / "test.db"
    project = create_sample_project(db_path)
    content = "#### Overview\n\nGenerated overview."

    output = save_project_ai_output(
        project["id"],
        CODEBASE_OVERVIEW_OUTPUT_TYPE,
        content,
        db_path=db_path,
    )

    assert output["id"]
    assert output["project_id"] == project["id"]
    assert output["output_type"] == CODEBASE_OVERVIEW_OUTPUT_TYPE
    assert output["content"] == content
    assert output["created_at"]
    assert output["updated_at"]


def test_get_project_ai_output_returns_saved_output(tmp_path):
    db_path = tmp_path / "test.db"
    project = create_sample_project(db_path)
    saved_output = save_project_ai_output(
        project["id"],
        CODEBASE_OVERVIEW_OUTPUT_TYPE,
        "#### Overview\n\nGenerated overview.",
        db_path=db_path,
    )

    loaded_output = get_project_ai_output(
        project["id"],
        CODEBASE_OVERVIEW_OUTPUT_TYPE,
        db_path=db_path,
    )

    assert loaded_output == saved_output


def test_get_project_ai_output_returns_none_for_missing_output(tmp_path):
    db_path = tmp_path / "test.db"
    project = create_sample_project(db_path)

    assert (
        get_project_ai_output(
            project["id"],
            CODEBASE_OVERVIEW_OUTPUT_TYPE,
            db_path=db_path,
        )
        is None
    )


def test_list_project_ai_outputs_returns_empty_list(tmp_path):
    db_path = tmp_path / "test.db"
    project = create_sample_project(db_path)

    assert list_project_ai_outputs(project["id"], db_path=db_path) == []


def test_list_project_ai_outputs_returns_only_project_outputs(tmp_path):
    db_path = tmp_path / "test.db"
    project = create_sample_project(db_path, name="Good Shop")
    other_project = create_sample_project(db_path, name="Other Shop")
    overview = save_project_ai_output(
        project["id"],
        CODEBASE_OVERVIEW_OUTPUT_TYPE,
        "Overview content",
        db_path=db_path,
    )
    setup = save_project_ai_output(
        project["id"],
        "setup_instructions",
        "Setup content",
        db_path=db_path,
    )
    save_project_ai_output(
        other_project["id"],
        CODEBASE_OVERVIEW_OUTPUT_TYPE,
        "Other overview",
        db_path=db_path,
    )

    outputs = list_project_ai_outputs(project["id"], db_path=db_path)

    assert outputs == [overview, setup]


def test_save_project_ai_output_upserts_existing_output(tmp_path):
    db_path = tmp_path / "test.db"
    project = create_sample_project(db_path)
    first_output = save_project_ai_output(
        project["id"],
        CODEBASE_OVERVIEW_OUTPUT_TYPE,
        "First overview",
        db_path=db_path,
    )
    time.sleep(0.001)

    second_output = save_project_ai_output(
        project["id"],
        CODEBASE_OVERVIEW_OUTPUT_TYPE,
        "Updated overview",
        db_path=db_path,
    )
    outputs = list_project_ai_outputs(project["id"], db_path=db_path)

    assert len(outputs) == 1
    assert second_output["id"] == first_output["id"]
    assert second_output["created_at"] == first_output["created_at"]
    assert second_output["updated_at"] > first_output["updated_at"]
    assert second_output["content"] == "Updated overview"


def test_same_project_can_store_multiple_output_types(tmp_path):
    db_path = tmp_path / "test.db"
    project = create_sample_project(db_path)

    overview = save_project_ai_output(
        project["id"],
        CODEBASE_OVERVIEW_OUTPUT_TYPE,
        "Overview",
        db_path=db_path,
    )
    setup = save_project_ai_output(
        project["id"],
        "setup_instructions",
        "Setup",
        db_path=db_path,
    )

    assert list_project_ai_outputs(project["id"], db_path=db_path) == [overview, setup]


def test_same_output_type_is_allowed_for_different_projects(tmp_path):
    db_path = tmp_path / "test.db"
    first_project = create_sample_project(db_path, name="First")
    second_project = create_sample_project(db_path, name="Second")

    first_output = save_project_ai_output(
        first_project["id"],
        CODEBASE_OVERVIEW_OUTPUT_TYPE,
        "First overview",
        db_path=db_path,
    )
    second_output = save_project_ai_output(
        second_project["id"],
        CODEBASE_OVERVIEW_OUTPUT_TYPE,
        "Second overview",
        db_path=db_path,
    )

    assert first_output["project_id"] == first_project["id"]
    assert second_output["project_id"] == second_project["id"]


@pytest.mark.parametrize("project_id", ["", "   "])
def test_save_project_ai_output_rejects_empty_project_id(tmp_path, project_id):
    with pytest.raises(ValueError, match="Project ID"):
        save_project_ai_output(
            project_id,
            CODEBASE_OVERVIEW_OUTPUT_TYPE,
            "Overview",
            db_path=tmp_path / "test.db",
        )


@pytest.mark.parametrize("output_type", ["", "   "])
def test_save_project_ai_output_rejects_empty_output_type(tmp_path, output_type):
    with pytest.raises(ValueError, match="Output type"):
        save_project_ai_output(
            "project-1",
            output_type,
            "Overview",
            db_path=tmp_path / "test.db",
        )


@pytest.mark.parametrize("content", ["", "   "])
def test_save_project_ai_output_rejects_empty_content(tmp_path, content):
    with pytest.raises(ValueError, match="Content"):
        save_project_ai_output(
            "project-1",
            CODEBASE_OVERVIEW_OUTPUT_TYPE,
            content,
            db_path=tmp_path / "test.db",
        )


def test_save_project_ai_output_rejects_missing_project(tmp_path):
    with pytest.raises(ValueError, match="Project does not exist"):
        save_project_ai_output(
            "missing-project",
            CODEBASE_OVERVIEW_OUTPUT_TYPE,
            "Overview",
            db_path=tmp_path / "test.db",
        )


def test_get_project_ai_output_rejects_empty_values(tmp_path):
    with pytest.raises(ValueError, match="Project ID"):
        get_project_ai_output("", CODEBASE_OVERVIEW_OUTPUT_TYPE, db_path=tmp_path / "test.db")

    with pytest.raises(ValueError, match="Output type"):
        get_project_ai_output("project-1", "", db_path=tmp_path / "test.db")


def test_list_project_ai_outputs_rejects_empty_project_id(tmp_path):
    with pytest.raises(ValueError, match="Project ID"):
        list_project_ai_outputs("", db_path=tmp_path / "test.db")


def test_project_ai_output_persists_across_connections(tmp_path):
    db_path = tmp_path / "test.db"
    project = create_sample_project(db_path)
    saved_output = save_project_ai_output(
        project["id"],
        CODEBASE_OVERVIEW_OUTPUT_TYPE,
        "Overview",
        db_path=db_path,
    )

    loaded_output = get_project_ai_output(
        project["id"],
        CODEBASE_OVERVIEW_OUTPUT_TYPE,
        db_path=db_path,
    )

    assert loaded_output == saved_output


def make_file_explanation(summary="Explains cart behavior.", elements=None):
    return {
        "file_path": "cart.py",
        "summary": summary,
        "elements": elements if elements is not None else [],
    }


def test_build_file_explanation_output_type_uses_prefix():
    assert (
        build_file_explanation_output_type("cart.py")
        == f"{FILE_EXPLANATION_OUTPUT_TYPE_PREFIX}cart.py"
    )


def test_build_file_explanation_output_type_removes_leading_current_directory():
    assert (
        build_file_explanation_output_type("./services/cart.py")
        == f"{FILE_EXPLANATION_OUTPUT_TYPE_PREFIX}services/cart.py"
    )


def test_build_file_explanation_output_type_normalizes_backslashes():
    assert (
        build_file_explanation_output_type("services\\cart.py")
        == f"{FILE_EXPLANATION_OUTPUT_TYPE_PREFIX}services/cart.py"
    )


def test_build_file_explanation_output_type_strips_whitespace():
    assert (
        build_file_explanation_output_type("  cart.py  ")
        == f"{FILE_EXPLANATION_OUTPUT_TYPE_PREFIX}cart.py"
    )


@pytest.mark.parametrize("file_path", ["", "   "])
def test_build_file_explanation_output_type_rejects_empty_path(file_path):
    with pytest.raises(ValueError, match="File path"):
        build_file_explanation_output_type(file_path)


def test_save_file_explanation_returns_saved_output(tmp_path):
    db_path = tmp_path / "test.db"
    project = create_sample_project(db_path)
    explanation = make_file_explanation()

    output = save_file_explanation(
        project["id"],
        "cart.py",
        explanation,
        db_path=db_path,
    )

    assert output["id"]
    assert output["project_id"] == project["id"]
    assert output["output_type"] == f"{FILE_EXPLANATION_OUTPUT_TYPE_PREFIX}cart.py"
    assert json.loads(output["content"]) == explanation


def test_get_file_explanation_returns_saved_explanation(tmp_path):
    db_path = tmp_path / "test.db"
    project = create_sample_project(db_path)
    explanation = make_file_explanation(
        summary="Cart logic.",
        elements=[
            {
                "name": "ShoppingCart",
                "kind": "class",
                "start_line": 1,
                "end_line": 20,
                "explanation": "Stores cart items.",
            }
        ],
    )

    save_file_explanation(project["id"], "cart.py", explanation, db_path=db_path)

    loaded_explanation = get_file_explanation(project["id"], "cart.py", db_path=db_path)

    assert loaded_explanation == explanation


def test_get_file_explanation_returns_none_for_missing_explanation(tmp_path):
    db_path = tmp_path / "test.db"
    project = create_sample_project(db_path)

    assert get_file_explanation(project["id"], "cart.py", db_path=db_path) is None


def test_save_file_explanation_upserts_existing_file_explanation(tmp_path):
    db_path = tmp_path / "test.db"
    project = create_sample_project(db_path)
    first_explanation = make_file_explanation(summary="First summary.")
    second_explanation = make_file_explanation(summary="Updated summary.")

    first_output = save_file_explanation(
        project["id"],
        "cart.py",
        first_explanation,
        db_path=db_path,
    )
    time.sleep(0.001)
    second_output = save_file_explanation(
        project["id"],
        "cart.py",
        second_explanation,
        db_path=db_path,
    )

    outputs = list_project_ai_outputs(project["id"], db_path=db_path)

    assert len(outputs) == 1
    assert second_output["id"] == first_output["id"]
    assert second_output["created_at"] == first_output["created_at"]
    assert second_output["updated_at"] > first_output["updated_at"]
    assert get_file_explanation(project["id"], "cart.py", db_path=db_path) == second_explanation


def test_same_file_explanation_path_is_allowed_for_different_projects(tmp_path):
    db_path = tmp_path / "test.db"
    first_project = create_sample_project(db_path, name="First")
    second_project = create_sample_project(db_path, name="Second")
    first_explanation = make_file_explanation(summary="First project.")
    second_explanation = make_file_explanation(summary="Second project.")

    save_file_explanation(first_project["id"], "cart.py", first_explanation, db_path=db_path)
    save_file_explanation(second_project["id"], "cart.py", second_explanation, db_path=db_path)

    assert (
        get_file_explanation(first_project["id"], "cart.py", db_path=db_path)
        == first_explanation
    )
    assert (
        get_file_explanation(second_project["id"], "cart.py", db_path=db_path)
        == second_explanation
    )


def test_list_file_explanations_returns_only_file_explanations(tmp_path):
    db_path = tmp_path / "test.db"
    project = create_sample_project(db_path)
    cart_explanation = make_file_explanation(summary="Cart.")
    checkout_explanation = make_file_explanation(summary="Checkout.")
    save_project_ai_output(
        project["id"],
        CODEBASE_OVERVIEW_OUTPUT_TYPE,
        "Overview",
        db_path=db_path,
    )
    cart_output = save_file_explanation(
        project["id"],
        "cart.py",
        cart_explanation,
        db_path=db_path,
    )
    checkout_output = save_file_explanation(
        project["id"],
        "services/checkout.py",
        checkout_explanation,
        db_path=db_path,
    )

    explanations = list_file_explanations(project["id"], db_path=db_path)

    assert explanations == [
        {
            "file_path": "cart.py",
            "explanation": cart_explanation,
            "created_at": cart_output["created_at"],
            "updated_at": cart_output["updated_at"],
        },
        {
            "file_path": "services/checkout.py",
            "explanation": checkout_explanation,
            "created_at": checkout_output["created_at"],
            "updated_at": checkout_output["updated_at"],
        },
    ]


@pytest.mark.parametrize("project_id", ["", "   "])
def test_file_explanation_helpers_reject_empty_project_id(tmp_path, project_id):
    db_path = tmp_path / "test.db"

    with pytest.raises(ValueError, match="Project ID"):
        save_file_explanation(project_id, "cart.py", make_file_explanation(), db_path=db_path)

    with pytest.raises(ValueError, match="Project ID"):
        get_file_explanation(project_id, "cart.py", db_path=db_path)

    with pytest.raises(ValueError, match="Project ID"):
        list_file_explanations(project_id, db_path=db_path)


@pytest.mark.parametrize("file_path", ["", "   "])
def test_file_explanation_helpers_reject_empty_file_path(tmp_path, file_path):
    db_path = tmp_path / "test.db"
    project = create_sample_project(db_path)

    with pytest.raises(ValueError, match="File path"):
        save_file_explanation(project["id"], file_path, make_file_explanation(), db_path=db_path)

    with pytest.raises(ValueError, match="File path"):
        get_file_explanation(project["id"], file_path, db_path=db_path)


@pytest.mark.parametrize("explanation", [None, [], "explanation"])
def test_save_file_explanation_rejects_non_dictionary_explanation(tmp_path, explanation):
    db_path = tmp_path / "test.db"
    project = create_sample_project(db_path)

    with pytest.raises(ValueError, match="dictionary"):
        save_file_explanation(project["id"], "cart.py", explanation, db_path=db_path)


def test_get_file_explanation_raises_for_invalid_stored_json(tmp_path):
    db_path = tmp_path / "test.db"
    project = create_sample_project(db_path)
    save_project_ai_output(
        project["id"],
        build_file_explanation_output_type("cart.py"),
        "not json",
        db_path=db_path,
    )

    with pytest.raises(RuntimeError, match="invalid JSON"):
        get_file_explanation(project["id"], "cart.py", db_path=db_path)


def test_list_file_explanations_raises_for_invalid_stored_json(tmp_path):
    db_path = tmp_path / "test.db"
    project = create_sample_project(db_path)
    save_project_ai_output(
        project["id"],
        build_file_explanation_output_type("cart.py"),
        "not json",
        db_path=db_path,
    )

    with pytest.raises(RuntimeError, match="invalid JSON"):
        list_file_explanations(project["id"], db_path=db_path)
