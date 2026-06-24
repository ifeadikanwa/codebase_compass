from utils.code_element_locator import extract_snippet_by_lines, locate_code_element


def test_extract_snippet_by_lines_uses_one_based_inclusive_lines():
    content = "line 1\nline 2\nline 3"

    snippet = extract_snippet_by_lines(content, 2, 3)

    assert snippet == {
        "start_line": 2,
        "end_line": 3,
        "snippet": "line 2\nline 3",
    }


def test_extract_snippet_by_lines_clamps_out_of_range_end_line():
    content = "line 1\nline 2"

    snippet = extract_snippet_by_lines(content, 1, 99)

    assert snippet == {
        "start_line": 1,
        "end_line": 2,
        "snippet": "line 1\nline 2",
    }


def test_extract_snippet_by_lines_rejects_invalid_start_line():
    assert extract_snippet_by_lines("line 1", 0, 1) == {
        "start_line": None,
        "end_line": None,
        "snippet": "",
    }


def test_extract_snippet_by_lines_rejects_end_line_before_start_line():
    assert extract_snippet_by_lines("line 1\nline 2", 2, 1) == {
        "start_line": None,
        "end_line": None,
        "snippet": "",
    }


def test_locate_code_element_finds_python_class():
    content = "class ShoppingCart:\n    def add_item(self):\n        pass\n"

    located = locate_code_element(
        "cart.py",
        content,
        {"name": "ShoppingCart", "kind": "class", "start_line": 99, "end_line": 99},
    )

    assert located["start_line"] == 1
    assert located["end_line"] == 3
    assert "class ShoppingCart:" in located["snippet"]
    assert located["source"] == "ast"


def test_locate_code_element_finds_python_methods_without_next_method():
    content = (
        "class ShoppingCart:\n"
        "    def __init__(self):\n"
        "        self.items = {}\n"
        "\n"
        "    def add_item(self, item):\n"
        "        self.items[item] = 1\n"
    )

    init_method = locate_code_element(
        "cart.py",
        content,
        {"name": "__init__", "kind": "method", "start_line": 99, "end_line": 99},
    )
    add_item_method = locate_code_element(
        "cart.py",
        content,
        {"name": "add_item", "kind": "method", "start_line": 99, "end_line": 99},
    )

    assert init_method["start_line"] == 2
    assert init_method["end_line"] == 3
    assert "def __init__" in init_method["snippet"]
    assert "def add_item" not in init_method["snippet"]
    assert init_method["source"] == "ast"
    assert add_item_method["start_line"] == 5
    assert "def add_item" in add_item_method["snippet"]
    assert add_item_method["source"] == "ast"


def test_locate_code_element_finds_python_function():
    content = "def calculate_total():\n    return 10\n"

    located = locate_code_element(
        "cart.py",
        content,
        {"name": "calculate_total", "kind": "function", "start_line": 99, "end_line": 99},
    )

    assert located["start_line"] == 1
    assert located["end_line"] == 2
    assert "def calculate_total" in located["snippet"]
    assert located["source"] == "ast"


def test_locate_code_element_finds_python_constant():
    content = "TAX_RATE = 0.06\n"

    located = locate_code_element(
        "cart.py",
        content,
        {"name": "TAX_RATE", "kind": "constant", "start_line": 99, "end_line": 99},
    )

    assert located["start_line"] == 1
    assert located["end_line"] == 1
    assert located["snippet"] == "TAX_RATE = 0.06"
    assert located["source"] == "ast"


def test_locate_code_element_finds_python_attribute_variable():
    content = "class Cart:\n    def __init__(self):\n        self.items = {}\n"

    located = locate_code_element(
        "cart.py",
        content,
        {"name": "items", "kind": "variable", "start_line": 99, "end_line": 99},
    )

    assert located["start_line"] == 3
    assert located["end_line"] == 3
    assert located["snippet"] == "        self.items = {}"
    assert located["source"] == "ast"


def test_locate_code_element_finds_python_import():
    content = "from models import Product\n"

    located = locate_code_element(
        "cart.py",
        content,
        {"name": "Product", "kind": "import", "start_line": 99, "end_line": 99},
    )

    assert located["start_line"] == 1
    assert located["end_line"] == 1
    assert located["snippet"] == "from models import Product"
    assert located["source"] == "ast"


def test_locate_code_element_falls_back_to_llm_lines_for_non_python_file():
    content = "first\nsecond\nthird"

    located = locate_code_element(
        "notes.txt",
        content,
        {"name": "second", "kind": "section", "start_line": 2, "end_line": 3},
    )

    assert located == {
        "start_line": 2,
        "end_line": 3,
        "snippet": "second\nthird",
        "source": "llm_lines",
    }


def test_locate_code_element_returns_unavailable_for_invalid_lines():
    located = locate_code_element(
        "notes.txt",
        "first\nsecond",
        {"name": "missing", "kind": "section", "start_line": None, "end_line": 3},
    )

    assert located == {
        "start_line": None,
        "end_line": None,
        "snippet": "",
        "source": "unavailable",
    }


def test_locate_code_element_falls_back_when_python_syntax_is_invalid():
    content = "def broken(:\n    pass\nfallback\n"

    located = locate_code_element(
        "broken.py",
        content,
        {"name": "broken", "kind": "function", "start_line": 3, "end_line": 3},
    )

    assert located == {
        "start_line": 3,
        "end_line": 3,
        "snippet": "fallback",
        "source": "llm_lines",
    }
