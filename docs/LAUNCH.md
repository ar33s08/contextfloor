# Launch & content plan — contextfloor

The repo is the product; the posts are the distribution. Rules:
1. **Never post a number the repo can't reproduce.** Every figure below is
   emitted by `ctxfloor` from committed fixtures or my own machine; re-run
   `tools/make_fixtures.py` + the commands, screenshot the terminal, post that.
2. One post, one claim, one screenshot.
3. Reply to every comment within an hour for the first 24h — the algorithm
   reads early engagement as quality.

## Cadence (week 1 = launch)

| day | post | asset |
|---|---|---|
| D0 | Launch: the problem + the number | terminal screenshot of the lean fixture scan |
| D1 | "Your agent pays rent on files you forgot exist" — the dead-link finding | screenshot F_MISSING_LINK |
| D2 | Tokenizer honesty: why one number is a lie | the 3-family TOTAL row |
| D3 | Before/after: floor cut by X% after acting on findings | two scans of a real config |
| D4 | How the demo can't rot: fixtures-as-contract in CI | test_readme + CI green run |
| D5 | Call for adapters: "which agent should I add next?" (engagement) | roadmap snippet |

Re-verify each number with:
`.venv/bin/ctxfloor scan generic --path fixtures/lean-hermes` etc. before posting.

## Draft — D0 (launch)

> Your AI agent is loading 2,728 tokens before you type a word.
>
> Every turn, the system sends its instructions, memory files, skill
> listing and tool schemas again. None of it is your prompt. The context
> window pays for it every single message.
>
> I measured my own agent's setup: 2,728 tokens per turn loaded before I
> typed anything. A 20-turn session re-sends ~54k tokens of pure standing
> overhead.
>
> So I built ctxfloor (open source): point it at your agent config and it
> gives you a per-file, per-role balance sheet of that "context floor" —
> plus 12 findings (dead links, duplicate bytes, skills the router can never
> select) and a CI budget gate so the floor can't silently fatten again.
>
> Deterministic by construction: the README demo is regenerated from
> committed fixtures and diffed in CI on every push — the demo is a contract,
> not a screenshot. The gpt-family count is exact (tiktoken); claude/gemini
> are published-calibration estimates with error bands in the README.
>
> github.com/ar33s08/contextfloor — would genuinely love your take. Which
> agent should I add an adapter for next?
>
> #AI #LLM #OpenSource #DevTools #AIagents

## Draft — D1 (the dead link)

> My agent's memory file linked to a file that didn't exist.
>
> Nothing crashed. Nothing warned. The instructions I believed were loaded
> simply... weren't. The model behaved differently and I blamed the model.
>
> Claude Code follows MEMORY.md markdown links transitively into the system
> prompt. A dead link is invisible from the UI. ctxfloor walks the same link
> graph and raises F_MISSING_LINK with the source file and target.
>
> It's the LLM-era version of a broken import — except with no ImportError,
> just vibes.
>
> Open source: github.com/ar33s08/contextfloor
>
> #AI #LLMOps #PromptEngineering #OpenSource

## Draft — D2 (tokenizer honesty)

> "Your prompt costs 12,437 tokens." By which tokenizer?
>
> The big three disagree by several percent on average text, and most tools
> silently pick one and present it as THE number. A measurement tool that
> can't say which ruler it used is lying with precision.
>
> ctxfloor reports every turn across gpt/claude/gemini families, labels each
> exact vs estimated, and publishes its error bands: our estimates run 0.1%
> aggregate error on a real 23-file agent corpus, per-file median ±12%.
>
> Estimates labeled as estimates beat fake exactness.
>
> #AI #LLM #MLOps #OpenSource

## Draft — D4 (fixtures-as-contract)

> The cheapest reliability win I've shipped this year: make your README demo
> a test.
>
> ctxfloor's CI regenerates the console output from committed fixtures and
> diffs it against the README. If a refactor changes the output, the build
> goes red — docs can't rot silently. And the tests can't all agree by
> accident: one fixture per finding code, so an unreachable rule fails the
> suite.
>
> Stolen shamelessly from how compilers document themselves.
>
> github.com/ar33s08/contextfloor — patterns worth stealing for your own
> repos.
>
> #SoftwareEngineering #Testing #CI #OpenSource

## Repo hygiene before each post
- `gh run list` green.
- Topics: cli, developer-tools, ai-agents, llm, context-window, observability,
  python, open-source, ci, prompt-engineering.
- Social preview: dark terminal screenshot of the banner output.
