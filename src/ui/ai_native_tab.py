"""
AI-Native Tab UI for Screeni-py Streamlit app.
Lightweight chat interface inspired by OpenWebUI — conversation history via
openai-agents SQLiteSession, scrollable chat window, persistent credentials.
"""
import os
import sys
import uuid
import streamlit as st
import streamlit.components.v1 as components

_src_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if _src_dir not in sys.path:
    sys.path.insert(0, _src_dir)

# ── CSS ────────────────────────────────────────────────────────────────────────
_CHAT_CSS = """
<style>
/* ── Chat bubbles ──────────────────────────────────────────────────────────── */
.chat-user {
    background: #1e3a5f;
    color: #e8f4fd;
    border-radius: 18px 18px 4px 18px;
    padding: 10px 16px;
    margin: 4px 0 4px 12%;
    display: inline-block;
    max-width: 88%;
    word-wrap: break-word;
    font-size: 0.93rem;
    line-height: 1.55;
}
.chat-row-user    { text-align: right; }
.chat-row-assistant { text-align: left; margin-bottom: 2px; }
.chat-label { font-size: 0.72rem; color: #666; margin-bottom: 1px; }

/* ── Thinking animation ────────────────────────────────────────────────────── */
.thinking-bar {
    display: flex; align-items: center; gap: 10px;
    padding: 10px 14px;
    background: #0f1117;
    border-left: 3px solid #f63366;
    border-radius: 6px;
    margin: 6px 0 2px 0;
    font-size: 0.88rem; color: #aaa;
}
.thinking-dots span {
    display: inline-block; width: 7px; height: 7px; margin: 0 2px;
    background: #f63366; border-radius: 50%;
    animation: tdot 1.2s infinite ease-in-out;
}
.thinking-dots span:nth-child(1) { animation-delay: 0s; }
.thinking-dots span:nth-child(2) { animation-delay: 0.2s; }
.thinking-dots span:nth-child(3) { animation-delay: 0.4s; }
@keyframes tdot {
    0%,80%,100% { transform: translateY(0); opacity: 0.35; }
    40%          { transform: translateY(-7px); opacity: 1; }
}
.scanning-bar {
    width: 100%; height: 2px; border-radius: 2px; margin: 2px 0 8px 0;
    background: linear-gradient(90deg, transparent, #f63366, transparent);
    background-size: 200% 100%;
    animation: scan 1.5s linear infinite;
}
@keyframes scan { 0% { background-position:-100% 0; } 100% { background-position:200% 0; } }

/* ── Step labels ───────────────────────────────────────────────────────────── */
.step-item {
    display: flex; align-items: center; gap: 7px;
    font-size: 0.8rem; color: #888; margin: 2px 0;
    animation: sfade 0.35s ease-in;
}
.step-item.done   { color: #2ecc71; }
.step-item.active { color: #ddd; }
@keyframes sfade { from { opacity:0; transform:translateY(3px); } to { opacity:1; } }
</style>
"""

_THINKING_HTML = """
<div class="thinking-bar">
    <div class="thinking-dots"><span></span><span></span><span></span></div>
    <span>Agent is analysing…</span>
</div>
<div class="scanning-bar"></div>
"""

# Keywords that suggest the user wants a fresh screen rather than follow-up chat
_SCREEN_KEYWORDS = {
    'screen', 'scan', 'find', 'show', 'list', 'top', 'best', 'breakout',
    'momentum', 'rsi', 'volume', 'vcp', 'consolidat', 'reversal', 'pattern',
    'nifty', 'sensex', 's&p', 'f&o', 'stock', 'trade', 'buy', 'sell',
    'today', 'tomorrow', 'week', 'month', 'rally', 'signal',
}


def _is_followup(query: str, history: list) -> bool:
    """
    Return True if this looks like a conversational follow-up that doesn't
    need fresh screener tool calls — i.e. there is prior assistant context
    AND the query contains no screener-trigger keywords.
    """
    if not history:
        return False
    # Must have at least one prior assistant reply
    has_prior = any(m['role'] == 'assistant' for m in history)
    if not has_prior:
        return False
    q_lower = query.lower()
    for kw in _SCREEN_KEYWORDS:
        if kw in q_lower:
            return False
    return True


# ── SQLiteSession DB path ──────────────────────────────────────────────────────
def _session_db_path() -> str:
    base = os.path.join(os.path.dirname(_src_dir), '.screenipy_sessions')
    os.makedirs(base, exist_ok=True)
    return os.path.join(base, 'chat_history.db')


