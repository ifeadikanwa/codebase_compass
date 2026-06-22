import pytest

from data.project_repository import (
    create_project_record,
    delete_project_record,
    get_project_record_by_id,
    get_project_record_by_name,
    list_project_records,
    update_project_record,
)
from data.project_ai_output_repository import (
    CODEBASE_OVERVIEW_OUTPUT_TYPE,
    get_project_ai_output,
    save_project_ai_output,
)
from data.task_repository import create_task_record, get_task_record_by_id


def create_sample_project(db_path, name="Good Shop"):
    return create_project_record(
        name=name,
        description=" Command-line grocery shopping app ",
        original_zip_filename="good_shop.zip",
        zip_file_size=12345,
        zip_path="storage/projects/good_shop/codebase.zip",
        codebase_path="storage/projects/good_shop/codebase",
        db_path=db_path,
    )


def test_create_project_record_returns_saved_project(tmp_path):
    db_path = tmp_path / "test.db"

    project = create_project_record(
        name="  Good Shop  ",
        description="  Command-line grocery shopping app  ",
        original_zip_filename="good_shop.zip",
        zip_file_size=12345,
        zip_path="storage/projects/good_shop/codebase.zip",
        codebase_path="storage/projects/good_shop/codebase",
        db_path=db_path,
    )

    assert project["id"]
    assert project["name"] == "Good Shop"
    assert project["description"] == "Command-line grocery shopping app"
    assert project["original_zip_filename"] == "good_shop.zip"
    assert project["zip_file_size"] == 12345
    assert project["zip_path"] == "storage/projects/good_shop/codebase.zip"
    assert project["codebase_path"] == "storage/projects/good_shop/codebase"
    assert project["created_at"]
    assert project["updated_at"]


@pytest.mark.parametrize("name", ["", "   "])
def test_create_project_record_rejects_empty_name(tmp_path, name):
    with pytest.raises(ValueError, match="name"):
        create_project_record(
            name=name,
            description="Description",
            original_zip_filename="project.zip",
            zip_file_size=123,
            zip_path="storage/projects/project/codebase.zip",
            codebase_path="storage/projects/project/codebase",
            db_path=tmp_path / "test.db",
        )


@pytest.mark.parametrize(
    ("field", "value", "message"),
    [
        ("original_zip_filename", "", "filename"),
        ("zip_path", "", "ZIP path"),
        ("codebase_path", "", "Codebase path"),
    ],
)
def test_create_project_record_rejects_empty_required_fields(tmp_path, field, value, message):
    kwargs = {
        "name": "Good Shop",
        "description": "Description",
        "original_zip_filename": "project.zip",
        "zip_file_size": 123,
        "zip_path": "storage/projects/project/codebase.zip",
        "codebase_path": "storage/projects/project/codebase",
        "db_path": tmp_path / "test.db",
    }
    kwargs[field] = value

    with pytest.raises(ValueError, match=message):
        create_project_record(**kwargs)


def test_create_project_record_rejects_negative_zip_file_size(tmp_path):
    with pytest.raises(ValueError, match="size"):
        create_project_record(
            name="Good Shop",
            description="Description",
            original_zip_filename="project.zip",
            zip_file_size=-1,
            zip_path="storage/projects/project/codebase.zip",
            codebase_path="storage/projects/project/codebase",
            db_path=tmp_path / "test.db",
        )


def test_create_project_record_rejects_duplicate_project_name(tmp_path):
    db_path = tmp_path / "test.db"
    create_sample_project(db_path, name="Good Shop")

    with pytest.raises(ValueError, match="already exists"):
        create_sample_project(db_path, name="Good Shop")


def test_list_project_records_returns_empty_list(tmp_path):
    assert list_project_records(db_path=tmp_path / "test.db") == []


def test_list_project_records_returns_created_projects_in_order(tmp_path):
    db_path = tmp_path / "test.db"
    first_project = create_sample_project(db_path, name="First")
    second_project = create_sample_project(db_path, name="Second")

    projects = list_project_records(db_path=db_path)

    assert projects == [first_project, second_project]
    assert all(isinstance(project, dict) for project in projects)


def test_get_project_record_by_id_returns_existing_project(tmp_path):
    db_path = tmp_path / "test.db"
    project = create_sample_project(db_path)

    assert get_project_record_by_id(project["id"], db_path=db_path) == project


