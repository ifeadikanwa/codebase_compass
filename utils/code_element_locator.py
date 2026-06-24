import ast
from pathlib import Path


def extract_snippet_by_lines(file_content, start_line, end_line):
    if (
        isinstance(start_line, bool)
        or isinstance(end_line, bool)
        or not isinstance(start_line, int)
        or not isinstance(end_line, int)
        or start_line < 1
        or end_line < start_line
    ):
        return {
            "start_line": None,
            "end_line": None,
            "snippet": "",
        }

    lines = file_content.splitlines()
    if not lines or start_line > len(lines):
        return {
            "start_line": None,
            "end_line": None,
            "snippet": "",
        }

    clamped_end_line = min(end_line, len(lines))

    return {
        "start_line": start_line,
        "end_line": clamped_end_line,
        "snippet": "\n".join(lines[start_line - 1:clamped_end_line]),
    }


def locate_code_element(file_path, file_content, element):
    if _is_python_file(file_path):
        located_element = _locate_python_code_element(file_content, element)
        if located_element is not None:
            return located_element

    return _fallback_from_element_lines(file_content, element)


def _is_python_file(file_path):
    return Path(str(file_path)).suffix.lower() == ".py"


def _locate_python_code_element(file_content, element):
    try:
        tree = ast.parse(file_content)
    except SyntaxError:
        return None

    element_name = element.get("name")
    if not isinstance(element_name, str) or not element_name.strip():
        return None

    cleaned_name = element_name.strip()
    kind = element.get("kind")
    cleaned_kind = kind.strip() if isinstance(kind, str) else "other"

    for node in ast.walk(tree):
        if _node_matches_element(node, cleaned_name, cleaned_kind):
            return _located_from_node(file_content, node)

    return None


def _node_matches_element(node, element_name, kind):
    if kind == "class":
        return isinstance(node, ast.ClassDef) and node.name == element_name

    if kind in {"function", "method"}:
        return isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef)) and (
            node.name == element_name
        )

    if kind in {"variable", "constant"}:
        return _assignment_matches_element(node, element_name)

    if kind == "import":
        return _import_matches_element(node, element_name)

    return (
        (isinstance(node, ast.ClassDef) and node.name == element_name)
        or (
            isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef))
            and node.name == element_name
        )
        or _assignment_matches_element(node, element_name)
        or _import_matches_element(node, element_name)
    )


def _assignment_matches_element(node, element_name):
    if isinstance(node, ast.Assign):
        return any(_assignment_target_matches(target, element_name) for target in node.targets)

    if isinstance(node, (ast.AnnAssign, ast.AugAssign)):
        return _assignment_target_matches(node.target, element_name)

    return False


def _assignment_target_matches(target, element_name):
    if isinstance(target, ast.Name):
        return target.id == element_name

    if isinstance(target, ast.Attribute):
        return target.attr == element_name

    if isinstance(target, (ast.Tuple, ast.List)):
        return any(_assignment_target_matches(item, element_name) for item in target.elts)

    return False


def _import_matches_element(node, element_name):
    if isinstance(node, ast.Import):
        return any(_alias_matches_element(alias, element_name) for alias in node.names)

    if isinstance(node, ast.ImportFrom):
        return any(_alias_matches_element(alias, element_name) for alias in node.names)

    return False


def _alias_matches_element(alias, element_name):
    alias_names = {alias.name, alias.name.split(".")[-1]}
    if alias.asname:
        alias_names.add(alias.asname)

    return element_name in alias_names


def _located_from_node(file_content, node):
    start_line = getattr(node, "lineno", None)
    end_line = getattr(node, "end_lineno", None) or start_line
    snippet = extract_snippet_by_lines(file_content, start_line, end_line)

    if not snippet["snippet"]:
        return None

    return {
        "start_line": snippet["start_line"],
        "end_line": snippet["end_line"],
        "snippet": snippet["snippet"],
        "source": "ast",
    }


def _fallback_from_element_lines(file_content, element):
    snippet = extract_snippet_by_lines(
        file_content,
        element.get("start_line"),
        element.get("end_line"),
    )

    if not snippet["snippet"]:
        return {
            "start_line": None,
            "end_line": None,
            "snippet": "",
            "source": "unavailable",
        }

    return {
        "start_line": snippet["start_line"],
        "end_line": snippet["end_line"],
        "snippet": snippet["snippet"],
        "source": "llm_lines",
    }
