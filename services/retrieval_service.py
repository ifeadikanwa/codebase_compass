import re

from utils.code_chunker import chunk_code_file
from utils.file_reader import read_code_file
from utils.file_scanner import scan_supported_files


STOP_WORDS = {
    "a",
    "an",
    "and",
    "are",
    "how",
    "in",
    "is",
    "of",
    "the",
    "to",
    "what",
    "where",
}


def tokenize_text(text: str) -> list[str]:
    normalized_text = re.sub(r"[^a-z0-9]+", " ", text.lower())
    return normalized_text.split()


def search_chunks(query: str, chunks: list[dict], top_k: int = 5) -> list[dict]:
    if top_k <= 0:
        raise ValueError("top_k must be greater than zero.")

    query_terms = {term for term in tokenize_text(query) if term not in STOP_WORDS}

    if not query_terms or not chunks:
        return []

    scored_results = []

    for index, chunk in enumerate(chunks):
        chunk_terms = set(tokenize_text(chunk["content"]))
        matching_terms = sorted(query_terms & chunk_terms)
        score = len(matching_terms)

        if score == 0:
            continue

        scored_results.append(
            (
                score,
                index,
                {
                    "file_path": chunk["file_path"],
                    "start_line": chunk["start_line"],
                    "end_line": chunk["end_line"],
                    "content": chunk["content"],
                    "score": score,
                    "matching_terms": matching_terms,
                },
            )
        )

    scored_results.sort(key=lambda result: (-result[0], result[1]))

    return [result for _, _, result in scored_results[:top_k]]


def search_codebase(codebase_path, query: str, top_k: int = 5) -> list[dict]:
    if not query.strip():
        return []

    chunks = []

    for file_path in scan_supported_files(codebase_path):
        content = read_code_file(codebase_path, file_path)
        chunks.extend(chunk_code_file(file_path, content))

    return search_chunks(query, chunks, top_k=top_k)
