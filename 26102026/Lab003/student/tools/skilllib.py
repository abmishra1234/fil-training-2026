"""Small helpers shared by the lab tools: read a SKILL.md into (frontmatter, body)."""
import re
from pathlib import Path

try:
    import yaml
except ImportError:  # pragma: no cover
    raise SystemExit("pip install pyyaml")


def read_skill(skill_dir):
    path = Path(skill_dir) / "SKILL.md"
    if not path.exists():
        raise SystemExit(f"No SKILL.md found in {skill_dir}")
    text = path.read_text(encoding="utf-8")
    m = re.match(r"^---\s*\n(.*?)\n---\s*\n?(.*)$", text, re.S)
    if not m:
        return {}, text, text
    try:
        front = yaml.safe_load(m.group(1)) or {}
    except yaml.YAMLError as e:
        raise SystemExit(f"Frontmatter is not valid YAML: {e}")
    return front, m.group(2), text


def estimate_tokens(text):
    try:
        import tiktoken
        return len(tiktoken.get_encoding("cl100k_base").encode(text))
    except Exception:
        return int(len(text.split()) * 1.35)  # rough rule of thumb for English
