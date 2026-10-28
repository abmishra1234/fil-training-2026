"""
app/vectorless/tree.py - the TREE INDEX.                             TODO V1, V2

Vector RAG cuts every file into 500-character chunks and turns each chunk into
1,536 numbers. The structure of the handbook (which section a sentence belongs
to) survives only as a "title > section" prefix.

Vectorless RAG keeps the structure as the index itself: a table of contents.

    root  "NovaPay employee handbook"
     ├─ [01] NovaPay Leave Policy (HR-POL-01)               <- one node per FILE  ("#" heading)
     │    ├─ [01.0] Overview                                <- text before the first "##"
     │    ├─ [01.1] Earned leave                            <- one node per "##" SECTION
     │    └─ ...
     ├─ [04] Payments Platform Error Codes (ENG-RUN-PAY)
     │    ├─ [04.4] PAY-E4035 - Signature mismatch on bank file
     │    └─ ...
     └─ [11] NovaPay Engineering Glossary                   <- no "##": the document is a leaf

Every node gets a short SUMMARY (the "signpost"). At query time the LLM only
reads ids + titles + summaries and decides where to go (see navigator.py).
Full text is read only for the leaves it finally picks.

Cost of the index: building the tree is free (it is just parsing). Summaries
cost ONE LLM call per document (12 for this handbook), paid once and cached on
disk by content hash, so a restart or a re-index of unchanged files is free.
No embedding model is used anywhere.
"""
from __future__ import annotations

import hashlib
import json
import re
from dataclasses import dataclass, field
from pathlib import Path

from langchain_core.documents import Document # type: ignore

from ..agent.parsing import parse_json
from ..llm import RagError, chat_complete
from . import prompts

ALLOWED_SUFFIXES = {".md", ".txt"}
ROOT_TITLE = "NovaPay employee handbook"


@dataclass
class TreeNode:
    node_id: str                 # "root", "04", "04.4"
    title: str                   # heading text (without the leading "#")
    kind: str                    # "root" | "document" | "section"
    source: str = ""             # file name, e.g. "04_payment_error_codes.md"
    text: str = ""               # the node's OWN text (sections, and documents without sections)
    summary: str = ""            # the signpost the navigator reads
    summary_source: str = ""     # "llm" | "cache" | "extractive" | ""
    doc_title: str = ""          # title of the document this node belongs to
    children: list["TreeNode"] = field(default_factory=list)

    @property
    def is_leaf(self) -> bool:
        return not self.children

    def walk(self):
        """This node and every node below it, depth first (table-of-contents order)."""
        yield self
        for c in self.children:
            yield from c.walk()

    def leaves(self) -> list["TreeNode"]:
        return [n for n in self.walk() if n.is_leaf and n.kind != "root"]

    def full_text(self) -> str:
        """Text of the node and everything below it (a whole document, for example)."""
        if self.is_leaf:
            return self.text
        parts = [self.text] if self.text else []
        parts += [f"{c.title}\n{c.full_text()}" for c in self.children]
        return "\n\n".join(p for p in parts if p.strip())


@dataclass
class TreeIndex:
    root: TreeNode
    by_id: dict[str, TreeNode] = field(default_factory=dict)
    summaries: str = "pending"    # pending | llm | extractive | none
    summary_llm_calls: int = 0    # LLM calls spent on the LAST summarize_tree() run

    @classmethod
    def from_root(cls, root: TreeNode) -> "TreeIndex":
        return cls(root=root, by_id={n.node_id: n for n in root.walk()})

    @property
    def documents(self) -> list[TreeNode]:
        return list(self.root.children)

    def find(self, node_id: str) -> TreeNode | None:
        return self.by_id.get(node_id)


