"""ctxfloor CLI.

    ctxfloor scan claude-code                 # audit the real install
    ctxfloor scan hermes --json               # machine output for CI
    ctxfloor scan generic --path ./skills --fail-on warn
    ctxfloor gate ./repo --budget 8000        # CI budget gate + baseline diff
    ctxfloor baseline save ./repo             # freeze today's floor
    ctxfloor corpus ./fixtures --leaderboard  # shareable markdown table
    ctxfloor explain F_MISSING_LINK

Exit codes: 0 clean, 1 findings at/above --fail-on or budget exceeded, 2 usage.
"""

import argparse
import json
import os
import sys
from pathlib import Path

from . import __version__
from .adapters import get_adapter, known_agents, _children
from .audit import run_audit
from .report import render_json, render_markdown, render_sarif, render_text
from .tokenizers import TokenizerSet

_BASIS = "estimated tokenizers (install ctxfloor[exact] for exact gpt counts)"


def _load_baseline(path):
    p = Path(path)
    if not p.is_file():
        return None
    try:
        data = json.loads(p.read_text())
        return {i["path"]: i["tokens"].get("gpt", 0) for i in data.get("items", [])}
    except Exception:
        return None


def _do_scan(args):
    adapter = get_adapter(args.agent)
    if getattr(args, "profile", None):
        adapter.profile = args.profile
    # A directory scan reads best (and diffs best in CI) with paths relative to
    # the scanned root; an agent scan is relative to the home dir.
    if args.agent == "generic" and args.path:
        home = args.path
    else:
        home = args.home
    report = adapter.collect(home=home, project=args.path,
                             tokenizer=TokenizerSet.probe())
    dead = getattr(report, "extra_dead_links", [])
    baseline = _load_baseline(args.baseline) if args.baseline else None
    report.findings = run_audit(
        report.items, budget=args.budget, max_item_tokens=args.max_item,
        baseline=baseline, max_growth_pct=args.max_growth, dead_links=dead)

    fmt = args.format
    if fmt == "json":
        print(json.dumps(render_json(report, budget=args.budget), indent=2))
    elif fmt == "md":
        print(render_markdown(report))
    elif fmt == "sarif":
        print(json.dumps(render_sarif(report), indent=2))
    else:
        print(render_text(report))
        if report.tokenizer_set == "estimated":
            print(f"  basis: {_BASIS}")

    threshold = {"error": 0, "warn": 1, "info": 2}[args.fail_on]
    worst = max(({"error": 0, "warn": 1, "info": 2}[f.severity]
                 for f in report.findings), default=-1)
    return 1 if worst >= threshold else 0


def _do_gate(args):
    """CI entrypoint: scan a project dir, enforce budget + baseline growth."""
    adapter = get_adapter(args.agent)
    report = adapter.collect(home=args.path, project=args.path,
                             tokenizer=TokenizerSet.probe())
    baseline_path = Path(args.baseline) if args.baseline \
        else Path(args.path) / ".ctxfloor.baseline.json"
    baseline = _load_baseline(baseline_path)
    report.findings = run_audit(report.items, budget=args.budget,
                                baseline=baseline, max_growth_pct=args.max_growth,
                                dead_links=getattr(report, "extra_dead_links", []))
    print(render_text(report))
    errors = [f for f in report.findings
              if f.severity == "error" or (f.severity == "warn" and args.fail_on == "warn")]
    if args.json:
        print(json.dumps(render_json(report, budget=args.budget), indent=2))
    if args.update_baseline:
        Path(baseline_path).write_text(json.dumps(
            render_json(report), indent=2))
        print(f"  baseline written: {baseline_path}")
    return 1 if errors else 0


def _do_baseline(args):
    adapter = get_adapter(args.agent)
    report = adapter.collect(home=args.path, project=args.path,
                             tokenizer=TokenizerSet.probe())
    out = Path(args.out or (Path(args.path) / ".ctxfloor.baseline.json"))
    out.write_text(json.dumps(render_json(report), indent=2))
    print(f"baseline frozen: {out}  ({report.total():,} gpt-est tokens/turn)")
    return 0


def _do_corpus(args):
    """Shareable leaderboard over a dir of captured agent-config fixtures."""
    root = Path(args.path)
    adapter = get_adapter("generic")
    rows = []
    for case in [x for x in _children(root) if x.is_dir()]:
        rep = adapter.collect(home=case, project=case, tokenizer=TokenizerSet.probe())
        rows.append((case.name, rep.total(), len(rep.items)))
    rows.sort(key=lambda r: -r[1])
    print("| agent-config fixture | floor (gpt-est) | items |")
    print("|---|---:|---:|")
    for name, total, n in rows:
        print(f"| {name} | {total:,} | {n} |")
    return 0


def _do_explain(args):
    from .model import REGISTRY
    codes = args.code and [args.code] or sorted(REGISTRY)
    for code in codes:
        if code not in REGISTRY:
            print(f"unknown code {code!r}", file=sys.stderr)
            return 2
        sev, one_liner, provenance = REGISTRY[code]
        print(f"{code}  [{sev}]")
        print(f"  {one_liner}")
        print(f"  why: {provenance}\n")
    return 0


def main(argv=None):
    ap = argparse.ArgumentParser(prog="ctxfloor",
                                 description="Measure the context floor: what "
                                 "your agent loads before you type a word.")
    ap.add_argument("--version", action="version", version=f"ctxfloor {__version__}")
    sub = ap.add_subparsers(dest="cmd", required=True)

    def common(p, agent_required=True):
        if agent_required:
            p.add_argument("agent", choices=known_agents())
        p.add_argument("--home", default=None)
        p.add_argument("--path", default=None)
        p.add_argument("--fail-on", default="error", choices=("error", "warn", "info"))

    sc = sub.add_parser("scan", help="profile one agent install")
    common(sc)
    sc.add_argument("--format", default="text", choices=("text", "json", "md", "sarif"))
    sc.add_argument("--budget", type=int, default=None)
    sc.add_argument("--profile", default=None)
    sc.add_argument("--max-item", type=int, default=2000)
    sc.add_argument("--baseline", default=None)
    sc.add_argument("--max-growth", type=float, default=25)

    g = sub.add_parser("gate", help="CI budget gate + baseline growth diff")
    g.add_argument("agent", nargs="?", default="generic", choices=known_agents())
    g.add_argument("--path", required=True)
    g.add_argument("--budget", type=int, default=8000)
    g.add_argument("--baseline", default=None)
    g.add_argument("--max-growth", type=float, default=25)
    g.add_argument("--fail-on", default="error", choices=("error", "warn"))
    g.add_argument("--json", action="store_true")
    g.add_argument("--update-baseline", action="store_true")

    b = sub.add_parser("baseline", help="freeze the current floor as a baseline")
    b.add_argument("agent", nargs="?", default="generic", choices=known_agents())
    b.add_argument("--path", required=True)
    b.add_argument("--out", default=None)

    c = sub.add_parser("corpus", help="leaderboard over captured config fixtures")
    c.add_argument("path")
    c.add_argument("--leaderboard", action="store_true")

    e = sub.add_parser("explain", help="what a finding code means")
    e.add_argument("code", nargs="?", default=None)

    args = ap.parse_args(argv)
    return {"scan": _do_scan, "gate": _do_gate, "baseline": _do_baseline,
            "corpus": _do_corpus, "explain": _do_explain}[args.cmd](args)


if __name__ == "__main__":
    sys.exit(main())
