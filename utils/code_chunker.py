def chunk_code_file(
    file_path: str,
    content: str,
    max_lines: int = 40,
    overlap_lines: int = 5,
) -> list[dict]:
    if max_lines <= 0:
        raise ValueError("max_lines must be greater than zero.")

    if overlap_lines < 0:
        raise ValueError("overlap_lines must not be negative.")

    if overlap_lines >= max_lines:
        raise ValueError("overlap_lines must be less than max_lines.")

    if not content:
        return []

    lines = content.splitlines()
    chunks = []
    step_size = max_lines - overlap_lines
    start_index = 0

    while start_index < len(lines):
        end_index = min(start_index + max_lines, len(lines))
        chunk_lines = lines[start_index:end_index]

        chunks.append(
            {
                "file_path": file_path,
                "start_line": start_index + 1,
                "end_line": end_index,
                "content": "\n".join(chunk_lines),
            }
        )

        if end_index == len(lines):
            break

        start_index += step_size

    return chunks
