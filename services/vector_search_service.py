import math

from data.code_chunk_repository import (
    list_project_code_chunks,
    replace_project_code_chunks,
)
from data.database import DEFAULT_DB_PATH
from services.embedding_service import embed_text, embed_texts
from utils.code_chunker import chunk_code_file
from utils.file_reader import read_code_file
from utils.file_scanner import scan_supported_files


def cosine_similarity(vector_a, vector_b):
    if not vector_a or not vector_b:
        raise ValueError("Vectors must not be empty.")

    if len(vector_a) != len(vector_b):
        raise ValueError("Vectors must have the same length.")

    magnitude_a = math.sqrt(sum(value * value for value in vector_a))
    magnitude_b = math.sqrt(sum(value * value for value in vector_b))

    if magnitude_a == 0.0 or magnitude_b == 0.0:
        return 0.0

    dot_product = sum(value_a * value_b for value_a, value_b in zip(vector_a, vector_b))
    return dot_product / (magnitude_a * magnitude_b)


def build_project_vector_index(
    project_id,
    codebase_path,
    db_path=DEFAULT_DB_PATH,
    embedder=None,
):
    files = scan_supported_files(codebase_path)
    chunks = []

    for file_path in files:
        content = read_code_file(codebase_path, file_path)
        chunks.extend(chunk_code_file(file_path, content))

    if chunks:
        embedding_inputs = [chunk["content"] for chunk in chunks]
        embeddings = _embed_texts(embedding_inputs, embedder=embedder)
    else:
        embeddings = []

    chunks_with_embeddings = [
        {
            **chunk,
            "embedding": embedding,
        }
        for chunk, embedding in zip(chunks, embeddings)
    ]

    replace_project_code_chunks(
        project_id,
        chunks_with_embeddings,
        db_path=db_path,
    )

    return {
        "files_indexed": len(files),
        "chunks_indexed": len(chunks_with_embeddings),
    }


def search_project_vectors(
    project_id,
    query,
    top_k=5,
    min_score=0.25,
    db_path=DEFAULT_DB_PATH,
    embedder=None,
):
    cleaned_query = _validate_query(query)
    cleaned_top_k = _validate_top_k(top_k)
    cleaned_min_score = _validate_min_score(min_score)

    stored_chunks = list_project_code_chunks(project_id, db_path=db_path)
    if not stored_chunks:
        return []

    query_embedding = _embed_text(cleaned_query, embedder=embedder)
    scored_results = []

    for chunk in stored_chunks:
        score = cosine_similarity(query_embedding, chunk["embedding"])
        scored_results.append(
            {
                "file_path": chunk["file_path"],
                "start_line": chunk["start_line"],
                "end_line": chunk["end_line"],
                "content": chunk["content"],
                "score": score,
            }
        )

    relevant_results = [
        result
        for result in sorted(scored_results, key=lambda result: result["score"], reverse=True)
        if result["score"] >= cleaned_min_score
    ]

    return relevant_results[:cleaned_top_k]


def _embed_texts(texts, embedder=None):
    if embedder is None:
        return embed_texts(texts)

    if hasattr(embedder, "embed_texts"):
        return embedder.embed_texts(texts)

    return embedder(texts)


def _embed_text(text, embedder=None):
    if embedder is None:
        return embed_text(text)

    if hasattr(embedder, "embed_text"):
        return embedder.embed_text(text)

    return embedder(text)


def _validate_query(query):
    if not isinstance(query, str) or not query.strip():
        raise ValueError("Query must not be empty.")

    return query.strip()


def _validate_top_k(top_k):
    if not isinstance(top_k, int) or isinstance(top_k, bool) or top_k <= 0:
        raise ValueError("top_k must be a positive integer.")

    return top_k


def _validate_min_score(min_score):
    if isinstance(min_score, bool) or not isinstance(min_score, (int, float)):
        raise ValueError("min_score must be a number.")

    return float(min_score)
