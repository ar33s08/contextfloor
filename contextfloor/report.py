"""Renderers: text (human), json (machine), md (shareable), sarif (CI upload).

The JSON schema is the stable public contract for CI and dashboards:
{agent, home, tokenizer_set, totals:{family:n}, by_role:{...}, items:[...],
 findings:[...], notes:[...]}
"""

import json as _json

from .model import REGISTRY

_ROLE_ORDER = ("system", "instructions", "memory", "skill-listing", "tool-schema")


def render_json(report, budget=None):
    totals = {}
    for fam in ("gpt", "claude", "gemini"):
        totals[fam] = report.total(fam)
    return {
        "schema": "ctxfloor/0.1",
        "agent": report.agent,
        "home": report.home,
        "tokenizer_set": report.tokenizer_set,
        "totals": totals,
        "budget": budget,
        "by_role": report.by_role(),
        "items": [{"role": i.role, "path": i.path, "bytes": i.bytes_,
                   "sha256": i.sha256, "tokens": i.tokens, "depth": i.depth,
                   "linked_from": i.linked_from, "origin": i.origin}
                  for i in sorted(report.items, key=lambda x: -x.tokens_primary)],
        "findings": [{"code": f.code, "severity": f.severity, "item": f.item,
                      "message": f.message, **({"detail": f.detail} if f.detail else {})}
                     for f in report.findings],
        "notes": report.notes,
    }


def render_text(report, width=74):
    lines = []
    bar = "═" * width
    lines.append(f"╔{bar}╣")
    lines.append(f"  ctxfloor — {report.agent}  |  {report.home}")
    lines.append(f"  tokenizers: {report.tokenizer_set}")
    lines.append(f"{bar[:width]}")
    totals = {fam: report.total(fam) for fam in ("gpt", "claude", "gemini")}
    lines.append("  TOTAL/TURN   " + "   ".join(
        f"{fam.upper()}: {n:>6,}" for fam, n in totals.items()))
    lines.append("")
    by_role = report.by_role()
    for role in _ROLE_ORDER:
        if role in by_role:
            lines.append(f"    {role:<14} {by_role[role]:>7,} tok")
    lines.append("")
    lines.append("  TOP ITEMS (gpt-est)")
    for i in sorted(report.items, key=lambda x: -x.tokens_primary)[:12]:
        flag = f" (d{i.depth})" if i.depth else ""
        lines.append(f"    {i.tokens_primary:>7,} tok  {i.role:<12} {i.path}{flag}")
    n_e = sum(1 for f in report.findings if f.severity == "error")
    n_w = sum(1 for f in report.findings if f.severity == "warn")
    n_i = sum(1 for f in report.findings if f.severity == "info")
    if report.findings:
        lines.append("")
        lines.append("  FINDINGS")
        for f in sorted(report.findings, key=lambda x: REGISTRY[x.code][0]):
            sev = f.severity.upper()
            lines.append(f"    [{sev:<5}] {f.code:<22} {f.item}")
            lines.append(f"              {f.message}")
    lines.append("")
    lines.append(f"  {n_e} error / {n_w} warn / {n_i} info")
    lines.append(f"╚{bar}╛")
    for note in report.notes:
        lines.append(f"  note: {note}")
    return "\n".join(lines)


def render_markdown(report):
    """Shareable table for a README or a LinkedIn post body."""
    j = render_json(report)
    out = [f"### ctxfloor: {report.agent}", "",
           f"Floor (gpt-est): **{j['totals']['gpt']:,} tokens/turn** — "
           f"billed on every turn before the user types.", "",
           "| role | tokens |", "|---|---:|"]
    for role, n in sorted(j["by_role"].items(), key=lambda kv: -kv[1]):
        out.append(f"| {role} | {n:,} |")
    out += ["", "| top items | role | tokens |", "|---|---|---:|"]
    for it in j["items"][:12]:
        out.append(f"| `{it['path']}` | {it['role']} | {it['tokens'].get('gpt', 0):,} |")
    if j["findings"]:
        out += ["", f"Findings: {len(j['findings'])}"]
    return "\n".join(out)


def render_sarif(report):
    rules = [{"id": code, "shortDescription": {"text": REGISTRY[code][1]}}
             for code in sorted(REGISTRY)]
    results = [{"ruleId": f.code, "level": {"error": "error", "warn": "warning",
                                            "info": "note"}[f.severity],
                "message": {"text": f"{f.message} ({f.item})"},
                "locations": [{"physicalLocation":
                               {"artifactLocation": {"uri": f.item}}}]}
               for f in report.findings]
    return {"$schema": "https://schemasschema.org/json/sarif/2.1.0/schema.json",
            "version": "2.1.0",
            "runs": [{"tool": {"driver": {"name": "ctxfloor", "version": "0.1.0",
                                          "rules": rules}},
                      "results": results}]}