def _get_or_create_agent_session():
    """Return (or create) a persistent SQLiteSession keyed per browser tab."""
    if 'agent_session_id' not in st.session_state:
        st.session_state['agent_session_id'] = str(uuid.uuid4())

    if '_agent_sql_session' not in st.session_state:
        try:
            import importlib as _il, site as _site
            _sp = [p for p in _site.getsitepackages() if os.path.exists(p)]
            _our = sys.modules.pop('agents', None)
            for p in _sp:
                sys.path.insert(0, p)
            try:
                _agents = _il.import_module('agents')
                SQLiteSession = _agents.SQLiteSession
            finally:
                for p in _sp:
                    try: sys.path.remove(p)
                    except ValueError: pass
                if _our is not None:
                    sys.modules['agents'] = _our
                else:
                    sys.modules.pop('agents', None)

            st.session_state['_agent_sql_session'] = SQLiteSession(
                session_id=st.session_state['agent_session_id'],
                db_path=_session_db_path(),
            )
        except Exception:
            st.session_state['_agent_sql_session'] = None

    return st.session_state.get('_agent_sql_session')


def _get_kite_session():
    from agents.kite_session import KiteMCPSession
    from agents.llm_config import load_kite_config
    kite_cfg = load_kite_config()
    if not kite_cfg.get('enabled') or not kite_cfg.get('url'):
        return None
    sess = st.session_state.get('_kite_mcp_session')
    if sess is None or not sess.is_connected:
        try:
            sess = KiteMCPSession(kite_cfg['url'])
            sess.start()
            st.session_state['_kite_mcp_session'] = sess
            st.session_state['_kite_authenticated'] = False
        except Exception:
            st.session_state.pop('_kite_mcp_session', None)
            return None
    return sess


