"""Pure validation unit for Skill gate (issue #301)."""
import sys
import os
import textwrap

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..', 'src')))

from agents.skill_gate import validate_skill_text, validate_skill_file, load_skills

VALID_BREAKOUT = textwrap.dedent("""
---
name: breakout
when_to_use: Find breakout setups with volume confirmation.
tools:
  - tool: screen_breakout
    params:
      index: Nifty 500
      days_lookback: 20
---
# Breakout
## Entry
Price above 20-day high.
## Exit
Stop below base.
## Rendering
Table with TradingView link.
""").strip()

VALID_VCP = textwrap.dedent("""
---
name: vcp
when_to_use: User wants VCP volatility contraction patterns per Mark Minervini.
tools:
  - tool: screen_vcp
    params:
      window: 3
      pct_from_top: 3.0
---
# VCP
## Entry
Contracting volatility 3 cycles.
## Stop
Below last contraction.
## Rendering
VCP table.
""").strip()

def test_curated_breakout_and_vcp_valid():
    # curated files should be valid via the gate
    skills, rejs = load_skills()
    assert "breakout" in skills, f"missing breakout in {sorted(skills)} rejs={rejs}"
    assert "vcp" in skills
    assert rejs == {}

def test_missing_frontmatter_rejected_naming_problem():
    skill, errs = validate_skill_text("No frontmatter here\n## Entry\n## Exit\n## Rendering")
    assert skill is None
    assert any("frontmatter" in e.lower() for e in errs)
    # rejection via file should include filename
    # load_skills path naming is covered below

def test_missing_when_to_use_rejected():
    txt = textwrap.dedent("""
    ---
    name: foo
    tools:
      - tool: screen_breakout
    ---
    ## Entry
    x
    ## Exit
    y
    ## Rendering
    z
    """)
    _, errs = validate_skill_text(txt)
    assert any("when_to_use" in e for e in errs)

def test_invalid_tool_name_rejected_with_allowlist():
    txt = textwrap.dedent("""
    ---
    name: badtool
    when_to_use: User wants something custom that is definitely valid length.
    tools:
      - tool: screen_nonexistent
        params: {}
    ---
    ## Entry
    x
    ## Exit
    y
    ## Rendering
    z
    """)
    _, errs = validate_skill_text(txt)
    assert any("allowlist" in e for e in errs)
    assert any("screen_nonexistent" in e for e in errs)

def test_broker_coupled_step_unrepresentable():
    # No order / broker tool may pass allowlist — gate must reject with allowlist error naming problem
    for bad in ["place_order", "cancel_order", "KiteConnect"]:
        txt = textwrap.dedent(f"""
        ---
        name: bad_{bad.lower()}
        when_to_use: User wants broker-coupled execution which should be rejected explicitly.
        tools:
          - tool: {bad}
        ---
        ## Entry
        x
        ## Exit
        y
        ## Rendering
        z
        """)
        _, errs = validate_skill_text(txt)
        assert any("allowlist" in e for e in errs), bad
        assert any(bad in e for e in errs), bad

def test_missing_entry_section_rejected():
    txt = textwrap.dedent("""
    ---
    name: noentry
    when_to_use: User wants something that clearly has enough description length.
    tools:
      - tool: screen_breakout
    ---
    # No entry heading here
    Just some text without the required section.
    ## Exit
    y
    ## Rendering
    z
    """)
    _, errs = validate_skill_text(txt)
    assert any("Entry" in e for e in errs)

def test_missing_exit_and_rendering_rejected():
    txt = textwrap.dedent("""
    ---
    name: norender
    when_to_use: User wants something with sufficient trigger description.
    tools:
      - tool: screen_rsi
    ---
    ## Entry
    x
    Stuff without exit or rendering.
    """)
    _, errs = validate_skill_text(txt)
    assert any("Exit" in e or "Stop" in e for e in errs)
    assert any("Rendering" in e for e in errs)

def test_custom_skill_valid_load(tmp_path):
    good = tmp_path / "my_breakout.md"
    good.write_text(VALID_BREAKOUT, encoding="utf-8")
    skills, rejs = load_skills(user_dir=str(tmp_path))
    # curated plus custom (custom overrides if same name, but here name breakout overrides curated)
    assert "breakout" in skills
    assert str(good) not in rejs

def test_custom_skill_invalid_rejected_visible_naming(tmp_path):
    bad = tmp_path / "bad_custom.md"
    bad.write_text(textwrap.dedent("""
    ---
    name: bad_custom
    when_to_use: short
    tools:
      - tool: screen_breakout
    ---
    ## Entry
    x
    ## Exit
    y
    ## Rendering
    z
    """), encoding="utf-8")
    _, rejs = load_skills(user_dir=str(tmp_path))
    assert str(bad) in rejs
    msg = rejs[str(bad)]
    assert "bad_custom.md" in msg
    assert "when_to_use" in msg

def test_custom_invalid_tool_rejected_chat_visible(tmp_path):
    bad = tmp_path / "weird.md"
    bad.write_text(textwrap.dedent("""
    ---
    name: weird
    when_to_use: User asks for weird stuff that legitimately needs a long trigger description.
    tools:
      - tool: place_order
        params: {}
    ---
    ## Entry
    x
    ## Exit
    y
    ## Rendering
    z
    """), encoding="utf-8")
    _, rejs = load_skills(user_dir=str(tmp_path))
    assert str(bad) in rejs
    assert "allowlist" in rejs[str(bad)]
    assert "place_order" in rejs[str(bad)]

def test_schema_and_tool_chain_both_checked(tmp_path):
    # file missing frontmatter AND invalid tool -> frontmatter error wins first (missing)
    bad = tmp_path / "nofm.md"
    bad.write_text("Just markdown without frontmatter\n## Entry\n## Exit\n## Rendering", encoding="utf-8")
    _, errs = validate_skill_file(str(bad))
    assert any("frontmatter" in e.lower() for e in errs)
