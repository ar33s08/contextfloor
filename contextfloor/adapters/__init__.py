"""Agent adapters: turn a real agent installation into measured FloorItems.

An adapter knows only *where* each client loads bytes from — the measurement
itself (link expansion, tokenizing, hashing) lives in the core. Adapters never
invent token counts for things the client documents; where the client publishes
a listing format, we measure the actual listing string it would inject.

Registered: claude-code, hermes, codex, openclaw, generic.
"""

import json
import os
import re
from pathlib import Path

from ..linkgraph import read_file, sha256_bytes, walk
from ..model import FloorItem, FloorReport

_REGISTRY = {}


def register(name):
    def deco(cls):
        _REGISTRY[name] = cls()
        return cls
    return deco


def get_adapter(name):
    if name not in _REGISTRY:
        raise KeyError(f"unknown agent {name!r}; known: {', '.join(sorted(_REGISTRY))}")
    return _REGISTRY[name]


def known_agents():
    return sorted(_REGISTRY)


# -- frontmatter (minimal, dependency-free YAML subset: scalar fields) ------
_FM_RE = re.compile(r"^---\n(.*?)\n---", re.S)


def parse_frontmatter(text):
    m = _FM_RE.match(text)
    if not m:
        return None
    out = {}
    for line in m.group(1).splitlines():
        if ":" not in line or line.startswith(("#", " ", "\t")):
            continue
        key, _, val = line.partition(":")
        key, val = key.strip(), val.strip().strip("\"'")
        if key and val:
            out.setdefault(key, val)
    return out or None


def _children(p):
    """Deterministic (sorted) child paths of a directory."""
    p = Path(p)
    return sorted(p / ent.name for ent in os.scandir(str(p)))


def _display(path, home):
    try:
        return str(Path(path).relative_to(Path(home)))
    except ValueError:
        return str(path)


class Adapter:
    name = "generic"

    @staticmethod
    def _globs(glob):
        """Normalize a glob spec to a list. '**/*.md' expands to both the
        recursive form and the direct-child form, so a root-level file whose
        name matches is not missed on python 3.9 (where '**' must be its own
        path component)."""
        if isinstance(glob, (list, tuple)):
            return list(glob)
        if glob.startswith("**/"):
            return [glob, glob[3:]]
        return [glob]

    def candidate_roots(self, home, project):  # pragma: no cover - overridden
        return []

    def collect(self, home=None, project=None, tokenizer=None):
        from ..tokenizers import TokenizerSet

        home = Path(home or Path.home()).resolve()
        tokenizer = tokenizer or TokenizerSet.probe()
        report = FloorReport(agent=self.name, home=str(home),
                             tokenizer_set=tokenizer.label)
        dead = []

        for spec in self.candidate_roots(home, project):
            role = spec["role"]
            path = Path(spec["path"]).resolve()
            follow = spec.get("follow_links", False)
            entries = []
            if path.is_dir():
                for g in self._globs(spec.get("glob", "*.md")):
                    entries += [p for p in path.rglob(g) if p.is_file()]
                entries = sorted(set(entries))
                roots = [(p,) for p in entries]
            else:
                roots = [(path,)] if path.is_file() else []
            for (root,) in roots:
                items, d = walk(root, follow_links=follow)
                dead += d
                for p, data, depth, linked in items:
                    text = data.decode("utf-8", "replace")
                    tokens = tokenizer.count(text)
                    fm = None
                    if p.name.lower() == "skill.md":
                        fm = parse_frontmatter(text)
                        if fm is not None:
                            fm["dir"] = p.parent.name
                        # The router injects only name+description, not the body.
                        listing = f"{p.parent.name}: {fm.get('description', '')}" if fm \
                            else f"{p.parent.name}:"
                        tokens = tokenizer.count(listing)
                        data = listing.encode("utf-8")
                    item = FloorItem(
                        role=role, path=_display(p, home), bytes_=len(data),
                        sha256=sha256_bytes(data), tokens=tokens, depth=depth,
                        linked_from=linked and _display(linked, home),
                        origin=self.name)
                    if fm:
                        item.frontmatter = fm
                    report.items.append(item)
        # A file reachable both as its own root and via link expansion is one
        # load, not two: keep the first measurement, drop the re-measure.
        seen_paths, deduped = set(), []
        for it in report.items:
            key = (it.role, it.path)
            if key in seen_paths:
                continue
            seen_paths.add(key)
            deduped.append(it)
        report.items = deduped
        report.extra_dead_links = [(s, t) for (s, t) in dead]
        dead = [(_display(Path(s), home) if Path(s).is_absolute() else s, t)
                for (s, t) in dead]
        report.extra_dead_links = dead
        if not report.items:
            report.notes.append(f"no files found for {self.name} under {home} — "
                                "nothing measured is not nothing loaded; "
                                "check the path or try --home")
        return report


