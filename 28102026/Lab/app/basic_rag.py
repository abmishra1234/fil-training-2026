"""
app/basic_rag.py - PROVIDED. The baseline: Basic RAG with LangChain (LCEL).

    question ──► retriever (FAISS top-k) ──► naive prompt ──► gpt-6-luna ──► answer
                     │
                     └── the same k chunks are returned as "sources"

This is what most first RAG demos look like. It works for well-worded
questions and fails in two typical ways that you will fix in this lab:

  1. Vocabulary mismatch  "Can I WFH on Fridays?"  vs the doc's "hybrid working",
     "anchor days"  -> the right chunk is not in the top-k.          (fix: MQR)
  2. Exact identifiers    "PAY-E4035"  -> embeddings are fuzzy, the chunk for a
     sibling code (PAY-E4033) can rank higher.                        (fix: BM25 + RRF)

Do not change this file: it is the "before" in your before/after comparison.
"""
from __future__ import annotations

from llm_client import traced  # OpenTelemetry span -> LangSmith run

from langchain_core.documents import Document
from langchain_core.output_parsers import StrOutputParser
from langchain_core.prompt_values import PromptValue
from langchain_core.prompts import ChatPromptTemplate
from langchain_core.runnables import RunnableLambda, RunnableParallel, RunnablePassthrough

from .llm import chat_complete
from .vector_store import InMemoryVectorStore

_ROLE = {"system": "system", "human": "user", "ai": "assistant"}


def _call_llm(prompt: PromptValue) -> str:
    """LangChain prompt -> OpenAI-style messages -> our gateway chat call."""
    messages = [{"role": _ROLE.get(m.type, "user"), "content": m.content} for m in prompt.to_messages()]
    return chat_complete(messages)


# A LangChain Runnable that calls azure/gpt-6-luna through llm_client.get_client().
gateway_llm = RunnableLambda(_call_llm, name="gpt-6-luna")

# Deliberately naive: no numbering, no citations, no "say I don't know" rule.
BASIC_PROMPT = ChatPromptTemplate.from_messages(
    [
        ("system", "You are a helpful assistant. Answer the question using the context."),
        ("human", "Context:\n{context}\n\nQuestion: {question}"),
    ]
)


def with_meta(doc: Document, **extra) -> Document:
    """Copy a Document and add metadata (never mutate the chunks stored in the index)."""
    return Document(page_content=doc.page_content, metadata={**doc.metadata, **extra})


@traced("basic_retrieve", kind="retriever")
def basic_retrieve(store: InMemoryVectorStore, question: str, k: int) -> list[Document]:
    """FAISS top-k for the question, best first, with metadata['score'] = cosine."""
    return [with_meta(doc, score=float(score)) for doc, score in store.search(question, k)]


def format_docs(docs: list[Document]) -> str:
    return "\n\n".join(d.page_content for d in docs)


def build_basic_chain(store: InMemoryVectorStore, k: int):
    """
    The classic LCEL "RAG with sources" chain.
    Input: the question (str).  Output: {"question", "context": [Document], "answer": str}
    """
    retriever = RunnableLambda(lambda q: basic_retrieve(store, q, k), name="faiss_retriever")
    answer_chain = (
        RunnableLambda(lambda x: {"context": format_docs(x["context"]), "question": x["question"]})
        | BASIC_PROMPT
        | gateway_llm
        | StrOutputParser()
    )
    return RunnableParallel(context=retriever, question=RunnablePassthrough()).assign(answer=answer_chain)