# ── Main render ────────────────────────────────────────────────────────────────
def render():
    """Render the AI-Native chat tab."""

    if not st.session_state.get('_chat_css_injected'):
        st.markdown(_CHAT_CSS, unsafe_allow_html=True)
        st.session_state['_chat_css_injected'] = True

    if 'chat_history' not in st.session_state:
        st.session_state['chat_history'] = []

    # ── Load personas ──────────────────────────────────────────────────────────
    personas, persona_names = [], []
    try:
        from agents.agent_loader import AgentLoader
        loader = AgentLoader()
        personas = loader.load_all()
        persona_names = [p.get('name', 'Unknown') for p in personas]
    except Exception as e:
        st.warning(f"Could not load personas: {e}")

    # Read credentials from session_state only — no value= re-seed
    provider = st.session_state.get('ai_provider', 'openai')
    model    = st.session_state.get('ai_model', 'gpt-4o')
    api_key  = st.session_state.get('ai_api_key', '')
    base_url = st.session_state.get('ai_base_url', '')

    # ── Layout ────────────────────────────────────────────────────────────────
    col_side, col_chat = st.columns([1, 3], gap="medium")

    # ── LEFT sidebar ───────────────────────────────────────────────────────────
    with col_side:
        st.markdown("### 🤖 Persona")
        selected_persona = None
        if persona_names:
            default_name = 'MomentumAnalyst'
            default_idx  = persona_names.index(default_name) if default_name in persona_names else 0
            chosen_name  = st.selectbox(
                "Persona", options=persona_names, index=default_idx,
                key='ai_persona_selector', label_visibility='collapsed',
            )
            selected_persona = next((p for p in personas if p.get('name') == chosen_name), None)
            if selected_persona:
                st.caption(f"**{selected_persona.get('description', '')}**")
                st.caption(f"📊 {selected_persona.get('index', 'Nifty 500')}")
                for t in selected_persona.get('tools', []):
                    st.markdown(
                        f"<span style='font-size:0.78rem;color:#aaa'>• {t}</span>",
                        unsafe_allow_html=True,
                    )
        else:
            st.warning("No personas found.")

        st.divider()
        _render_kite_auth_compact()
        st.divider()

        if st.button("🗑️ Clear Chat", use_container_width=True, key='clear_chat_btn'):
            st.session_state['chat_history'] = []
            st.session_state.pop('_agent_sql_session', None)
            st.session_state.pop('agent_session_id', None)
            st.rerun()

        if not api_key:
            st.warning("No API key — go to **Configuration** tab.", icon="⚠️")

    # ── RIGHT: chat area ───────────────────────────────────────────────────────
    with col_chat:
        history = st.session_state['chat_history']

        # ── Scrollable chat window via fixed-height iframe ─────────────────────
        # Build the full message HTML, then render it via components.html so the
        # auto-scroll JS actually executes (st.markdown blocks scripts).
        chat_inner = ""
        if not history:
            chat_inner = (
                "<div style='text-align:center;padding:60px 0;color:#555;"
                "font-size:0.95rem;'>"
                "💬 Ask me anything — e.g. "
                "<em>\"Top 3 Nifty 50 breakouts for tomorrow\"</em>"
                "</div>"
            )

        # Render user bubbles inside the iframe; assistant replies below natively
        # (st.chat_message must be outside the iframe for full markdown support)
        for msg in history:
            if msg['role'] == 'user':
                safe = (msg['content']
                        .replace("&", "&amp;").replace("<", "&lt;")
                        .replace(">", "&gt;").replace("\n", "<br>"))
                chat_inner += (
                    f"<div class='chat-row-user'>"
                    f"<div class='chat-label'>You</div>"
                    f"<div class='chat-user'>{safe}</div>"
                    f"</div>"
                )

        scroll_html = f"""
<!DOCTYPE html>
<html>
<head>
<style>
  * {{ box-sizing: border-box; margin: 0; padding: 0; }}
  body {{ background: transparent; font-family: sans-serif; overflow: hidden; }}
  .chat-viewport {{
      height: 100%;
      overflow-y: auto;
      overflow-x: hidden;
      padding: 8px 4px;
      display: flex;
      flex-direction: column;
      gap: 4px;
      scrollbar-width: thin;
      scrollbar-color: #444 transparent;
  }}
  .chat-viewport::-webkit-scrollbar {{ width: 5px; }}
  .chat-viewport::-webkit-scrollbar-thumb {{ background:#444; border-radius:4px; }}
  .chat-user {{
      background:#1e3a5f; color:#e8f4fd;
      border-radius:18px 18px 4px 18px;
      padding:10px 16px; margin:4px 0 4px 12%;
      display:inline-block; max-width:88%;
      word-wrap:break-word; font-size:0.93rem; line-height:1.55;
  }}
  .chat-row-user {{ text-align:right; }}
  .chat-label {{ font-size:0.72rem; color:#666; margin-bottom:1px; }}
</style>
</head>
<body>
  <div class="chat-viewport" id="vp">
    {chat_inner}
  </div>
  <script>
    var vp = document.getElementById('vp');
    if (vp) vp.scrollTop = vp.scrollHeight;
  </script>
</body>
</html>"""

        # Dynamic height: 55px per message pair, min 200, max 520
        n_pairs = max(1, len([m for m in history if m['role'] == 'user']))
        iframe_h = min(520, max(200, n_pairs * 80 + 60))
        components.html(scroll_html, height=iframe_h, scrolling=False)

        # Render assistant messages natively (full markdown + tables)
        for msg in history:
            if msg['role'] == 'assistant':
                with st.chat_message("assistant", avatar="📈"):
                    st.markdown(msg['content'])

        st.divider()

        # ── Input — st.form so Enter submits ──────────────────────────────────
        with st.form(key='chat_form', clear_on_submit=True):
            fi_col, fb_col = st.columns([5, 1], gap="small")
            user_input = fi_col.text_input(
                "Message",
                placeholder="Ask about stocks, or follow up on previous results… (Enter to send)",
                label_visibility='collapsed',
            )
            submitted = fb_col.form_submit_button(
                "Send ▶", type='primary', use_container_width=True
            )

        # ── Handle submit ─────────────────────────────────────────────────────
        if submitted and user_input.strip():
            if not api_key:
                st.error("Configure your API key in the **Configuration** tab first.")
                return
            if not selected_persona:
                st.error("Select a persona.")
                return

            query = user_input.strip()
            st.session_state['chat_history'].append({'role': 'user', 'content': query})

            anim_slot  = st.empty()
            steps_slot = st.empty()
            anim_slot.markdown(_THINKING_HTML, unsafe_allow_html=True)

            def _step(text, done=False):
                icon = "✅" if done else "⏳"
                cls  = "done" if done else "active"
                steps_slot.markdown(
                    f'<div class="step-item {cls}"><span>{icon}</span>{text}</div>',
                    unsafe_allow_html=True,
                )

            result = ""
            try:
                # Determine whether to give the agent its screener tools or
                # run in tool-free mode for pure conversational follow-ups.
                followup = _is_followup(query, st.session_state['chat_history'][:-1])

                _step("Building agent…" if not followup else "Answering from context…")
                llm_cfg = {
                    'provider': provider, 'model': model,
                    'base_url': base_url or None, 'api_key': api_key,
                }
                from agents.screeni_agent import ScreeniAgent

                if followup:
                    # Clone persona config but strip tools so the agent answers
                    # purely from conversation history — no screener calls.
                    import copy
                    followup_persona = copy.deepcopy(selected_persona)
                    followup_persona['tools'] = []
                    agent_obj = ScreeniAgent(followup_persona, llm_cfg)
                else:
                    agent_obj = ScreeniAgent(selected_persona, llm_cfg)

                sql_session = _get_or_create_agent_session()

                if not followup:
                    _step("Running screener tools…")

                kite_sess = st.session_state.get('_kite_mcp_session')
                if (kite_sess and kite_sess.is_connected
                        and st.session_state.get('_kite_authenticated', False)):
                    try:
                        agent_obj._agent.mcp_servers = [kite_sess.server]
                        result = kite_sess.run_agent_query(
                            agent_obj._agent, query, sql_session=sql_session,
                        )
                    except Exception:
                        result = agent_obj.run_sync(query, session=sql_session)
                else:
                    result = agent_obj.run_sync(query, session=sql_session)

                _step("Done!", done=True)

            except Exception as e:
                result = f"⚠️ Error: {e}"
                _step(f"Failed: {e}")

            anim_slot.empty()
            steps_slot.empty()

            st.session_state['chat_history'].append({'role': 'assistant', 'content': result})

            if 'kite.zerodha.com/connect/login' in result:
                import re as _re
                m = _re.search(
                    r'https://kite\.zerodha\.com/connect/login[^\s\)\"\']+', result
                )
                if m:
                    st.session_state['_kite_pending_login_url'] = m.group(0)
                    st.session_state['_kite_authenticated'] = False

            st.rerun()


