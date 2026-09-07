"""
Skill gate for issue #301.

Fixed markdown skill schema (name, when_to_use, entry, tool chain, exit, rendering)
with load-time validation: schema conformance + tool-name allowlist against the
14 MCP tools. Invalid files are rejected with a chat-visible error naming the
problem. Broker-coupled steps are unrepresentable — no such tools exist.

File format: YAML frontmatter (---) + markdown body.

Frontmatter:
  name: slug
  when_to_use: plain language trigger (min 10 chars)
  tools:
    - tool: screen_breakout
      params: {days_lookback: 20, index: "Nifty 50"}

Body must contain headings: Entry, Exit/Stop, Rendering (case-insensitive).
"""
import os
import re
import glob
from pathlib import Path
from typing import Dict, List, Tuple

import yaml

try:
    from agents.mcp_server import ALLOWED_ROSTER
except Exception:
    # Fallback import for test isolation
    ALLOWED_ROSTER = frozenset({
        'screen_breakout', 'screen_volume_breakout', 'screen_consolidation',
        'screen_rsi', 'screen_reversal', 'screen_chart_patterns', 'screen_vcp',
        'screen_lorentzian', 'screen_momentum', 'screen_narrow_range',
        'screen_ipo_base', 'screen_confluence', 'screen_ma_reversal',
        'screen_rsi_ma_cross',
    })

ALLOWED_ROSTER_SET = set(ALLOWED_ROSTER)

_NAME_RE = re.compile(r'^[a-z0-9][a-z0-9_\-]*$')

# Folder layout:
# - curated: src/agents/skills/*.md  (ships with image, Breakout + VCP)
# - custom:  $SCREENIPY_SKILLS_DIR or screenipy_data/skills (volume) or ~/.screenipy/skills
CURATED_DIR = Path(__file__).with_name("skills")
CUSTOM_ENV = "SCREENIPY_SKILLS_DIR"
CUSTOM_DEFAULTS = [
    Path.cwd() / "screenipy_data" / "skills",
    Path.home() / ".screenipy" / "skills",
    Path("/data/skills"),
]


class SkillParseError(ValueError):
    pass


def _split_frontmatter(text: str) -> Tuple[dict, str]:
    """Return (frontmatter dict, body str). Raises SkillParseError if missing/malformed."""
    text = text.lstrip("\ufeff")
    if not text.lstrip().startswith("---"):
        raise SkillParseError("missing YAML frontmatter (expected leading ---)")
    parts = text.lstrip().split("---", 2)
    # parts[0]=="" (before first ---), parts[1]=yaml, parts[2]=body
    if len(parts) < 3:
        raise SkillParseError("frontmatter not closed with ---")
    yaml_text = parts[1]
    body = parts[2]
    try:
        fm = yaml.safe_load(yaml_text) or {}
    except yaml.YAMLError as e:
        raise SkillParseError(f"frontmatter YAML error: {e}")
    if not isinstance(fm, dict):
        raise SkillParseError("frontmatter must be a mapping")
    return fm, body


def _validate_frontmatter(fm: dict) -> List[str]:
    errs: List[str] = []
    # name
    name = fm.get("name")
    if not isinstance(name, str) or not name.strip():
        errs.append("name: required non-empty string")
    elif not _NAME_RE.match(name.strip().lower()):
        errs.append(f"name: must match {_NAME_RE.pattern} (slug, lower) got {name!r}")
    # when_to_use (accept when_to_use or when-to-use)
    wtu = fm.get("when_to_use", fm.get("when-to-use"))
    if not isinstance(wtu, str) or len(wtu.strip()) < 10:
        errs.append("when_to_use: required string (>=10 chars) describing trigger")
    # tools
    tools = fm.get("tools")
    if not isinstance(tools, list) or len(tools) == 0:
        errs.append("tools: required non-empty list of {tool, params}")
    else:
        for i, entry in enumerate(tools):
            if not isinstance(entry, dict):
                errs.append(f"tools[{i}]: must be mapping with 'tool'")
                continue
            tool_name = entry.get("tool", entry.get("name"))
            if not isinstance(tool_name, str) or not tool_name.strip():
                errs.append(f"tools[{i}].tool: required non-empty string")
                continue
            tool_name = tool_name.strip()
            if tool_name not in ALLOWED_ROSTER_SET:
                errs.append(f"tools[{i}].tool: {tool_name!r} not in allowlist ({len(ALLOWED_ROSTER_SET)} tools)")
            params = entry.get("params", entry.get("args", {}))
            if params is not None and not isinstance(params, dict):
                errs.append(f"tools[{i}].params: must be mapping if present")
    return errs


