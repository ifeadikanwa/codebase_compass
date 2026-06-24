import json
import uuid

from data.database import DEFAULT_DB_PATH, get_connection, initialize_database


def _initialize_code_chunks_table(db_path=DEFAULT_DB_PATH):
    initialize_database(db_path)

    with get_connection(db_path) as connection:
        connection.execute(
            """
            CREATE TABLE IF NOT EXISTS code_chunks (
                id TEXT PRIMARY KEY,
                project_id TEXT NOT NULL,
                file_path TEXT NOT NULL,
                start_line INTEGER NOT NULL,
                end_line INTEGER NOT NULL,
                content TEXT NOT NULL,
                embedding_json TEXT NOT NULL
            );
            """
        )


def _validate_project_id(project_id):
    cleaned_project_id = project_id.strip()
    if not cleaned_project_id:
        raise ValueError("Project ID is required.")

    return cleaned_project_id


def _row_to_code_chunk(row):
    if row is None:
        return None

    return {
        "id": row["id"],
        "project_id": row["project_id"],
        "file_path": row["file_path"],
        "start_line": row["start_line"],
        "end_line": row["end_line"],
        "content": row["content"],
        "embedding": json.loads(row["embedding_json"]),
    }


def replace_project_code_chunks(project_id, chunks, db_path=DEFAULT_DB_PATH):
    cleaned_project_id = _validate_project_id(project_id)
    _initialize_code_chunks_table(db_path)

    with get_connection(db_path) as connection:
        connection.execute(
            "DELETE FROM code_chunks WHERE project_id = ?;",
            (cleaned_project_id,),
        )

        for chunk in chunks:
            connection.execute(
                """
                INSERT INTO code_chunks (
                    id,
                    project_id,
                    file_path,
                    start_line,
                    end_line,
                    content,
                    embedding_json
                )
                VALUES (?, ?, ?, ?, ?, ?, ?);
                """,
                (
                    str(uuid.uuid4()),
                    cleaned_project_id,
                    chunk["file_path"],
                    chunk["start_line"],
                    chunk["end_line"],
                    chunk["content"],
                    json.dumps(chunk["embedding"]),
                ),
            )

    return list_project_code_chunks(cleaned_project_id, db_path=db_path)


def list_project_code_chunks(project_id, db_path=DEFAULT_DB_PATH):
    cleaned_project_id = _validate_project_id(project_id)
    _initialize_code_chunks_table(db_path)

    with get_connection(db_path) as connection:
        rows = connection.execute(
            """
            SELECT * FROM code_chunks
            WHERE project_id = ?
            ORDER BY file_path ASC, start_line ASC;
            """,
            (cleaned_project_id,),
        ).fetchall()

    return [_row_to_code_chunk(row) for row in rows]
