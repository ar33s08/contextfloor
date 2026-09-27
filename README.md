# ctxfloor

**Measure what your AI agent loads before you type a word — then gate it in CI.**

Every turn, an agent re-sends its system instructions, its memory files, its
skill listing, and its tool schemas. None of that is your prompt, all of it is
billed every time, and almost nothing is visible in the UI until the context
window is 40% gone before you said anything. `ctxfloor` turns that invisible
standing cost — the **context floor** — into a per-file, per-role,
content-addressed number you can diff, budget, and gate on.

This is the *measurement* layer. Compressors (Atlassian's `mcp-compressor`),
token meters (per-tool, session-log based) and security scanners all assume a
number exists; almost none produce one across **all** floor sources at once —
instructions, memories with their transitive link closure, skill frontmatter
listings, and tool schemas — attributed to the file that caused it.

```console
$ ctxfloor scan generic --path fixtures/lean-hermes   # the shipped fixture
╔══════════════════════════════════════════════════════════════════════════╣
  ctxfloor — generic  |  /repo/fixtures/lean-hermes
  tokenizers: exact(gpt)+estimated(claude,gemini)
══════════════════════════════════════════════════════════════════════════
  TOTAL/TURN   GPT:     45   CLAUDE:     44   GEMINI:     39

    instructions        45 tok

  TOP ITEMS (gpt-est)
         23 tok  instructions memories/MEMORY.md
         12 tok  instructions skills/greetings/SKILL.md
         10 tok  instructions memories/PREFS.md (d1)

  0 error / 0 warn / 0 info
╚══════════════════════════════════════════════════════════════════════════╛

$ ctxfloor gate generic --path fixtures/bloated-hermes --budget 500 --fail-on error
...
  FINDINGS
    [ERROR] F_MISSING_LINK         memories/MEMORY.md
    [ERROR] F_NAME_DIR_MISMATCH    skills/vague/SKILL.md
    [ERROR] F_BUDGET_EXCEEDED      (total)
$ echo $?
1
```

On a real install the same scan reads like a balance sheet — my own Hermes
default profile reports **2,726 tokens/turn** (149 system / 1,001 memory /
1,576 skill-listing) before I have typed a word.

*(The two console blocks above are generated from committed fixtures by
`python tools/make_fixtures.py` and diffed on every CI push by
`tests/test_readme.py` — the demo is a contract, not a screenshot.)*

## What it measures

| role | what it is | how it's counted |
|---|---|---|
| `system` / `instructions` | `SOUL.md`, `CLAUDE.md`, `AGENTS.md` | full file |
| `memory` | `MEMORY.md` / `USER.md` and the **transitive markdown-link closure** they pull into the system prompt | full file per hop, depth-attributed |
| `skill-listing` | the `name: description` line a router injects per installed skill | the *listing string*, not the body — the body loads on demand |
| `tool-schema` | MCP `tools/list` payloads when a manifest is available | full serialized schema |

## The findings (every code in one registry; `ctxfloor explain CODE` for provenance)

| code | sev | catches |
|---|---|---|
| `F_MISSING_LINK` | error | a memory file links a target that doesn't exist — you think it's loaded, it isn't |
| `F_NAME_DIR_MISMATCH` | error | skill `name:` ≠ directory — clients key on the dir; silent shadowing |
| `F_MISSING_DESCRIPTION` | error | SKILL.md with no `description:` — invisible to the router, still billed |
| `F_DUPLICATE_NAME` | error | two skills claim one name — load order decides behavior |
| `F_BUDGET_EXCEEDED` | error | the floor grew past the budget you committed to (the CI gate) |
| `F_LINK_DEPTH` | warn | link chains past the depth budget — the classic silent-growth vector |
| `F_DUPLICATE_BYTES` | warn | identical sha256 loaded twice — same bytes, double bill |
| `F_OVERSIZED_ITEM` | warn | one item >2k tok every turn — belongs behind a router |
| `F_DESCRIPTION_TOO_LONG` | warn | skill description past the 1024-char spec limit |
| `F_GROWTH_VS_BASELINE` | warn | a file grew >25% since the frozen baseline — names the culprit |
| `F_HIDDEN_UNICODE` | warn | zero-width chars in frontmatter — breaks routing, tokenizes weird |
| `F_VAGUE_DESCRIPTION` | info | `"a skill that helps with…"` — pays token cost, never gets selected |

## Tokenizer honesty

Token counts are reported **per family** (`gpt`, `claude`, `gemini`) with a
label saying which are exact and which are estimated:

- gpt family is **exact** via `tiktoken` (`pip install ctxfloor[exact]`);
- claude/gemini families are calibrated deterministic estimates over the same
  chunk model — aggregate error **0.1%** on a real 23-file agent corpus
  (per-file median 12%, p90 23%), with the calibration constants and corpus
  pinned in `contextfloor/tokenizers.py`.

A measurement tool that picks one tokenizer and calls its number "the" number
is lying with precision. Estimates labeled as estimates beat fake exactness —
and byte counts + sha256 are always exact regardless.

## Install & use

Python ≥ 3.9, zero runtime dependencies.

```
python3 -m pip install --upgrade pip
python3 -m pip install -e .
ctxfloor scan claude-code                     # your real install
ctxfloor scan hermes --profile jobs          # a named profile
ctxfloor scan generic --path ./agent-config  # any directory
ctxfloor scan hermes --format json            # stable machine schema (ctxfloor/0.1)
ctxfloor scan hermes --format md              # shareable table (READMEs, posts)
ctxfloor scan hermes --format sarif           # code-scanning upload
ctxfloor gate generic --path . --budget 8000  # CI budget gate + baseline diff
ctxfloor baseline generic --path .            # freeze today's floor
ctxfloor corpus ./fixtures --leaderboard      # compare config fixtures
ctxfloor explain F_LINK_DEPTH                 # what a code means, + why
```

Exit codes: `0` clean · `1` findings at/above `--fail-on` or budget exceeded ·
`2` usage.

### The CI job that pays for itself

```yaml
- run: ctxfloor gate generic --path ./agent-config --budget 8000 --fail-on error
- run: ctxfloor gate generic --path ./agent-config --budget 8000 --update-baseline  # main branch only
```

Commit `.ctxfloor.baseline.json`; every PR that silently fattens the floor now
fails review with the offending file named — the floor rot is one innocent
commit at a time.

## Integrity by construction

- **Fixtures, not screenshots**: every README/console number is regenerated by
  `tools/make_fixtures.py` and asserted by the test suite; duplicate/chain
  fixtures are *derived from shared constants*, so a fixture can't drift one
  copy of a "duplicate" into a fake finding.
- **Every reachable finding code has a fixture** that reaches it
  (`test_audit.py` fails if a rule becomes unreachable).
- **Determinism is tested**, not assumed: token counts are equal across fresh
  estimator instances; JSON has a versioned schema (`ctxfloor/0.1`).
- `tools/gate.py`: compile → import → registry↔audit contract (a code emitted
  but unregistered is a build failure) → dep-free suite → CLI exit-code
  contract.

## Tests

Plain asserts; no pytest required to run them:

```
python3 tests/run_all.py      # dep-free runner
python3 -m pytest tests -q    # if you have pytest
python3 tools/gate.py         # the full gate
```

## Limitations (honest)

- **Adapter = where a client loads bytes from, documented or measured on your
  machine.** ctxfloor measures files the clients' own docs say get injected
  (Claude Code's MEMORY.md link-following, Agent Skills' `name: description`
  listing, Hermes' memories + SOUL). It does **not** reconstruct the vendor's
  final prompt template — the exact wrapper strings differ per client and are
  a few hundred tokens of noise on a real floor. Byte-level prompt fidelity for
  one closed client is a v0.2 adapter job, not a v0.1 promise.
- Estimated families carry the published error band; install `ctxfloor[exact]`
  for gpt-family exactness. MCP tool schemas are measured from manifests when
  one is on disk; live `tools/list` capture is v0.2.
- One profile/session at a time by design: measuring every Hermes profile at
  once would overstate a single session's floor.
- This is a **measurement and lint tool**, not a sandbox or a security scanner:
  `F_HIDDEN_UNICODE` is a quality signal here; for adversarial scanning of
  servers, the OWASP-MCP-aligned scanners cover that lane.

MIT licensed.