def test_get_project_record_by_id_returns_none_for_missing_project(tmp_path):
    assert get_project_record_by_id("missing", db_path=tmp_path / "test.db") is None


@pytest.mark.parametrize("project_id", ["", "   "])
def test_get_project_record_by_id_rejects_empty_id(tmp_path, project_id):
    with pytest.raises(ValueError, match="ID"):
        get_project_record_by_id(project_id, db_path=tmp_path / "test.db")


def test_get_project_record_by_name_returns_existing_project(tmp_path):
    db_path = tmp_path / "test.db"
    project = create_sample_project(db_path, name="Good Shop")

    assert get_project_record_by_name("Good Shop", db_path=db_path) == project


def test_get_project_record_by_name_strips_lookup_name(tmp_path):
    db_path = tmp_path / "test.db"
    project = create_sample_project(db_path, name="Good Shop")

    assert get_project_record_by_name("  Good Shop  ", db_path=db_path) == project


def test_get_project_record_by_name_returns_none_for_missing_project(tmp_path):
    assert get_project_record_by_name("Missing", db_path=tmp_path / "test.db") is None


@pytest.mark.parametrize("name", ["", "   "])
def test_get_project_record_by_name_rejects_empty_name(tmp_path, name):
    with pytest.raises(ValueError, match="name"):
        get_project_record_by_name(name, db_path=tmp_path / "test.db")


def test_project_records_persist_across_connections(tmp_path):
    db_path = tmp_path / "test.db"
    project = create_sample_project(db_path)

    loaded_project = get_project_record_by_id(project["id"], db_path=db_path)

    assert loaded_project == project


def test_update_project_record_updates_project_name(tmp_path):
    db_path = tmp_path / "test.db"
    project = create_sample_project(db_path)

    updated_project = update_project_record(
        {
            **project,
            "name": "Updated Shop",
        },
        db_path=db_path,
    )

    assert updated_project["name"] == "Updated Shop"
    assert get_project_record_by_id(project["id"], db_path=db_path)["name"] == "Updated Shop"


def test_update_project_record_updates_and_strips_description(tmp_path):
    db_path = tmp_path / "test.db"
    project = create_sample_project(db_path)

    updated_project = update_project_record(
        {
            **project,
            "description": "  Updated description  ",
        },
        db_path=db_path,
    )

    assert updated_project["description"] == "Updated description"


def test_update_project_record_preserves_storage_fields_and_created_at(tmp_path):
    db_path = tmp_path / "test.db"
    project = create_sample_project(db_path)

    updated_project = update_project_record(
        {
            **project,
            "name": "Updated Shop",
            "description": "Updated description",
            "original_zip_filename": "changed.zip",
            "zip_file_size": 999,
            "zip_path": "changed/codebase.zip",
            "codebase_path": "changed/codebase",
            "created_at": "changed",
        },
        db_path=db_path,
    )

    assert updated_project["original_zip_filename"] == project["original_zip_filename"]
    assert updated_project["zip_file_size"] == project["zip_file_size"]
    assert updated_project["zip_path"] == project["zip_path"]
    assert updated_project["codebase_path"] == project["codebase_path"]
    assert updated_project["created_at"] == project["created_at"]


def test_update_project_record_refreshes_updated_at(tmp_path):
    db_path = tmp_path / "test.db"
    project = create_sample_project(db_path)

    updated_project = update_project_record(
        {
            **project,
            "description": "Updated description",
        },
        db_path=db_path,
    )

    assert updated_project["updated_at"]
    assert updated_project["updated_at"] >= project["updated_at"]


def test_update_project_record_returns_none_for_missing_project(tmp_path):
    db_path = tmp_path / "test.db"

    assert (
        update_project_record(
            {
                "id": "missing-project",
                "name": "Missing",
                "description": "Missing description",
            },
            db_path=db_path,
        )
        is None
    )


def test_update_project_record_rejects_missing_id(tmp_path):
    with pytest.raises(ValueError, match="ID"):
        update_project_record(
            {
                "name": "Good Shop",
                "description": "Description",
            },
            db_path=tmp_path / "test.db",
        )


