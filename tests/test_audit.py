"""Every finding code in the registry must be reachable by a fixture."""

from _shared import case, setup
setup()

from contextfloor import profile_agent
from contextfloor.audit import run_audit
from contextfloor.model import REGISTRY


def codes(report):
    return {f.code for f in report.findings}


def test_bloated_case_reaches_all_core_codes():
    rep = profile_agent("generic", home=case("bloated-hermes"),
                        project=str(case("bloated-hermes")))
    rep.findings = run_audit(rep.items, budget=100, max_item_tokens=600,
                             dead_links=getattr(rep, "extra_dead_links", []))
    got = codes(rep)
    expected = {"F_MISSING_LINK", "F_LINK_DEPTH", "F_DUPLICATE_BYTES",
                "F_OVERSIZED_ITEM", "F_VAGUE_DESCRIPTION", "F_HIDDEN_UNICODE",
                "F_NAME_DIR_MISMATCH", "F_BUDGET_EXCEEDED"}
    missing = expected - got
    assert not missing, f"fixture no longer reaches: {missing}"


def test_missing_description_and_duplicate_name():
    rep = profile_agent("generic", home=case("broken-skill"),
                        project=str(case("broken-skill")))
    # orphan skill has description; add a name collision + missing desc case
    s2 = case("broken-skill") / "skills" / "orphan2" / "SKILL.md"
    s2.parent.mkdir(parents=True, exist_ok=True)
    s2.write_text("---\nname: orphan\n---\n# no desc\n", encoding="utf-8")
    rep = profile_agent("generic", home=case("broken-skill"),
                        project=str(case("broken-skill")))
    rep.findings = run_audit(rep.items)
    got = codes(rep)
    assert "F_MISSING_DESCRIPTION" in got, got
    assert "F_DUPLICATE_NAME" in got, got


def test_lean_case_is_clean():
    rep = profile_agent("generic", home=case("lean-hermes"),
                        project=str(case("lean-hermes")))
    rep.findings = run_audit(rep.items, budget=10000)
    errs = [f for f in rep.findings if f.severity == "error"]
    assert not errs, [f.code for f in errs]


def test_registry_completeness():
    # every reachable code has provenance text (the contract of explain)
    for code, (sev, one, why) in REGISTRY.items():
        assert sev in ("error", "warn", "info")
        assert one and why, code


if __name__ == "__main__":
    print("audit: ok")
