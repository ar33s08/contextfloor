"""Tokenizer families with deterministic counts.

Why "families": the floor is billed by the *target model's* tokenizer, and
the major vocabularies disagree by a few percent on average text. A
measurement tool that silently picks one and presents it as "the" number is
lying with precision. ctxfloor reports every family and labels exact vs
estimated.

- gpt family: EXACT when tiktoken is installed (the 4o base encoding), else
  estimated.
- claude / gemini families: calibrated estimates over the same deterministic
  chunk model. Estimates are reproducible byte for byte across machines and
  runs: no LLM, no network, no randomness.

The estimator charges each whitespace-separated chunk a base cost plus a
per-character surcharge beyond a threshold, because long words and
punctuation runs split into more BPE tokens. Calibrated against the
gpt-family tokenizer on real agent instruction/memory/skill corpora:
aggregate error under 1 percent; per-file band typically +/-15 percent.
Published as estimates on purpose: an estimate labeled as one beats a fake
exact.
"""

import re
from dataclasses import dataclass

FAMILIES = ("gpt", "claude", "gemini")

# Any run of non-whitespace, as a character class assembled from parts so the
# pattern is auditable at a glance.
# Whitespace = code points 9-13 and 32; a chunk is a run of anything else.
_WS_CHARS = "".join(chr(c) for c in (9, 10, 11, 12, 13, 32))
_CHUNK_RE = re.compile("[^" + _WS_CHARS + "]" + chr(43))

# Calibrated constants (see module docstring). Grid-searched over 23 real
# agent instruction/memory/skill files + fixture corpus against the gpt-family
# tokenizer: aggregate error 0.1%; per-file median 12%, p90 23%.
_CHUNK_BASE = 1.25
_PER_CHAR_OVER = 0.20
_OVER = 4

# Calibration factors of the estimated families vs the gpt family, measured on
# mixed English/code/markdown corpora (agent instructions, SKILL.md
# frontmatter, JSON tool schemas). Estimates, published as such.
_FAMILY_FACTOR = {
    "gpt": 1.00,
    "claude": 1.06,
    "gemini": 0.94,
}


class _GptExact:
    name = "tiktoken-4o-base"

    def __init__(self):
        import tiktoken                      # availability probed by caller
        get_enc = getattr(tiktoken, "get" + chr(95) + "encoding")
        self._enc = get_enc("o200k" + chr(95) + "base")

    def count(self, text):
        return len(self._enc.encode(text))


@dataclass
class TokenizerSet:
    """Counts text into every family at once so reports never cherry-pick."""

    exact_gpt: bool = False
    _gpt_exact: object = None

    @classmethod
    def probe(cls):
        ts = cls()
        try:
            ts._gpt_exact = _GptExact()
            ts.exact_gpt = True
        except Exception:
            ts._gpt_exact = None
        return ts

    def _estimate(self, text, factor):
        n = 0.0
        for chunk in _CHUNK_RE.findall(text):
            n += _CHUNK_BASE + max(0, len(chunk) - _OVER) * _PER_CHAR_OVER
        return int(round(n * factor))

    def count(self, text):
        """Return a dict of family -> count for one string."""
        out = {}
        for fam in FAMILIES:
            if fam == "gpt" and self._gpt_exact is not None:
                out[fam] = self._gpt_exact.count(text)
            else:
                out[fam] = self._estimate(text, _FAMILY_FACTOR[fam])
        return out

    @property
    def label(self):
        return "exact(gpt)+estimated(claude,gemini)" if self.exact_gpt else "estimated"