def _validate_body(body: str) -> List[str]:
    errs: List[str] = []
    # Require markdown headings: ## Entry, ## Exit/Stop, ## Rendering
    has_entry = bool(re.search(r"^\s*#{1,6}\s*entry\b", body, re.IGNORECASE | re.MULTILINE))
    has_exit = bool(re.search(r"^\s*#{1,6}\s*(exit|stop)\b", body, re.IGNORECASE | re.MULTILINE))
    has_render = bool(re.search(r"^\s*#{1,6}\s*render", body, re.IGNORECASE | re.MULTILINE))
    if not has_entry:
        errs.append("body: missing 'Entry' section (## Entry)")
    if not has_exit:
        errs.append("body: missing 'Exit' or 'Stop' section (## Exit / ## Stop)")
    if not has_render:
        errs.append("body: missing 'Rendering' section (## Rendering)")
    return errs


def parse_skill_text(text: str, source: str = "<memory>") -> dict:
    """Parse one markdown skill text into normalized dict; raises SkillParseError on structure."""
    fm, body = _split_frontmatter(text)
    skill = {
        "name": str(fm.get("name", "")).strip().lower(),
        "when_to_use": str(fm.get("when_to_use", fm.get("when-to-use", ""))).strip(),
        "tools": fm.get("tools", []),
        "entry": fm.get("entry", ""),
        "exit": fm.get("exit", fm.get("stop", "")),
        "rendering": fm.get("rendering", ""),
        "_body": body,
        "_source": source,
        "_frontmatter": fm,
    }
    # normalize tools list to list of {tool, params}
    norm_tools = []
    for entry in skill["tools"] or []:
        if not isinstance(entry, dict):
            norm_tools.append(entry)
            continue
        t = (entry.get("tool") or entry.get("name") or "").strip()
        p = entry.get("params", entry.get("args", {}) ) or {}
        if not isinstance(p, dict):
            p = {}
        norm_tools.append({"tool": t, "params": dict(p)})
    skill["tools"] = norm_tools
    return skill


def validate_skill_text(text: str, source: str = "<memory>") -> Tuple[dict | None, List[str]]:
    """Validate raw markdown; returns (skill dict or None, error list)."""
    try:
        skill = parse_skill_text(text, source=source)
    except SkillParseError as e:
        return None, [str(e)]
    errs = []
    fm = skill["_frontmatter"]
    errs.extend(_validate_frontmatter(fm))
    errs.extend(_validate_body(skill["_body"]))
    if errs:
        return None, errs
    # normalized valid skill (strip private keys for caller if needed)
    return skill, []


def validate_skill_file(path: str | Path) -> Tuple[dict | None, List[str]]:
    p = Path(path)
    try:
        text = p.read_text(encoding="utf-8")
    except Exception as e:
        return None, [f"cannot read file: {e}"]
    return validate_skill_text(text, source=str(p))


def format_rejection(source: str, errs: List[str]) -> str:
    name = Path(source).name if source else source
    return f"Skill '{name}' rejected: " + "; ".join(errs)


def _resolve_custom_dir() -> Path | None:
    env = os.environ.get(CUSTOM_ENV, "").strip()
    if env:
        return Path(env)
    for cand in CUSTOM_DEFAULTS:
        # Use first candidate that exists or cwd default if none exist (so tests can mkdir)
        if cand.exists():
            return cand
    return CUSTOM_DEFAULTS[0]


def load_skills(curated_dir: str | Path | None = None,
                user_dir: str | Path | None = None,
                allowed_roster: set | None = None) -> Tuple[Dict[str, dict], Dict[str, str]]:
    """
    Load curated + custom markdown skills.

    Returns (skills_by_name, rejections) where rejections maps filename->chat-visible error.
    A valid skill's key is its slug name (lower).
    """
    if allowed_roster is not None:
        # For injection in tests - monkeypatch global set check via fm validation still uses
        # module ALLOWED_ROSTER_SET, so we patch both
        global ALLOWED_ROSTER_SET
        ALLOWED_ROSTER_SET = set(allowed_roster)

    curated_dir = Path(curated_dir) if curated_dir is not None else CURATED_DIR
    if user_dir is None:
        user_dir = _resolve_custom_dir()
    else:
        user_dir = Path(user_dir)

    skills: Dict[str, dict] = {}
    rejections: Dict[str, str] = {}

    # glob both dirs
    for base in (curated_dir, user_dir):
        if base is None or not Path(base).exists():
            continue
        for fp in sorted(Path(base).glob("*.md")):
            skill, errs = validate_skill_file(fp)
            if errs:
                rejections[str(fp)] = format_rejection(str(fp), errs)
            else:
                assert skill is not None
                # user dir wins over curated on same name (custom override)
                skills[skill["name"]] = skill

    return skills, rejections


def list_skill_names(skills: Dict[str, dict]) -> List[str]:
    return sorted(skills.keys())
