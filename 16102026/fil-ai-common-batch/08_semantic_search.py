"""
    08_semantic_search.py - a tiny semantic search with embeddings (deck: "Try it").
    Expected: the two food reviews rank above the flight one, even though the
    query shares no keywords like "food" or "delicious".
"""
import os
import sys

from llm_client import get_client, settings

import numpy as np

client = get_client()

docs = [
    "The food was delicious and the waiter was friendly.",
    "Our flight was delayed by three hours.",
    "The pasta was cold but the dessert was great.",
]

query = ["How was the meal?",
         "Why you are late?",
         "What is the best place to visit?"
]

# Now its time to embed the documents and the query, and then compute the similarity between them.
# index once
doc_embeddings = client.embeddings.create(
    model=settings.embed_model,
    input=docs,
)

# store the docs_embedding into vector store
doc_vector = np.array([d.embedding for d in doc_embeddings.data])

query_embeddings = client.embeddings.create(
    model=settings.embed_model,
    input=query,
)

query_vector = np.array([d.embedding for d in query_embeddings.data])

# One row per query and one column per document.
scores = query_vector @ doc_vector.T

for query_text, query_scores in zip(query, scores):
    print(f"Query: {query_text!r}\n")

    for i in np.argsort(-query_scores):
        print(f"{query_scores[i]:.3f} {docs[i]}")
    print()





