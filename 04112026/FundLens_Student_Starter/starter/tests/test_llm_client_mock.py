import os

os.environ["FUNDLENS_LLM_MODE"] = "mock"

from fundlens import llm_client  # noqa: E402


def test_mock_chat_is_deterministic():
    m = [{"role": "user", "content": "hello"}]
    assert llm_client.chat(m) == llm_client.chat(m)


def test_mock_embeddings_similarity():
    a, b, c = llm_client.embed(["ongoing charge of the fund", "fund ongoing charge", "dealing cut-off time"])
    def dot(x, y):
        return sum(i * j for i, j in zip(x, y, strict=True))

    assert dot(a, b) > dot(a, c)