# ---------------------------------------------------------------------------
# TODO V1 - build_tree()
# ---------------------------------------------------------------------------
def build_tree(folder: Path) -> TreeIndex:
    """
    Turn every .md / .txt file in `folder` into a 3-level tree. NO LLM, NO embeddings.

    Files: sorted(folder.glob("*")), only real files with a suffix in
    ALLOWED_SUFFIXES (case-insensitive). The n-th file (1-based) gets node_id
    f"{n:02d}" -> "01", "02", ... (by position, not by the file name).

    Markdown (.md), read line by line:
      * "# Title"     -> the document title (first one only). No "# " line -> the
                         file stem (e.g. "11_glossary").
      * "## Heading"  -> starts a new SECTION node: node_id f"{doc_id}.{k}" where k
                         is the heading's position (1, 2, 3 ...) among ALL "## "
                         headings of the file, title = the heading text.
      * any other line (including "### ..." sub-headings) is text of the current
        section. Lines before the first "##" are the document's INTRO.
      * text = the lines joined with "\\n", then .strip()
      * if the intro is not empty and the document has sections, the intro
        becomes a section node f"{doc_id}.0" titled "Overview", placed FIRST.
      * if the document has NO "##" sections at all, the intro is the document
        node's own text and the document node is a leaf (children == []).
      * skip sections whose text is empty (their k is still used up, so
        "## A", an empty "## B", "## C" give ids .1 and .3).
    Plain text (.txt): one leaf document; title = file stem; text = whole file.

    Every node: source = file name; doc_title = the document title.
    Document nodes: kind="document". Section nodes: kind="section".
    Root: TreeNode("root", ROOT_TITLE, "root", children=[documents...]).

    Return TreeIndex.from_root(root)   (summaries are filled later, TODO V2).
    """
    # >>> SOLUTION lab3
    docs: list[TreeNode] = []
    files = [p for p in sorted(folder.glob("*")) if p.is_file() and p.suffix.lower() in ALLOWED_SUFFIXES]
    for n, path in enumerate(files, start=1):
        doc_id = f"{n:02d}"
        raw = path.read_text(encoding="utf-8", errors="replace")
        if path.suffix.lower() != ".md":
            docs.append(TreeNode(doc_id, path.stem, "document", path.name, raw.strip(), doc_title=path.stem))
            continue
        title: str | None = None
        intro: list[str] = []
        sections: list[tuple[str, list[str]]] = []
        for line in raw.splitlines():
            if line.startswith("# ") and title is None:
                title = line[2:].strip()
            elif line.startswith("## "):
                sections.append((line[3:].strip(), []))
            elif sections:
                sections[-1][1].append(line)
            else:
                intro.append(line)
        title = title or path.stem
        intro_text = "\n".join(intro).strip()
        doc = TreeNode(doc_id, title, "document", path.name, doc_title=title)
        children: list[TreeNode] = []
        if sections and intro_text:
            children.append(TreeNode(f"{doc_id}.0", "Overview", "section", path.name, intro_text, doc_title=title))
        for k, (heading, lines) in enumerate(sections, start=1):
            text = "\n".join(lines).strip()
            if text:
                children.append(TreeNode(f"{doc_id}.{k}", heading, "section", path.name, text, doc_title=title))
        if sections:
            doc.children = children
        else:
            doc.text = intro_text
        docs.append(doc)
    return TreeIndex.from_root(TreeNode("root", ROOT_TITLE, "root", children=docs))
    # <<< SOLUTION
    # >>> STARTER lab3
    # raise NotImplementedError("TODO V1: implement build_tree() in app/vectorless/tree.py")
    # <<< STARTER


# ---------------------------------------------------------------------------
# PROVIDED helpers
# ---------------------------------------------------------------------------
_SENT = re.compile(r"(?<=[.!?])\s+")


def extractive_summary(text: str, max_chars: int = 180) -> str:
    """The free fallback signpost: the first sentence(s) of the text, at most max_chars."""
    flat = " ".join((text or "").split())
    if len(flat) <= max_chars:
        return flat
    out = ""
    for sent in _SENT.split(flat):
        if out and len(out) + 1 + len(sent) > max_chars:
            break
        out = f"{out} {sent}".strip()
    return out if out and len(out) <= max_chars else flat[: max_chars - 1].rstrip() + "…"


def extractive_signpost(node: TreeNode) -> str:
    """
    Free signpost for any node. A document WITH sections is best described by its
    section titles (a mini table of contents); everything else by its first sentence(s).
    """
    if node.kind == "document" and node.children:
        return extractive_summary("Covers: " + "; ".join(c.title for c in node.children) + ".", 220)
    return extractive_summary(node.full_text())


def document_prompt(doc: TreeNode) -> str:
    """The user message for TREE_SUMMARY: the document with every section id in brackets."""
    lines = [f"Document [{doc.node_id}] {doc.title}"]
    if doc.is_leaf:
        lines.append(doc.text)
    for s in doc.children:
        lines.append(f"\n[{s.node_id}] {s.title}\n{s.text}")
    return "\n".join(lines)


# ---------------------------------------------------------------------------
# TODO V2 - summarize_document()
# ---------------------------------------------------------------------------
def summarize_document(doc: TreeNode) -> int:
    """
    Write the signposts of ONE document with ONE LLM call. Returns the number
    of LLM calls made (always 1).

      1. reply = chat_complete([
             {"role": "system", "content": prompts.TREE_SUMMARY},
             {"role": "user",   "content": document_prompt(doc)},
         ])
         If chat_complete raises RagError, use reply = "" (never crash indexing).
      2. data = parse_json(reply)   (from app/agent/parsing.py: handles ```json fences
         and chatter around the JSON; returns None when there is no JSON object)
      3. The document node:
           data["document"] is a non-blank string -> doc.summary = it.strip(),
                                                     doc.summary_source = "llm"
           otherwise -> doc.summary = extractive_signpost(doc),
                        doc.summary_source = "extractive"
      4. Every child section s (same rule, looked up in data["sections"][s.node_id]):
           a non-blank string -> "llm";  missing / not a string / blank / data is None
           -> extractive_signpost(s), "extractive".
         data["sections"] may be missing or not a dict: treat it as {}.
    """
    # >>> SOLUTION lab3
    try:
        reply = chat_complete([
            {"role": "system", "content": prompts.TREE_SUMMARY},
            {"role": "user", "content": document_prompt(doc)},
        ])
    except RagError:
        reply = ""
    data = parse_json(reply) or {}
    sections = data.get("sections") if isinstance(data.get("sections"), dict) else {}

    def put(node: TreeNode, value) -> None:
        if isinstance(value, str) and value.strip():
            node.summary, node.summary_source = value.strip(), "llm"
        else:
            node.summary, node.summary_source = extractive_signpost(node), "extractive"

    put(doc, data.get("document"))
    for s in doc.children:
        put(s, sections.get(s.node_id))
    return 1
    # <<< SOLUTION
    # >>> STARTER lab3
    # raise NotImplementedError("TODO V2: implement summarize_document() in app/vectorless/tree.py")
    # <<< STARTER


