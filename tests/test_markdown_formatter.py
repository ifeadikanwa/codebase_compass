from utils.markdown_formatter import normalize_generated_markdown


def test_normalize_generated_markdown_converts_h1_to_h4():
    assert normalize_generated_markdown("# Title") == "#### Title"


def test_normalize_generated_markdown_converts_h2_to_h4():
    assert normalize_generated_markdown("## Summary") == "#### Summary"


def test_normalize_generated_markdown_converts_h3_to_h4():
    assert normalize_generated_markdown("### Files") == "#### Files"


def test_normalize_generated_markdown_leaves_h4_unchanged():
    assert normalize_generated_markdown("#### Details") == "#### Details"


def test_normalize_generated_markdown_preserves_paragraphs():
    assert normalize_generated_markdown("A normal paragraph.") == "A normal paragraph."


def test_normalize_generated_markdown_preserves_bullet_lists():
    markdown = "- First item\n- Second item"

    assert normalize_generated_markdown(markdown) == markdown


def test_normalize_generated_markdown_preserves_inline_code():
    markdown = "- `main.py`: Entry point"

    assert normalize_generated_markdown(markdown) == markdown


def test_normalize_generated_markdown_preserves_blank_lines():
    markdown = "# Title\n\nParagraph"

    assert normalize_generated_markdown(markdown) == "#### Title\n\nParagraph"


def test_normalize_generated_markdown_ignores_headings_inside_fenced_code_blocks():
    markdown = "```markdown\n# Title\n## Summary\n```\n# Real Title"
    expected = "```markdown\n# Title\n## Summary\n```\n#### Real Title"

    assert normalize_generated_markdown(markdown) == expected


def test_normalize_generated_markdown_returns_empty_string_for_empty_string():
    assert normalize_generated_markdown("") == ""
