"""The finding registry and the data model.

Every finding code lives in this one registry; ``ctxfloor explain CODE`` prints
its definition. This mirrors the gguf-sentinel approach: codes are the
contract, the renderer never invents one.
"""

from dataclasses import dataclass, field
from typing import Dict, List, Optional, Tuple

SEVERITIES = ("error", "warn", "info")

# code -> (severity, one-line definition, provenance)
REGISTRY = {
    "F_MISSING_LINK": (
        "error",
        "A memory/instructions file links to a target that does not exist on disk.",
        "Claude Code follows MEMORY.md markdown links transitively; a dead link "
        "means bytes the author believes are loaded are not, and vice versa.",
    ),
    "F_LINK_DEPTH": (
        "warn",
        "A transitive markdown-link chain exceeds the depth budget (default 3).",
        "Every hop is re-billed on every turn; deep chains are the classic "
        "silent-floor growth vector reported in heavily customized setups.",
    ),
    "F_DUPLICATE_BYTES": (
        "warn",
        "Two measured items share the identical sha256 digest.",
        "Same bytes loaded twice is billed twice. Usually a skill copied "
        "between profile dirs or a memory file linked from two roots.",
    ),
    "F_OVERSIZED_ITEM": (
        "warn",
        "A single item exceeds --max-item-tokens (default 2000).",
        "An item this big dominates the floor and usually belongs behind a "
        "router or a on-demand skill, not loaded every turn.",
    ),
    "F_MISSING_DESCRIPTION": (
        "error",
        "A SKILL.md carries no description frontmatter field.",
        "The Agent Skills spec requires description; without it the agent "
        "cannot route to the skill, and its name still costs context.",
    ),
    "F_DESCRIPTION_TOO_LONG": (
        "warn",
        "A skill description exceeds the spec limit of 1024 characters.",
        "Agent Skills spec: description must be 1-1024 chars; every character "
        "past the limit is re-billed on every turn and may be truncated.",
    ),
    "F_VAGUE_DESCRIPTION": (
        "info",
        "A skill description starts with filler or has no ASCII words beyond filler.",
        "The listing is the router; a vague description makes the skill pay "
        "token cost while never being selected.",
    ),
    "F_NAME_DIR_MISMATCH": (
        "error",
        "A skill's name frontmatter does not match its parent directory.",
        "Agent Skills spec requires the match; clients key on the directory, "
        "so a mismatch silently changes which copy wins.",
    ),
    "F_DUPLICATE_NAME": (
        "error",
        "Two measured skills claim the same name.",
        "Name collisions make load order decide behavior; the loser still "
        "costs its listing bytes.",
    ),
    "F_HIDDEN_UNICODE": (
        "warn",
        "Zero-width or bidi control characters in a frontmatter description.",
        "Heuristic quality check (not a sandbox): invisible characters break "
        "routing string matches and tokenize unpredictably across families.",
    ),
    "F_BUDGET_EXCEEDED": (
        "error",
        "The total context floor exceeds the configured --budget-tokens.",
        "The gate finding: your CI fails when the floor grows past the budget "
        "you committed to.",
    ),
    "F_GROWTH_VS_BASELINE": (
        "warn",
        "An item grew more than --max-growth-pct since the stored baseline.",
        "Floors rot one innocent commit at a time. The baseline diff names "
        "the exact file that grew.",
    ),
}


@dataclass
class Finding:
    code: str
    item: str            # display path (posix, ~-relative when possible)
    message: str
    detail: Dict = field(default_factory=dict)

    @property
    def severity(self):
        return REGISTRY[self.code][0]

    @classmethod
    def new(cls, code, item, message=None, **detail):
        if code not in REGISTRY:
            raise KeyError(f"unknown finding code {code!r}; add it to REGISTRY")
        return cls(code=code, item=item, message=message or REGISTRY[code][1], detail=detail)


@dataclass
class FloorItem:
    """One measured unit of the floor: a file, or a derived listing string."""

    role: str             # system | memory | skill-listing | tool-schema | instructions
    path: str             # display path
    bytes_: int
    sha256: str
    tokens: Dict[str, int]        # tokenizer-family -> token count
    depth: int = 0                # transitive link depth (0 = root)
    linked_from: Optional[str] = None
    origin: str = ""              # adapter name, e.g. "claude-code"

    @property
    def tokens_primary(self):
        return self.tokens.get("gpt", sum(self.tokens.values()) // max(1, len(self.tokens)))


@dataclass
class FloorReport:
    agent: str
    home: str
    items: List[FloorItem] = field(default_factory=list)
    findings: List[Finding] = field(default_factory=list)
    tokenizer_set: str = "estimated"
    notes: List[str] = field(default_factory=list)

    def total(self, family=None):
        if family:
            return sum(i.tokens.get(family, 0) for i in self.items)
        return sum(i.tokens_primary for i in self.items)

    def by_role(self, family=None):
        out = {}
        for i in self.items:
            out[i.role] = out.get(i.role, 0) + (
                i.tokens.get(family, 0) if family else i.tokens_primary)
        return out