# ---------------------------------------------------------------------------
# PROVIDED: summaries for the whole tree, with a disk cache
# ---------------------------------------------------------------------------
def _doc_key(doc: TreeNode) -> str:
    """Content hash (title, section titles, texts, prompt version). Ids are left out on purpose:
    adding a file shifts the ids of the files after it, but their summaries are still valid."""
    parts = [prompts.SUMMARY_PROMPT_VERSION, doc.title, doc.text] + [f"{c.title}\n{c.text}" for c in doc.children]
    return hashlib.sha1("\n\x1f".join(parts).encode("utf-8")).hexdigest()


def _load_cache(path: Path | None) -> dict:
    if path is None or not path.exists():
        return {}
    try:
        data = json.loads(path.read_text(encoding="utf-8"))
        return data if isinstance(data, dict) else {}
    except (OSError, json.JSONDecodeError):
        return {}


def _save_cache(path: Path | None, cache: dict) -> None:
    if path is None:
        return
    try:
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(json.dumps(cache, indent=1, ensure_ascii=False), encoding="utf-8")
    except OSError:
        pass  # a read-only folder must never break retrieval


def summarize_tree(tree: TreeIndex, mode: str = "llm", cache_path: Path | None = None) -> int:
    """
    Fill every node's summary. Returns the number of LLM calls made.

      mode="none"        titles only (summaries stay ""): the cheapest navigator input
      mode="extractive"  first sentence(s) of each node: free
      mode="llm"         summarize_document() per document, cached by content hash:
                         unchanged documents cost nothing the next time
    """
    calls = 0
    if mode == "none":
        for n in tree.root.walk():
            n.summary, n.summary_source = "", ""
    elif mode == "extractive":
        for n in tree.root.walk():
            if n.kind != "root":
                n.summary, n.summary_source = extractive_signpost(n), "extractive"
    else:
        mode = "llm"
        cache = _load_cache(cache_path)
        for doc in tree.documents:
            key = _doc_key(doc)
            hit = cache.get(key)
            sections = hit.get("sections") if isinstance(hit, dict) else None
            if isinstance(hit, dict) and isinstance(hit.get("document"), str) and isinstance(sections, list) \
                    and len(sections) == len(doc.children):
                doc.summary, doc.summary_source = hit["document"], "cache"
                for s, cached in zip(doc.children, sections):  # by position, not by id
                    if isinstance(cached, str) and cached:
                        s.summary, s.summary_source = cached, "cache"
                    else:
                        s.summary, s.summary_source = extractive_signpost(s), "extractive"
                continue
            calls += summarize_document(doc)
            if doc.summary_source == "llm":  # cache only real LLM summaries
                cache[key] = {
                    "title": doc.title,
                    "document": doc.summary,
                    "sections": [s.summary if s.summary_source == "llm" else "" for s in doc.children],
                }
        _save_cache(cache_path, cache)
    tree.root.summary = "Documents: " + "; ".join(d.title for d in tree.documents)
    tree.summaries, tree.summary_llm_calls = mode, calls
    return calls


# ---------------------------------------------------------------------------
# PROVIDED: tree nodes -> LangChain Documents (so Lab 1 generation + evaluation reuse them)
# ---------------------------------------------------------------------------
def node_document(node: TreeNode) -> Document:
    """
    A selected node as a Document. Same "<doc title> > <section>" first line as
    the Lab 1 chunks, so the grounded prompt and the evaluation treat both alike.
    chunk_id = "<file>::<node_id>", e.g. "04_payment_error_codes.md::04.4".
    """
    if node.kind == "section":
        heading, section, body = f"{node.doc_title} > {node.title}", node.title, node.text
    else:
        heading, section, body = node.title, "", node.full_text()
    return Document(
        page_content=f"{heading}\n{body}",
        metadata={
            "chunk_id": f"{node.source}::{node.node_id}",
            "source": node.source,
            "title": node.doc_title or node.title,
            "section": section,
            "node_id": node.node_id,
            "summary": node.summary,
        },
    )


def tree_to_dict(node: TreeNode) -> dict:
    """JSON for the UI's Tree index tab."""
    return {
        "node_id": node.node_id, "title": node.title, "kind": node.kind, "source": node.source,
        "summary": node.summary, "summary_source": node.summary_source,
        "chars": len(node.full_text()), "text": node.text if node.is_leaf else "",
        "children": [tree_to_dict(c) for c in node.children],
    }
