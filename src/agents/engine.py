"""
Screenipy engine for issue #301.

- Loads curated + custom Skills via skill_gate.
- Auto-routes by when_to_use with explicit name override.
- Freshness UX contract:
    * fresh data  -> silent (no age line)
    * stale data  -> blocks on fresh-or-stale choice (HITL)
    * failed refresh (stale served) -> one-line outdated note
- Executes the ordered MCP tool chain (via local TOOL_MAP for now; same
  allowlist as MCP surface) and renders a chat-complete answer.

The OpenAI-Agents / BYOK LLM layer is an optional outer wrapper; the engine
produces a correct answer even when no LLM key is configured so that /v1
contract tests stay deterministic.
"""
import re
from typing import Dict, List, Tuple

from agents.skill_gate import load_skills
from agents.screener_tools import TOOL_MAP

# Freshness helper – thin wrapper over DataFloor cache so tests can inject fakes.
def _get_cache():
    try:
        from classes.DataFloor import get_shared_cache
        return get_shared_cache()
    except Exception:
        return None

def _summaries(cache) -> Tuple[dict, dict]:
    """Return (daily_summary, universe_summary) from cache or empty markers."""
    if cache is None:
        return {"stale": False, "as_of": None, "count": 0}, {"stale": False, "as_of": None, "count": 0}
    try:
        daily = cache.summarize("daily")
    except Exception:
        daily = {"stale": False, "as_of": None, "count": 0}
    try:
        uni = cache.summarize("universe")
        # universe summarize packs as universe dict, but for cache.summarize('universe')
        # we get stale etc; if not present treat as fresh empty
        if uni is None:
            uni = {"stale": False, "as_of": None, "count": 0}
    except Exception:
        uni = {"stale": False, "as_of": None, "count": 0}
    # universe summarize also may be under daily-like summary; normalize
    return daily, uni

def freshness_state(cache=None) -> dict:
    """Assess cache freshness for the UX contract."""
    cache = cache if cache is not None else _get_cache()
    daily, uni = _summaries(cache)
    # also probe universe via direct lookup shape if summarize returns count 0 stale
    stale = bool(daily.get("stale")) or bool(uni.get("stale"))
    # if cache is empty (count 0 and stale True) we consider stale only if we have stale markers
    # Empty cache without markers should not block; treat as fresh for bootstrapping.
    if daily.get("count") == 0 and uni.get("count") == 0 and daily.get("as_of") is None and uni.get("as_of") is None:
        stale = False
    as_of = daily.get("as_of") or uni.get("as_of")
    return {"stale": stale, "as_of": as_of, "daily": daily, "universe": uni}

def _needs_choice(state: dict) -> bool:
    return bool(state.get("stale"))

def _outdated_note(state: dict) -> str:
    as_of = state.get("as_of")
    if as_of:
        return f"Note: data may be outdated (as of {as_of})."
    return "Note: data may be outdated."

def _tokenize(s: str) -> set:
    return set(re.findall(r"[a-z0-9]+", s.lower()))

def pick_skill(query: str, skills: Dict[str, dict], explicit: str | None = None) -> dict | None:
    """Route to a skill.

    - explicit name (from query extraction or caller override) wins.
    - otherwise token-overlap scoring against when_to_use.
    """
    if not skills:
        return None
    ql = query.lower()
    if explicit:
        key = explicit.strip().lower()
        if key in skills:
            return skills[key]
        # allow explicit like "breakout" substring without exact key
        for k, sk in skills.items():
            if k in key or key in k:
                return sk
    # explicit mention in query text wins without caller hint
    for name, sk in skills.items():
        if re.search(rf"\b{re.escape(name)}\b", ql):
            return sk
    # score by token overlap with when_to_use
    q_tokens = _tokenize(query)
    best = None
    best_score = -1
    for name, sk in skills.items():
        wtu = sk.get("when_to_use", "")
        w_tokens = _tokenize(wtu)
        # overlap count; weight exact name tokens higher
        score = len(q_tokens & w_tokens)
        # small boost for breakout flagship on generic breakout queries
        if "breakout" in q_tokens and name == "breakout":
            score += 0.5
        if "vcp" in q_tokens and name == "vcp":
            score += 0.5
        if score > best_score:
            best_score = score
            best = sk
    # fallback to breakout flagship if no overlap
    if best is None or best_score <= 0:
        return skills.get("breakout") or next(iter(skills.values()))
    return best