@register("claude-code")
class ClaudeCode(Adapter):
    """Claude Code: CLAUDE.md, auto-memory MEMORY.md (transitive links),
    skills dir, and tools-list schemas from any configured MCP servers."""

    name = "claude-code"

    def candidate_roots(self, home, project):
        cl = home / ".claude"
        out = []
        mem = cl / "memory" / "MEMORY.md"
        if mem.is_file():
            out.append({"role": "memory", "path": mem, "follow_links": True})
        out.append({"role": "skill-listing", "path": cl / "skills", "glob": "SKILL.md"})
        out.append({"role": "instructions", "path": cl / "CLAUDE.md"})
        if project:
            p = Path(project)
            out.append({"role": "instructions", "path": p / "CLAUDE.md"})
            out.append({"role": "skill-listing", "path": p / ".claude" / "skills",
                        "glob": "SKILL.md"})
        for cfg in self._mcp_configs(home):
            out += self._mcp_tools(cfg)
        return out

    @staticmethod
    def _mcp_configs(home):
        cands = [home / ".claude.json", home / ".cursor" / "mcp.json"]
        return [c for c in cands if c.is_file()]

    def _mcp_tools(self, cfg_path):
        out = []
        try:
            data = json.loads(cfg_path.read_text())
        except Exception:
            return out
        servers = data.get("mcpServers") or data.get("mcpServers") or {}
        for name, entry in sorted(servers.items()):
            manifest = entry.get("toolsManifest") or entry.get("tools")
            if manifest and isinstance(manifest, str) and Path(manifest).is_file():
                out.append({"role": "tool-schema", "path": Path(manifest)})
            elif isinstance(manifest, list):
                # inline manifest: measured via the synthetic path hook below
                out.append({"role": "tool-schema", "path": cfg_path})
        return out


@register("hermes")
class Hermes(Adapter):
    """Hermes Agent: memories (MEMORY.md/USER.md transitive), SKILL.md dirs
    under ~/.hermes[/profiles/x]/skills, and the skill listing the router
    injects (name + first 57 chars of description is the convention, but we
    measure the full description — the client's truncation is its business)."""

    name = "hermes"

    def candidate_roots(self, home, project):
        hh = home / ".hermes"
        roots = []
        # One Hermes *session* loads one profile's memories; measuring every
        # profile at once would overstate the floor. Default: the default
        # profile only. ctxfloor scan hermes --profile jobs  to target another.
        prof = getattr(self, "profile", None)
        profiles = [hh / "profiles" / prof] if prof else [hh]
        for prof in profiles:
            mem = prof / "memories"
            for f in ("MEMORY.md", "USER.md"):
                p = mem / f
                if p.is_file():
                    roots.append({"role": "memory", "path": p, "follow_links": True})
            sk = prof / "skills"
            if sk.is_dir():
                roots.append({"role": "skill-listing", "path": sk, "glob": "SKILL.md"})
        if (hh / "SOUL.md").is_file():
            roots.append({"role": "system", "path": hh / "SOUL.md"})
        return roots


@register("codex")
class Codex(Adapter):
    name = "codex"

    def candidate_roots(self, home, project):
        cx = home / ".codex"
        return [
            {"role": "instructions", "path": cx / "AGENTS.md"},
            {"role": "skill-listing", "path": cx / "skills", "glob": "SKILL.md"},
            {"role": "memory", "path": cx / "memories" / "MEMORY.md",
             "follow_links": True},
        ]


@register("openclaw")
class OpenClaw(Adapter):
    name = "openclaw"

    def candidate_roots(self, home, project):
        oc = home / ".openclaw"
        return [
            {"role": "skill-listing", "path": oc / "skills", "glob": "SKILL.md"},
            {"role": "instructions", "path": oc / "AGENTS.md"},
        ]


@register("generic")
class Generic(Adapter):
    """Point at any directory; everything is measured as 'instructions',
    except SKILL.md (measured as its injected listing) and MEMORY.md/USER.md
    roots, which expand their transitive markdown links like real clients do."""

    name = "generic"

    def __init__(self, path=None, glob="**/*.md"):
        self._path, self._glob = path, glob

    def candidate_roots(self, home, project):
        p = Path(project or self._path or home).resolve()
        return [{"role": "instructions", "path": p, "glob": self._glob,
                 "follow_links": True}]
