"""contextfloor — measure what your agent loads before you type a word.

The *context floor* is everything injected into an LLM turn before the user's
message: system instructions (and the files they pull in via markdown links),
memory files, skill frontmatter listings, and tool schemas. It is billed on
every single turn and is invisible until the bill arrives.

Public API:

    from contextfloor import profile_agent, render_text, TokenizerSet

Deterministic by construction: byte counts, sha256 digests, and estimated
token counts are reproducible across machines. Only ``--json`` field order
depends on insertion order, which is canonical (sorted).
"""

__version__ = "0.1.0"

from .model import Finding, FloorItem, FloorReport, SEVERITIES
from .report import render_json, render_text
from .tokenizers import TokenizerSet

__all__ = [
    "__version__",
    "Finding",
    "FloorItem",
    "FloorReport",
    "SEVERITIES",
    "TokenizerSet",
    "render_json",
    "render_text",
    "profile_agent",
]


def profile_agent(agent, home=None, project=None, tokenizer=None):
    """Profile one agent installation. Returns a FloorReport."""
    from .adapters import get_adapter

    adapter = get_adapter(agent)
    return adapter.collect(home=home, project=project, tokenizer=tokenizer)
