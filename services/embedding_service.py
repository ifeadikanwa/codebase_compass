import os

from dotenv import load_dotenv
from openai import APIError, OpenAI


DEFAULT_OPENAI_EMBEDDING_MODEL = "text-embedding-3-small"


def get_embedding_model(model=None):
    load_dotenv()
    return model or os.getenv("OPENAI_EMBEDDING_MODEL") or DEFAULT_OPENAI_EMBEDDING_MODEL


def get_openai_embedding_client():
    load_dotenv()

    api_key = os.getenv("OPENAI_API_KEY")
    if not api_key:
        raise RuntimeError("OPENAI_API_KEY environment variable must be configured.")

    return OpenAI(api_key=api_key)


def embed_text(text, client=None, model=None):
    cleaned_text = _validate_text(text, "Text")
    embeddings = embed_texts([cleaned_text], client=client, model=model)
    return embeddings[0]


def embed_texts(texts, client=None, model=None):
    cleaned_texts = _validate_texts(texts)
    selected_model = get_embedding_model(model)

    if client is None:
        client = get_openai_embedding_client()

    try:
        response = client.embeddings.create(
            model=selected_model,
            input=cleaned_texts,
        )
    except APIError as error:
        raise RuntimeError("Could not generate embeddings from OpenAI.") from error

    return _extract_embedding_vectors(response, expected_count=len(cleaned_texts))


def _validate_text(text, field_name):
    if not isinstance(text, str) or not text.strip():
        raise ValueError(f"{field_name} must not be empty.")

    return text.strip()


def _validate_texts(texts):
    if not isinstance(texts, list):
        raise ValueError("Texts must be a list.")

    if not texts:
        raise ValueError("Texts must not be empty.")

    return [_validate_text(text, "Text") for text in texts]


def _extract_embedding_vectors(response, expected_count):
    data = getattr(response, "data", None)

    if not isinstance(data, list) or len(data) != expected_count:
        raise RuntimeError("OpenAI returned a malformed embedding response.")

    vectors = []
    for item in data:
        embedding = _get_embedding_from_response_item(item)
        if not _is_float_list(embedding):
            raise RuntimeError("OpenAI returned a malformed embedding response.")

        vectors.append([float(value) for value in embedding])

    return vectors


def _get_embedding_from_response_item(item):
    if isinstance(item, dict):
        return item.get("embedding")

    return getattr(item, "embedding", None)


def _is_float_list(value):
    return isinstance(value, list) and all(
        isinstance(item, (int, float)) and not isinstance(item, bool)
        for item in value
    )
