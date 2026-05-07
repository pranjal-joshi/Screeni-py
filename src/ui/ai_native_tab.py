"""
AI-Native Tab UI for Screeni-py Streamlit app.
Lightweight chat interface inspired by OpenWebUI — conversation history via
openai-agents SQLiteSession, scrollable chat window, persistent credentials.
"""
import os
import sys
import uuid
import streamlit as st

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


def _check_credential_source() -> str:
    """Check where LLM credentials came from: browser localStorage, YAML, or env."""
    import os as _os
    provider = st.session_state.get('ai_provider', '')
    model = st.session_state.get('ai_model', '')
    api_key = st.session_state.get('ai_api_key', '')

    env_key = _os.environ.get('SCREENIPY_API_KEY', '')
    if api_key and api_key != env_key:
        key_source = "browser localStorage / manual input"
    elif api_key:
        key_source = "env var SCREENIPY_API_KEY"
    else:
        key_source = "not set"

    masked_key = f"{api_key[:6]}...{api_key[-4:]}" if len(api_key) > 10 else ("(not set)" if not api_key else "***")
    return (
        f"🔑 Credentials — Provider: **{provider}**, "
        f"Model: **{model}**, "
        f"API Key: `{masked_key}` (source: {key_source})"
    )


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

    # ── RIGHT: chat area — scrollable viewport + pinned footer form ────────────
    with col_chat:
        history = st.session_state['chat_history']

        # ── Build full conversation HTML for iframe ────────────────────────────
        def _md_to_html(text: str) -> str:
            """Minimal markdown-to-HTML for rendering assistant messages in iframe."""
            import re as _re2

            # Extract code blocks first to protect them from later transforms
            code_blocks = []
            def _save_code_block(m):
                code_blocks.append(m.group(1))
                return f"\x00CODEBLOCK{len(code_blocks)-1}\x00"
            text = _re2.sub(r'```(?:\w*)\n?(.*?)```', _save_code_block, text, flags=_re2.DOTALL)

            safe = (text
                    .replace("&", "&amp;").replace("<", "&lt;")
                    .replace(">", "&gt;"))
            # Inline code
            safe = _re2.sub(r'`([^`]+)`', r'<code style="background:#222;color:#ddd;padding:1px 5px;border-radius:3px;font-size:0.85em;">\1</code>', safe)
            # Bold
            safe = _re2.sub(r'\*\*(.+?)\*\*', r'<strong>\1</strong>', safe)
            # Italic
            safe = _re2.sub(r'\*(.+?)\*', r'<em>\1</em>', safe)
            # Tables: convert pipe tables to HTML
            lines = safe.split("\n")
            result_lines = []
            in_table = False
            table_rows = []
            for line in lines:
                stripped = line.strip()
                if stripped.startswith("|") and stripped.endswith("|"):
                    cells = [c.strip() for c in stripped.split("|")[1:-1]]
                    if all(c.replace("-", "") == "" for c in cells):
                        continue
                    if not in_table:
                        in_table = True
                        th = "".join(f"<th style='border:1px solid #444;padding:5px 10px;background:#1a1a2e;color:#f63366;text-align:left;'>{c}</th>" for c in cells)
                        table_rows.append(f"<tr>{th}</tr>")
                    else:
                        td = "".join(f"<td style='border:1px solid #333;padding:5px 10px;'>{c}</td>" for c in cells)
                        table_rows.append(f"<tr>{td}</tr>")
                else:
                    if in_table:
                        result_lines.append(f"<table style='border-collapse:collapse;margin:6px 0;font-size:0.85rem;'>{''.join(table_rows)}</table>")
                        table_rows = []
                        in_table = False
                    result_lines.append(stripped if stripped else "<br>")
            if in_table:
                result_lines.append(f"<table style='border-collapse:collapse;margin:6px 0;font-size:0.85rem;'>{''.join(table_rows)}</table>")
            safe = "".join(result_lines)

            # Restore code blocks
            for i, block in enumerate(code_blocks):
                escaped = (block.replace("&", "&amp;").replace("<", "&lt;")
                                .replace(">", "&gt;"))
                safe = safe.replace(
                    f"\x00CODEBLOCK{i}\x00",
                    f"<pre style='background:#1a1a2e;color:#0f0;padding:8px 12px;border-radius:6px;font-size:0.85rem;overflow-x:auto;'>{escaped}</pre>",
                )
            return safe

        chat_inner = ""
        if not history:
            chat_inner = (
                "<div style='text-align:center;padding:60px 0;color:#888;"
                "font-size:0.95rem;'>"
                "💬 Ask me anything — e.g. "
                "<em>\"Top 3 Nifty 50 breakouts for tomorrow\"</em>"
                "</div>"
            )

        for msg in history:
            if msg['role'] == 'user':
                safe = (msg['content']
                        .replace("&", "&amp;").replace("<", "&lt;")
                        .replace(">", "&gt;").replace("\n", "<br>"))
                chat_inner += (
                    "<div class='chat-row-user'>"
                    "<div class='chat-label'>You</div>"
                    f"<div class='chat-user'>{safe}</div>"
                    "</div>"
                )
            else:
                html = _md_to_html(msg['content'])
                chat_inner += (
                    "<div class='chat-row-assistant'>"
                    "<div class='chat-label'>Screeni</div>"
                    f"<div class='chat-assistant'>{html}</div>"
                    "</div>"
                )

        # ── Scrollable messages iframe via srcdoc (height via CSS calc) ────────
        import html as _html_mod
        _safe_srcdoc = _html_mod.escape(f"""<!DOCTYPE html>
<html>
<head>
<style>
  * {{ box-sizing: border-box; margin: 0; padding: 0; }}
  html, body {{
      height: 100%;
      overflow: hidden;
      background: #0e1117;
      color: #fafafa;
      font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', sans-serif;
  }}
  #viewport {{
      height: 100%;
      overflow-y: auto;
      overflow-x: hidden;
      padding: 12px 8px 16px 8px;
      display: flex;
      flex-direction: column;
      gap: 6px;
      scrollbar-width: thin;
      scrollbar-color: #444 transparent;
  }}
  #viewport::-webkit-scrollbar {{ width: 5px; }}
  #viewport::-webkit-scrollbar-thumb {{ background:#444; border-radius:4px; }}
  .chat-user {{
      background:#1e3a5f; color:#e8f4fd;
      border-radius:18px 18px 4px 18px;
      padding:10px 16px; margin:4px 0 4px 12%;
      display:inline-block; max-width:88%;
      word-wrap:break-word; font-size:0.93rem; line-height:1.55;
      align-self: flex-end;
  }}
  .chat-assistant {{
      color:#fafafa; padding:6px 14px; margin:4px 0 4px 2%;
      display:inline-block; max-width:92%;
      word-wrap:break-word; font-size:0.9rem; line-height:1.6;
      align-self: flex-start;
  }}
  .chat-row-user {{ text-align:right; }}
  .chat-row-assistant {{ text-align:left; margin-bottom:2px; }}
  .chat-label {{ font-size:0.72rem; color:#888; margin-bottom:1px; }}
  .chat-assistant pre {{ white-space:pre-wrap; word-break:break-word; background:#1a1a2e;color:#0f0;padding:6px 10px;border-radius:6px;font-size:0.85rem; }}
  .chat-assistant code {{ word-break:break-word; background:#222;color:#ddd;padding:1px 5px;border-radius:3px;font-size:0.85em; }}
</style>
</head>
<body>
  <div id="viewport">
    {chat_inner}
  </div>
  <script>
    var vp = document.getElementById('viewport');
    if (vp) {{
      requestAnimationFrame(function() {{
        vp.scrollTop = vp.scrollHeight;
      }});
    }}
  </script>
</body>
</html>""")

        # Inject iframe via st.markdown — uses dvh (dynamic viewport height) for
        # responsive sizing across desktop and mobile browsers.
        st.markdown(
            f'<iframe class="chat-iframe" srcdoc="{_safe_srcdoc}" '
            'style="width:100%;height:calc(100dvh - 220px);min-height:350px;'
            'border:none;border-radius:8px;background:#0e1117;" '
            'sandbox="allow-scripts"></iframe>',
            unsafe_allow_html=True,
        )

        # ── Input — st.form so Enter submits (pinned at footer) ───────────────
        with st.form(key='chat_form', clear_on_submit=True):
            fi_col, fb_col = st.columns([5, 1], gap="small")
            user_input = fi_col.text_input(
                "Message",
                placeholder="Ask about stocks, or follow up on previous results… (Enter to send)",
                label_visibility='collapsed',
            )
            submitted = fb_col.form_submit_button(
                "Send", type='primary', use_container_width=True
            )

        # ── Handle submit ─────────────────────────────────────────────────────
        if submitted and user_input.strip():
            if not api_key:
                st.error("Configure your API key in the **Configuration** tab first.")
                return
            if not selected_persona:
                st.error("Select a persona.")
                return

            # Verify credential source (localStorage vs env var)
            cred_source = _check_credential_source()
            if cred_source:
                st.caption(cred_source)

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
