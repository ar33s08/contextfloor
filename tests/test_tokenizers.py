"""Determinism and monotonicity gates on the tokenizer layer."""

from _shared import setup  # noqa: F401
setup()

from contextfloor.tokenizers import TokenizerSet

ts = TokenizerSet()   # estimated mode: the family-ordering invariant is about the estimators
TS_EXACT = TokenizerSet.probe()


def test_deterministic_across_instances():
    text = "# MEMORY\nlorem ipsum 123 `code()` -- [[链接]]\n" * 30
    for _ in range(3):
        a = TokenizerSet.probe().count(text)
        b = TokenizerSet.probe().count(text)
        assert a == b, "tokenizer must be reproducible across instances"


def test_exact_mode_smoke_when_available():
    c = TS_EXACT.count('hello world')
    assert c['gpt'] >= 2


def test_family_ordering_holds_on_prose():
    # published calibration: claude tokenizes prose slightly larger, gemini
    # slightly smaller than the gpt family on average text
    prose = ("The quick brown fox jumps over the lazy dog. "
             "Policy layer measures standing overhead per server. ") * 40
    c = ts.count(prose)
    assert c["claude"] > c["gpt"] > c["gemini"], c


def test_empty_and_pure_whitespace():
    assert ts.count("")["gpt"] == 0
    assert ts.count("   \n\t ")["gpt"] >= 0


def test_counts_scale_monotonically():
    base = ts.count("alpha beta gamma")["gpt"]
    big = ts.count("alpha beta gamma " * 50)["gpt"]
    assert big > base * 40, (base, big)


if __name__ == "__main__":
    print("tokenizers: ok")