# ── Kite auth compact sidebar ──────────────────────────────────────────────────
def _render_kite_auth_compact():
    from agents.llm_config import load_kite_config
    kite_cfg = load_kite_config()
    if not kite_cfg.get('enabled'):
        return

    authenticated = st.session_state.get('_kite_authenticated', False)
    kite_sess     = st.session_state.get('_kite_mcp_session')
    session_alive = kite_sess is not None and kite_sess.is_connected

    st.markdown("### 🔑 Kite")

    if authenticated and session_alive:
        st.success("Live data ✅", icon="📡")
        if st.button("Disconnect", key='kite_disconnect_btn', use_container_width=True):
            from agents.kite_session import clear_session
            clear_session()
            st.session_state.pop('_kite_mcp_session', None)
            st.session_state['_kite_authenticated'] = False
            st.session_state.pop('_kite_pending_login_url', None)
            st.rerun()
        return

    pending_url = st.session_state.get('_kite_pending_login_url')
    if pending_url:
        st.markdown(f"[🔓 Login to Kite]({pending_url})")
        st.caption("Click link, log in, then:")
        c1, c2 = st.columns(2)
        if c1.button("✅ Done", key='kite_confirm_login', use_container_width=True):
            st.session_state['_kite_authenticated'] = True
            st.session_state.pop('_kite_pending_login_url', None)
            st.rerun()
        if c2.button("🔄", key='kite_refresh_link', use_container_width=True):
            st.session_state.pop('_kite_pending_login_url', None)
            st.session_state.pop('_kite_mcp_session', None)
            st.rerun()
        return

    st.caption("Real-time quotes & orders")
    if st.button("🔗 Connect", key='kite_connect_btn', use_container_width=True):
        with st.spinner("Connecting…"):
            try:
                sess = _get_kite_session()
                if sess is None:
                    st.error("Connect failed.")
                    return
                login_url_text = sess.get_login_url()
                import re
                m = re.search(
                    r'https://kite\.zerodha\.com/connect/login[^\s\)\"\']+',
                    login_url_text,
                )
                st.session_state['_kite_pending_login_url'] = (
                    m.group(0) if m else login_url_text
                )
                st.rerun()
            except Exception as e:
                st.error(f"Kite error: {e}")