@pytest.mark.parametrize("project_id", ["", "   "])
def test_update_project_record_rejects_empty_id(tmp_path, project_id):
    with pytest.raises(ValueError, match="ID"):
        update_project_record(
            {
                "id": project_id,
                "name": "Good Shop",
                "description": "Description",
            },
            db_path=tmp_path / "test.db",
        )


def test_update_project_record_rejects_missing_name(tmp_path):
    with pytest.raises(ValueError, match="name"):
        update_project_record(
            {
                "id": "project-1",
                "description": "Description",
            },
            db_path=tmp_path / "test.db",
        )


@pytest.mark.parametrize("name", ["", "   "])
def test_update_project_record_rejects_empty_name(tmp_path, name):
    with pytest.raises(ValueError, match="name"):
        update_project_record(
            {
                "id": "project-1",
                "name": name,
                "description": "Description",
            },
            db_path=tmp_path / "test.db",
        )


def test_update_project_record_rejects_duplicate_project_name(tmp_path):
    db_path = tmp_path / "test.db"
    first_project = create_sample_project(db_path, name="First")
    second_project = create_sample_project(db_path, name="Second")

    with pytest.raises(ValueError, match="already exists"):
        update_project_record({**second_project, "name": first_project["name"]}, db_path=db_path)

    assert get_project_record_by_id(first_project["id"], db_path=db_path) == first_project
    assert get_project_record_by_id(second_project["id"], db_path=db_path) == second_project


def test_update_project_record_persists_across_connections(tmp_path):
    db_path = tmp_path / "test.db"
    project = create_sample_project(db_path)

    update_project_record(
        {
            **project,
            "name": "Updated Shop",
            "description": "Updated description",
        },
        db_path=db_path,
    )
    loaded_project = get_project_record_by_id(project["id"], db_path=db_path)

    assert loaded_project["name"] == "Updated Shop"
    assert loaded_project["description"] == "Updated description"


def test_delete_project_record_deletes_existing_project(tmp_path):
    db_path = tmp_path / "test.db"
    project = create_sample_project(db_path)

    deleted = delete_project_record(project["id"], db_path=db_path)

    assert deleted is True
    assert get_project_record_by_id(project["id"], db_path=db_path) is None
    assert list_project_records(db_path=db_path) == []


def test_delete_project_record_returns_false_for_missing_project(tmp_path):
    assert delete_project_record("missing-project", db_path=tmp_path / "test.db") is False


@pytest.mark.parametrize("project_id", ["", "   "])
def test_delete_project_record_rejects_empty_id(tmp_path, project_id):
    with pytest.raises(ValueError, match="Project ID"):
        delete_project_record(project_id, db_path=tmp_path / "test.db")


def test_delete_project_record_deletes_only_one_project(tmp_path):
    db_path = tmp_path / "test.db"
    first_project = create_sample_project(db_path, name="First")
    second_project = create_sample_project(db_path, name="Second")

    assert delete_project_record(first_project["id"], db_path=db_path) is True

    assert get_project_record_by_id(first_project["id"], db_path=db_path) is None
    assert get_project_record_by_id(second_project["id"], db_path=db_path) == second_project
    assert list_project_records(db_path=db_path) == [second_project]


def test_delete_project_record_cascades_to_tasks_and_ai_outputs(tmp_path):
    db_path = tmp_path / "test.db"
    project = create_sample_project(db_path)
    task = create_task_record(
        project["id"],
        {
            "id": "task-1",
            "title": "Add login",
            "description": "Users should be able to sign in.",
        },
        db_path=db_path,
    )
    save_project_ai_output(
        project["id"],
        CODEBASE_OVERVIEW_OUTPUT_TYPE,
        "Generated overview",
        db_path=db_path,
    )

    delete_project_record(project["id"], db_path=db_path)

    assert get_task_record_by_id(task["id"], db_path=db_path) is None
    assert (
        get_project_ai_output(
            project["id"],
            CODEBASE_OVERVIEW_OUTPUT_TYPE,
            db_path=db_path,
        )
        is None
    )


def test_delete_project_record_persists_across_connections(tmp_path):
    db_path = tmp_path / "test.db"
    project = create_sample_project(db_path)

    delete_project_record(project["id"], db_path=db_path)

    assert get_project_record_by_id(project["id"], db_path=db_path) is None
