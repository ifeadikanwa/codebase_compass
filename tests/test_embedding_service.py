import pytest

from services import embedding_service


class FakeEmbeddingResponse:
    def __init__(self, data):
        self.data = data


class FakeEmbeddingItem:
    def __init__(self, embedding):
        self.embedding = embedding


class FakeEmbeddings:
    def __init__(self, response):
        self.response = response
        self.calls = []

    def create(self, **kwargs):
        self.calls.append(kwargs)
        return self.response


class FakeClient:
    def __init__(self, response):
        self.embeddings = FakeEmbeddings(response)


@pytest.fixture(autouse=True)
def prevent_real_dotenv_loading(monkeypatch):
    monkeypatch.setattr(embedding_service, "load_dotenv", lambda *args, **kwargs: None)


def test_get_embedding_model_uses_explicit_model_first(monkeypatch):
    monkeypatch.setenv("OPENAI_EMBEDDING_MODEL", "env-embedding-model")

    model = embedding_service.get_embedding_model(model="explicit-embedding-model")

    assert model == "explicit-embedding-model"


def test_get_embedding_model_uses_environment_variable_second(monkeypatch):
    monkeypatch.setenv("OPENAI_EMBEDDING_MODEL", "env-embedding-model")

    model = embedding_service.get_embedding_model()

    assert model == "env-embedding-model"


def test_get_embedding_model_falls_back_to_default(monkeypatch):
    monkeypatch.delenv("OPENAI_EMBEDDING_MODEL", raising=False)

    model = embedding_service.get_embedding_model()

    assert model == "text-embedding-3-small"


def test_embed_text_returns_one_vector_and_sends_model_and_input():
    client = FakeClient(
        FakeEmbeddingResponse(
            data=[
                FakeEmbeddingItem([0.1, 0.2, 0.3]),
            ]
        )
    )

    embedding = embedding_service.embed_text(
        "  explain this  ",
        client=client,
        model="test-embedding-model",
    )

    assert embedding == [0.1, 0.2, 0.3]
    assert client.embeddings.calls == [
        {
            "model": "test-embedding-model",
            "input": ["explain this"],
        }
    ]


def test_embed_texts_returns_vectors_in_order_and_sends_one_batch_call():
    client = FakeClient(
        FakeEmbeddingResponse(
            data=[
                {"embedding": [0.1, 0.2]},
                {"embedding": [0.3, 0.4]},
            ]
        )
    )

    embeddings = embedding_service.embed_texts(
        ["  first text  ", "second text"],
        client=client,
        model="batch-model",
    )

    assert embeddings == [[0.1, 0.2], [0.3, 0.4]]
    assert client.embeddings.calls == [
        {
            "model": "batch-model",
            "input": ["first text", "second text"],
        }
    ]


@pytest.mark.parametrize("text", ["", "   ", None, 123])
def test_embed_text_rejects_empty_or_invalid_text(text):
    client = FakeClient(FakeEmbeddingResponse(data=[]))

    with pytest.raises(ValueError):
        embedding_service.embed_text(text, client=client)

    assert client.embeddings.calls == []


@pytest.mark.parametrize(
    "texts",
    [
        "not a list",
        (),
        [],
        ["valid", ""],
        ["valid", "   "],
        ["valid", None],
    ],
)
def test_embed_texts_rejects_empty_or_invalid_input(texts):
    client = FakeClient(FakeEmbeddingResponse(data=[]))

    with pytest.raises(ValueError):
        embedding_service.embed_texts(texts, client=client)

    assert client.embeddings.calls == []


def test_missing_api_key_raises_runtime_error_before_openai_client_creation(monkeypatch):
    monkeypatch.delenv("OPENAI_API_KEY", raising=False)

    def fail_if_openai_client_is_created(*args, **kwargs):
        raise AssertionError("OpenAI client should not be created without an API key.")

    monkeypatch.setattr(embedding_service, "OpenAI", fail_if_openai_client_is_created)

    with pytest.raises(RuntimeError, match="OPENAI_API_KEY"):
        embedding_service.embed_text("hello")


@pytest.mark.parametrize(
    "data",
    [
        None,
        [],
        [{}],
        [{"embedding": "not a vector"}],
        [{"embedding": [True]}],
        [{"embedding": [object()]}],
    ],
)
def test_malformed_embedding_responses_raise_runtime_error(data):
    client = FakeClient(FakeEmbeddingResponse(data=data))

    with pytest.raises(RuntimeError, match="malformed embedding response"):
        embedding_service.embed_text("hello", client=client)
