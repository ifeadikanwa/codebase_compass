import pytest

from utils.code_chunker import chunk_code_file


def make_lines(count: int) -> str:
    return "\n".join(f"line {line_number}" for line_number in range(1, count + 1))


def test_chunk_code_file_returns_one_chunk_for_short_file():
    content = "line 1\nline 2\nline 3"

    chunks = chunk_code_file("app.py", content, max_lines=10, overlap_lines=2)

    assert chunks == [
        {
            "file_path": "app.py",
            "start_line": 1,
            "end_line": 3,
            "content": content,
        }
    ]


def test_chunk_code_file_returns_one_chunk_for_exact_chunk_size():
    content = make_lines(4)

    chunks = chunk_code_file("app.py", content, max_lines=4, overlap_lines=1)

    assert chunks == [
        {
            "file_path": "app.py",
            "start_line": 1,
            "end_line": 4,
            "content": content,
        }
    ]


def test_chunk_code_file_creates_multiple_chunks_without_overlap():
    content = make_lines(8)

    chunks = chunk_code_file("app.py", content, max_lines=3, overlap_lines=0)

    assert chunks == [
        {
            "file_path": "app.py",
            "start_line": 1,
            "end_line": 3,
            "content": "line 1\nline 2\nline 3",
        },
        {
            "file_path": "app.py",
            "start_line": 4,
            "end_line": 6,
            "content": "line 4\nline 5\nline 6",
        },
        {
            "file_path": "app.py",
            "start_line": 7,
            "end_line": 8,
            "content": "line 7\nline 8",
        },
    ]


def test_chunk_code_file_creates_multiple_chunks_with_overlap():
    content = make_lines(9)

    chunks = chunk_code_file("app.py", content, max_lines=4, overlap_lines=1)

    assert chunks == [
        {
            "file_path": "app.py",
            "start_line": 1,
            "end_line": 4,
            "content": "line 1\nline 2\nline 3\nline 4",
        },
        {
            "file_path": "app.py",
            "start_line": 4,
            "end_line": 7,
            "content": "line 4\nline 5\nline 6\nline 7",
        },
        {
            "file_path": "app.py",
            "start_line": 7,
            "end_line": 9,
            "content": "line 7\nline 8\nline 9",
        },
    ]


def test_chunk_code_file_preserves_blank_lines():
    content = "def first():\n\n    return True\n\ndef second():\n    return False"

    chunks = chunk_code_file("app.py", content, max_lines=10, overlap_lines=2)

    assert chunks[0]["content"] == content


def test_chunk_code_file_returns_empty_list_for_empty_content():
    assert chunk_code_file("app.py", "") == []


@pytest.mark.parametrize(
    ("max_lines", "overlap_lines"),
    [
        (0, 0),
        (-1, 0),
        (5, -1),
        (5, 5),
        (5, 6),
    ],
)
def test_chunk_code_file_rejects_invalid_settings(max_lines, overlap_lines):
    with pytest.raises(ValueError):
        chunk_code_file(
            "app.py",
            "line 1\nline 2",
            max_lines=max_lines,
            overlap_lines=overlap_lines,
        )