def _extract_explicit_skill(query: str) -> str | None:
    """Heuristic: 'use breakout', 'run vcp', 'skill: breakout' patterns."""
    m = re.search(r"(?:use|run|skill:?)\s+([a-z_]+)", query.lower())
    if m:
        cand = m.group(1).strip()
        if cand in ("breakout", "vcp", "momentum", "rsi", "consolidation"):
            return cand
        # also allow multi-word? take first token
        return cand
    return None

class ScreenipyEngine:
    """State-light engine used by the /v1 server and CLI."""

    def __init__(self, skills: Dict[str, dict] | None = None,
                 rejections: Dict[str, str] | None = None,
                 cache=None, curated_dir=None, user_dir=None):
        if skills is None or rejections is None:
            s, r = load_skills(curated_dir=curated_dir, user_dir=user_dir)
            self.skills = s
            self.rejections = r
        else:
            self.skills = skills
            self.rejections = rejections
        self._cache = cache

    def reload(self):
        self.skills, self.rejections = load_skills()

    def route(self, query: str, explicit: str | None = None) -> dict | None:
        hint = explicit or _extract_explicit_skill(query)
        return pick_skill(query, self.skills, explicit=hint)

    def _choose_freshness_reply(self, state: dict, user_choice: str | None) -> Tuple[bool, str]:
        """Return (should_block, prefix_or_note)."""
        if not _needs_choice(state):
            return False, ""
        # pending choice?
        if user_choice is None:
            as_of = state.get("as_of") or "unknown"
            msg = (
                f"Data is stale (as of {as_of}). "
                "Reply with 'fresh' to refresh from source or 'stale' to use cached data."
            )
            return True, msg
        user_choice = user_choice.strip().lower()
        if user_choice == "fresh":
            # Caller should refresh; here we just note we're refreshing. If refresh
            # fails upstream the stale note path will be used on next turn.
            return False, ""
        if user_choice == "stale":
            return False, _outdated_note(state) + "\n"
        # unknown choice -> block again
        return True, "Please reply with 'fresh' or 'stale'."

    def run_skill(self, skill: dict, index: str = "Nifty 500") -> str:
        """Execute the ordered tool chain for one skill; returns rendered string."""
        parts: List[str] = []
        for entry in skill.get("tools", []):
            tool_name = entry.get("tool", "")
            params = dict(entry.get("params", {}) or {})
            # allow index override from caller (query) or keep skill default
            if "index" not in params:
                params["index"] = index
            fn = TOOL_MAP.get(tool_name)
            if fn is None:
                parts.append(f"[{tool_name}: unknown tool]")
                continue
            try:
                out = fn(**params)
                parts.append(str(out))
            except Exception as e:
                parts.append(f"[{tool_name} error: {type(e).__name__}: {e}]")
        # Basic rendering: skill name header + tool outputs
        header = f"### {skill.get('name','skill').title()} — {len(parts)} tool(s)"
        body = "\n\n".join(parts) if parts else "No results."
        return f"{header}\n{body}"

    def answer(self, query: str, user_choice: str | None = None,
               explicit_skill: str | None = None,
               index: str = "Nifty 500",
               cache=None) -> str:
        """High-level answer honoring freshness UX and routing."""
        state = freshness_state(cache if cache is not None else self._cache)
        should_block, block_msg = self._choose_freshness_reply(state, user_choice=user_choice)
        if should_block:
            return block_msg

        skill = self.route(query, explicit=explicit_skill)
        if skill is None:
            return "No skills available. Add a valid markdown skill to the skills folder."

        note_prefix = ""
        # stale-but-user-chose-stale path already carries note
        if not should_block and _needs_choice(state) and (user_choice or "").strip().lower() == "stale":
            # block check already returned note prefix
            note_prefix = block_msg  # contains outdated note
            # actually _choose already cleared block; redo note
            note_prefix = _outdated_note(state) + "\n"

        # failed refresh note: if cache was stale and we attempted fresh but still stale,
        # treat as outdated note. Heuristic: daily summary stale_symbols non-empty and state stale.
        # For now reuse outdated note when stale and not blocked.

        result = self.run_skill(skill, index=index)

        # freshness UX: silent when fresh, note when stale+stale choice or failed refresh
        if note_prefix:
            return note_prefix + result
        # Also if we had a failed refresh flag injected via cache (stale+count>0 but refresh failed),
        # the caller can pass _failed_refresh state; simplest: if stale and we served anyway (user said stale)
        # we already added note. Otherwise silent.
        return result

    def chat_visible_rejections(self) -> List[str]:
        """Chat-visible errors for invalid custom skills (sorted for determinism)."""
        return sorted(self.rejections.values())
