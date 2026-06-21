def normalize_generated_markdown(markdown_text):
    normalized_lines = []
    in_fenced_code_block = False

    for line in markdown_text.splitlines(keepends=True):
        line_without_newline = line.rstrip("\r\n")
        newline = line[len(line_without_newline) :]

        if line_without_newline.lstrip().startswith("```"):
            in_fenced_code_block = not in_fenced_code_block
            normalized_lines.append(line)
            continue

        if not in_fenced_code_block:
            stripped_line = line_without_newline.lstrip()
            indentation = line_without_newline[
                : len(line_without_newline) - len(stripped_line)
            ]

            for heading_prefix in ("### ", "## ", "# "):
                if stripped_line.startswith(heading_prefix):
                    heading_text = stripped_line[len(heading_prefix) :]
                    line = f"{indentation}#### {heading_text}{newline}"
                    break

        normalized_lines.append(line)

    return "".join(normalized_lines)
