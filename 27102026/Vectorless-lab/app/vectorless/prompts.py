"""
app/vectorless/prompts.py - PROVIDED. The two prompts of vectorless RAG.

Like the agent prompts, each starts with "TASK: <NAME>" so you can spot it in
logs and the tests' fake LLM can tell them apart. Both reply with JSON.

  TREE_SUMMARY   indexing time, once per document: write the "signposts"
  TREE_NAVIGATE  query time, once per tree level: pick which nodes to open

Stretch: tune these on your own documents. Summaries decide what the
navigator can see, so they decide retrieval quality.
"""

# Bump this when you change TREE_SUMMARY: cached summaries made with an older
# prompt are then ignored and rebuilt.
SUMMARY_PROMPT_VERSION = "v1"

TREE_SUMMARY = """TASK: TREE_SUMMARY
You write the signposts of a table of contents. A search agent will read ONLY
these summaries (never the full text) to decide which section to open, so each
summary must say which concrete facts the section contains.

For the document below write:
- "document": 1-2 sentences: what the document covers and who it applies to.
- "sections": for EVERY section id shown in square brackets, one sentence of at
  most 30 words naming the concrete facts inside: codes, amounts, limits, time
  periods, roles, systems. Name things; do not answer questions; no opinions.

Reply ONLY with JSON:
{"document": "...", "sections": {"<id>": "...", "<id>": "..."}}"""

TREE_NAVIGATE = """TASK: TREE_NAVIGATE
You find information in the NovaPay employee handbook by navigating its table of
contents, like an expert reading a book. You see node ids, titles and short
summaries, never the full text.

Pick the nodes most likely to contain the facts needed to answer the question.
- Pick at most {max_pick} ids, best first. Pick fewer when one node clearly covers it.
- If the question has several parts or topics, pick a node for EACH part.
- If the question names an exact identifier (an error code like PAY-E4035, a
  policy id, a system name), pick the node whose title or summary contains it.
- Translate casual words into handbook words (WFH -> hybrid working,
  food money -> per diem, holidays -> leave).
- Only use ids from the list.

Reply ONLY with JSON:
{{"thinking": "<max 25 words: where the answer should be and why>", "node_ids": ["..."]}}"""
