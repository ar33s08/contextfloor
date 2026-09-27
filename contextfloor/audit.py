"""Audit rules. Every finding code here must exist in model.REGISTRY.

Rules are pure functions over already-measured items — no I/O — so they are
trivially fixture-testable and deterministic.
"""

import re

_HIDDEN_CLASS = '[\u200b\u200c\u200d\u200e\u200f\u2060\u2061\u2062\u2063\u2064\ufeff]'
from collections import defaultdict

from .model import Finding

_HIDDEN_RE = re.compile(_HIDDEN_CLASS)
_VAGUE_PREFIXES = ("a skill that", "this skill", "skill for", "helps with", "can help",
                   "various", "misc", "tool", "assistant")
_SPEC_DESC_MAX = 1024


def run_audit(items, budget=None, max_item_tokens=2000, baseline=None,
               max_growth_pct=25, dead_links=None):
    """Return [Finding] over a measured FloorReport's items."""
    findings = []

    # 1. dead links from link expansion (passed in from adapters)
    for src, target in (dead_links or []):
        findings.append(Finding.new("F_MISSING_LINK", src, target=target))

    # 2. link depth
    for it in items:
        if it.depth >= 3:
            findings.append(Finding.new("F_LINK_DEPTH", it.path, depth=it.depth,
                                        linked_from=it.linked_from))

    # 3. duplicate content by digest
    by_digest = defaultdict(list)
    for it in items:
        by_digest[it.sha256].append(it)
    for digest, group in by_digest.items():
        if len(group) > 1:
            paths = [g.path for g in group]
            findings.append(Finding.new("F_DUPLICATE_BYTES", paths[0],
                                         also=paths[1:], digest=digest[:12]))

    # 4. oversized single items
    for it in items:
        if it.tokens_primary > max_item_tokens:
            findings.append(Finding.new("F_OVERSIZED_ITEM", it.path,
                                        tokens=it.tokens_primary, role=it.role))

    # 5-9. skill frontmatter checks (adapters attach frontmatter meta on items)
    names = defaultdict(list)
    for it in items:
        meta = getattr(it, "frontmatter", None)
        if not meta:
            continue
        name = meta.get("name")
        desc = meta.get("description")
        if name:
            names[name].append(it.path)
            if meta.get("dir") and name != meta["dir"]:
                findings.append(Finding.new("F_NAME_DIR_MISMATCH", it.path,
                                             name=name, dir=meta["dir"]))
        if not desc or not desc.strip():
            findings.append(Finding.new("F_MISSING_DESCRIPTION", it.path))
        else:
            if len(desc) > _SPEC_DESC_MAX:
                findings.append(Finding.new("F_DESCRIPTION_TOO_LONG", it.path,
                                             chars=len(desc)))
            low = desc.strip().lower()
            if any(low.startswith(p) for p in _VAGUE_PREFIXES):
                findings.append(Finding.new("F_VAGUE_DESCRIPTION", it.path,
                                            description=low[:60]))
            if _HIDDEN_RE.search(desc):
                findings.append(Finding.new("F_HIDDEN_UNICODE", it.path))
    for name, paths in names.items():
        if len(paths) > 1:
            findings.append(Finding.new("F_DUPLICATE_NAME", paths[0],
                                        name=name, also=paths[1:]))

    # 10. budget gate
    if budget is not None:
        total = sum(i.tokens_primary for i in items)
        if total > budget:
            findings.append(Finding.new("F_BUDGET_EXCEEDED", "(total)",
                                        total=total, budget=budget))

    # 11. baseline growth (baseline: {path: tokens})
    if baseline:
        for it in items:
            prev = baseline.get(it.path)
            if prev and prev > 200:                     # ignore noise on tiny items
                growth = (it.tokens_primary - prev) / prev * 100
                if growth >= max_growth_pct:
                    findings.append(Finding.new("F_GROWTH_VS_BASELINE", it.path,
                                                before=prev, after=it.tokens_primary,
                                                pct=round(growth, 1)))
    return findings
