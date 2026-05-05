"""
AI-Native Tab UI for Screeni-py Streamlit app.
Provides an interactive AI-powered stock screening interface with persona selection,
LLM configuration (in Configure tab), and streaming agent output.
"""
import os
import sys
import streamlit as st

_src_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if _src_dir not in sys.path:
    sys.path.insert(0, _src_dir)


def _get_kite_session():
    """
    Return (or create) a persistent KiteMCPSession stored in st.session_state.
    The session object lives across Streamlit reruns so the MCP connection —
    and the Kite login session_id — stays alive while the user authenticates.
    """
    from agents.kite_session import KiteMCPSession
    from agents.llm_config import load_kite_config

    kite_cfg = load_kite_config()
    if not kite_cfg.get('enabled') or not kite_cfg.get('url'):
        return None

    sess: KiteMCPSession = st.session_state.get('_kite_mcp_session')
    if sess is None or not sess.is_connected:
        try:
            sess = KiteMCPSession(kite_cfg['url'])
            sess.start()
            st.session_state['_kite_mcp_session'] = sess
            st.session_state['_kite_authenticated'] = False
        except Exception as e:
            st.session_state.pop('_kite_mcp_session', None)
            return None
    return sess


def render():
    """
    Render the AI-Native screening tab.

    UX:
    - Persona selector (left) shows description/index/tools at a glance
    - Single query box with one "Run" button — the selected persona's instructions
      are automatically injected as system context; the user just types what they want
    - Agent response rendered as markdown; structured tables auto-extracted
    - Kite MCP section: persistent session with login URL kept alive for auth
    """
    st.header("🤖 AI-Native Screening")
    st.caption(
        "Select a persona and describe what you want to screen for. "
        "The persona's strategy is used automatically as context. "
        "Configure your LLM in the **Configuration** tab."
    )

    # ── Load personas ──────────────────────────────────────────────────────────
    personas = []
    persona_names = []
    try:
        from agents.agent_loader import AgentLoader
        loader = AgentLoader()
        personas = loader.load_all()
        persona_names = [p.get('name', 'Unknown') for p in personas]
    except Exception as e:
        st.warning(f"Could not load personas: {e}")

    # ── Read LLM config from session_state ────────────────────────────────────
    provider = st.session_state.get('ai_provider', 'openai')
    model = st.session_state.get('ai_model', 'gpt-4o')
    api_key = st.session_state.get('ai_api_key', os.environ.get('SCREENIPY_API_KEY', ''))
    base_url = st.session_state.get('ai_base_url', None)

    if not api_key:
        st.info(
            "No API key configured. Go to the **Configuration** tab → LLM Configuration to set it up.",
            icon="ℹ️",
        )

    # ── Kite MCP auth panel ────────────────────────────────────────────────────
    _render_kite_auth_panel()

    st.divider()

    # ── Layout: persona panel (left) | query + output (right) ─────────────────
    col_persona, col_main = st.columns([1, 2])

    with col_persona:
        st.markdown("#### Persona")
        selected_persona = None
        if persona_names:
            default_name = 'MomentumAnalyst'
            default_idx = persona_names.index(default_name) if default_name in persona_names else 0
            selected_persona_name = st.selectbox(
                "Select",
                options=persona_names,
                index=default_idx,
                key='ai_persona_selector',
                label_visibility='collapsed',
            )
            selected_persona = next(
                (p for p in personas if p.get('name') == selected_persona_name), None
            )
            if selected_persona:
                st.markdown(f"**{selected_persona.get('description', '')}**")
                st.caption(f"Index: {selected_persona.get('index', 'Nifty 500')}")
                tools_list = selected_persona.get('tools', [])
                if tools_list:
                    for t in tools_list:
                        st.markdown(f"- `{t}`")
        else:
            st.warning("No personas found. Check the **Configuration** tab to create one.")

    with col_main:
        st.markdown("#### What do you want to screen for?")
        query = st.text_area(
            "Query",
            placeholder=(
                "e.g. 'Show me Nifty 500 stocks breaking out today with high volume'\n"
                "or 'Find top 10 momentum setups with RSI between 55-70'\n\n"
                "Leave blank to run the persona's default strategy."
            ),
            height=140,
            key='ai_query',
            label_visibility='collapsed',
        )

        run_btn = st.button(
            "🚀 Run",
            type='primary',
            use_container_width=True,
            disabled=(selected_persona is None),
            key='ai_run_btn',
        )

    # ── Output ────────────────────────────────────────────────────────────────
    st.divider()

    if run_btn:
        if not api_key:
            st.error("Please configure your API key in the **Configuration** tab → LLM Configuration.")
            return
        if selected_persona is None:
            st.error("Please select a persona.")
            return

        # Build the final query
        if query.strip():
            final_query = query.strip()
        else:
            final_query = (
                f"Run your complete {selected_persona.get('name')} strategy for "
                f"{selected_persona.get('index', 'Nifty 500')}. "
                f"Identify the top opportunities and explain each setup briefly with entry, stop, and target."
            )

        st.markdown(f"**Running:** `{final_query[:140]}{'...' if len(final_query) > 140 else ''}`")

        with st.spinner("Agent is thinking..."):
            try:
                llm_cfg = {
                    'provider': provider,
                    'model': model,
                    'base_url': base_url,
                    'api_key': api_key,
                }
                from agents.screeni_agent import ScreeniAgent
                agent = ScreeniAgent(selected_persona, llm_cfg)

                # If Kite session is live and authenticated, run query inside it
                # (shares the authenticated MCP connection)
                kite_sess = st.session_state.get('_kite_mcp_session')
                if (
                    kite_sess is not None
                    and kite_sess.is_connected
                    and st.session_state.get('_kite_authenticated', False)
                ):
                    try:
                        agent._agent.mcp_servers = [kite_sess.server]
                        result = kite_sess.run_agent_query(agent._agent, final_query)
                    except Exception:
                        # Fall back to normal run_sync if session query fails
                        result = agent.run_sync(final_query)
                else:
                    result = agent.run_sync(final_query)

                st.markdown("### Results")
                st.markdown(result)

                # Check if the agent's response is asking for Kite login
                if 'kite.zerodha.com/connect/login' in result:
                    st.session_state['_kite_authenticated'] = False
                    import re
                    url_match = re.search(
                        r'https://kite\.zerodha\.com/connect/login[^\s\)\"\']+', result
                    )
                    if url_match:
                        st.session_state['_kite_pending_login_url'] = url_match.group(0)
                        st.rerun()

                _try_show_structured_results(result)

            except ImportError as e:
                st.error(f"Missing dependency: {e}")
                st.info("Install with: `pip install openai-agents`")
            except Exception as e:
                err = str(e)
                if 'api_key' in err.lower() or 'authentication' in err.lower():
                    st.error("API key error. Please check your API key in the Configuration tab.")
                else:
                    st.error(f"Agent error: {e}")
                st.exception(e)


def _render_kite_auth_panel():
    """
    Render the Kite MCP authentication status panel.
    Manages the two-step login flow:
      1. Connect MCP → show login URL (session stays alive)
      2. User logs in → marks authenticated → next Run uses live session
    """
    from agents.llm_config import load_kite_config
    kite_cfg = load_kite_config()
    if not kite_cfg.get('enabled'):
        return

    authenticated = st.session_state.get('_kite_authenticated', False)
    kite_sess = st.session_state.get('_kite_mcp_session')
    session_alive = kite_sess is not None and kite_sess.is_connected

    with st.expander("🔑 Kite Live Data (Zerodha)", expanded=not authenticated):
        if authenticated and session_alive:
            col1, col2 = st.columns([3, 1])
            col1.success("Connected to Kite — live market data is available.", icon="✅")
            if col2.button("Disconnect", key='kite_disconnect_btn'):
                from agents.kite_session import clear_session
                clear_session()
                st.session_state.pop('_kite_mcp_session', None)
                st.session_state['_kite_authenticated'] = False
                st.session_state.pop('_kite_pending_login_url', None)
                st.rerun()
            return

        # Pending login URL already fetched — show it until user confirms
        pending_url = st.session_state.get('_kite_pending_login_url')
        if pending_url:
            st.warning(
                "**AI Disclaimer:** AI systems are unpredictable and non-deterministic. "
                "By continuing, you agree to interact with your Zerodha account via AI at your own risk.",
                icon="⚠️",
            )
            st.markdown(
                f"**Step 2:** [Click here to log in to Kite]({pending_url})\n\n"
                "After completing login in your browser, click **I've logged in** below."
            )
            col1, col2 = st.columns([2, 1])
            if col1.button("✅ I've logged in", type='primary', key='kite_confirm_login'):
                st.session_state['_kite_authenticated'] = True
                st.session_state.pop('_kite_pending_login_url', None)
                st.rerun()
            if col2.button("🔄 Get new link", key='kite_refresh_link'):
                st.session_state.pop('_kite_pending_login_url', None)
                st.session_state.pop('_kite_mcp_session', None)
                st.rerun()
            return

        # No session / not authenticated — offer to connect
        st.info(
            "Connect to Kite for real-time quotes, portfolio data, and order placement via AI.",
            icon="ℹ️",
        )
        if st.button("🔗 Connect Kite", key='kite_connect_btn'):
            with st.spinner("Connecting to Kite MCP..."):
                try:
                    sess = _get_kite_session()
                    if sess is None:
                        st.error("Could not connect to Kite MCP. Check your config.")
                        return
                    login_url_text = sess.get_login_url()
                    import re
                    url_match = re.search(
                        r'https://kite\.zerodha\.com/connect/login[^\s\)\"\']+',
                        login_url_text
                    )
                    if url_match:
                        st.session_state['_kite_pending_login_url'] = url_match.group(0)
                    else:
                        st.session_state['_kite_pending_login_url'] = login_url_text
                    st.rerun()
                except Exception as e:
                    st.error(f"Kite connect failed: {e}")


def _try_show_structured_results(result: str):
    """
    Attempt to parse agent output as a dataframe.
    Looks for markdown tables or JSON arrays in the response.
    """
    import re
    import json
    import pandas as pd

    # Try JSON array
    json_match = re.search(r'\[(\s*\{.*?\}\s*,?\s*)+\]', result, re.DOTALL)
    if json_match:
        try:
            data = json.loads(json_match.group(0))
            df = pd.DataFrame(data)
            st.markdown("### Structured Results")
            st.dataframe(df, use_container_width=True)
            return
        except Exception:
            pass

    # Try markdown table
    lines = result.split('\n')
    table_lines = [l for l in lines if '|' in l and l.strip().startswith('|')]
    if len(table_lines) >= 3:
        try:
            headers = [h.strip() for h in table_lines[0].split('|') if h.strip()]
            data_rows = []
            for row in table_lines[2:]:
                cells = [c.strip() for c in row.split('|') if c.strip()]
                if cells:
                    data_rows.append(cells)
            if data_rows:
                df = pd.DataFrame(data_rows, columns=headers[:len(data_rows[0])])
                st.markdown("### Structured Results")
                st.dataframe(df, use_container_width=True)
        except Exception:
            pass
    """
    Render the AI-Native screening tab.

    UX:
    - Persona selector (left) shows description/index/tools at a glance
    - Single query box with one "Run" button — the selected persona's instructions
      are automatically injected as system context; the user just types what they want
    - Agent response rendered as markdown; structured tables auto-extracted
    """
    st.header("🤖 AI-Native Screening")
    st.caption(
        "Select a persona and describe what you want to screen for. "
        "The persona's strategy is used automatically as context. "
        "Configure your LLM in the **Configuration** tab."
    )

    # ── Load personas ──────────────────────────────────────────────────────────
    personas = []
    persona_names = []
    try:
        from agents.agent_loader import AgentLoader
        loader = AgentLoader()
        personas = loader.load_all()
        persona_names = [p.get('name', 'Unknown') for p in personas]
    except Exception as e:
        st.warning(f"Could not load personas: {e}")

    # ── Read LLM config from session_state ────────────────────────────────────
    provider = st.session_state.get('ai_provider', 'openai')
    model = st.session_state.get('ai_model', 'gpt-4o')
    api_key = st.session_state.get('ai_api_key', os.environ.get('SCREENIPY_API_KEY', ''))
    base_url = st.session_state.get('ai_base_url', None)

    if not api_key:
        st.info(
            "No API key configured. Go to the **Configuration** tab → LLM Configuration to set it up.",
            icon="ℹ️",
        )

    # ── Layout: persona panel (left) | query + output (right) ─────────────────
    col_persona, col_main = st.columns([1, 2])

    with col_persona:
        st.markdown("#### Persona")
        selected_persona = None
        if persona_names:
            default_name = 'MomentumAnalyst'
            default_idx = persona_names.index(default_name) if default_name in persona_names else 0
            selected_persona_name = st.selectbox(
                "Select",
                options=persona_names,
                index=default_idx,
                key='ai_persona_selector',
                label_visibility='collapsed',
            )
            selected_persona = next(
                (p for p in personas if p.get('name') == selected_persona_name), None
            )
            if selected_persona:
                st.markdown(f"**{selected_persona.get('description', '')}**")
                st.caption(f"Index: {selected_persona.get('index', 'Nifty 500')}")
                tools_list = selected_persona.get('tools', [])
                if tools_list:
                    for t in tools_list:
                        st.markdown(f"- `{t}`")
        else:
            st.warning("No personas found. Check the **Configuration** tab to create one.")

    with col_main:
        st.markdown("#### What do you want to screen for?")
        query = st.text_area(
            "Query",
            placeholder=(
                "e.g. 'Show me Nifty 500 stocks breaking out today with high volume'\n"
                "or 'Find top 10 momentum setups with RSI between 55-70'\n\n"
                "Leave blank to run the persona's default strategy."
            ),
            height=140,
            key='ai_query',
            label_visibility='collapsed',
        )

        run_btn = st.button(
            "🚀 Run",
            type='primary',
            use_container_width=True,
            disabled=(selected_persona is None),
            key='ai_run_btn',
        )

    # ── Output ────────────────────────────────────────────────────────────────
    st.divider()

    if run_btn:
        if not api_key:
            st.error("Please configure your API key in the **Configuration** tab → LLM Configuration.")
            return
        if selected_persona is None:
            st.error("Please select a persona.")
            return

        # Build the final query: use user text if provided, else ask persona to run its default strategy
        if query.strip():
            final_query = query.strip()
        else:
            final_query = (
                f"Run your complete {selected_persona.get('name')} strategy for "
                f"{selected_persona.get('index', 'Nifty 500')}. "
                f"Identify the top opportunities and explain each setup briefly with entry, stop, and target."
            )

        st.markdown(f"**Running:** `{final_query[:140]}{'...' if len(final_query) > 140 else ''}`")

        with st.spinner("Agent is thinking..."):
            try:
                llm_cfg = {
                    'provider': provider,
                    'model': model,
                    'base_url': base_url,
                    'api_key': api_key,
                }
                from agents.screeni_agent import ScreeniAgent
                agent = ScreeniAgent(selected_persona, llm_cfg)
                result = agent.run_sync(final_query)

                st.markdown("### Results")
                st.markdown(result)

                _try_show_structured_results(result)

            except ImportError as e:
                st.error(f"Missing dependency: {e}")
                st.info("Install with: `pip install openai-agents`")
            except Exception as e:
                err = str(e)
                if 'api_key' in err.lower() or 'authentication' in err.lower():
                    st.error("API key error. Please check your API key in the Configuration tab.")
                else:
                    st.error(f"Agent error: {e}")
                st.exception(e)


def _try_show_structured_results(result: str):
    """
    Attempt to parse agent output as a dataframe.
    Looks for markdown tables or JSON arrays in the response.
    """
    import re
    import json
    import pandas as pd

    # Try JSON array
    json_match = re.search(r'\[(\s*\{.*?\}\s*,?\s*)+\]', result, re.DOTALL)
    if json_match:
        try:
            data = json.loads(json_match.group(0))
            df = pd.DataFrame(data)
            st.markdown("### Structured Results")
            st.dataframe(df, use_container_width=True)
            return
        except Exception:
            pass

    # Try markdown table
    lines = result.split('\n')
    table_lines = [l for l in lines if '|' in l and l.strip().startswith('|')]
    if len(table_lines) >= 3:
        try:
            headers = [h.strip() for h in table_lines[0].split('|') if h.strip()]
            data_rows = []
            for row in table_lines[2:]:
                cells = [c.strip() for c in row.split('|') if c.strip()]
                if cells:
                    data_rows.append(cells)
            if data_rows:
                df = pd.DataFrame(data_rows, columns=headers[:len(data_rows[0])])
                st.markdown("### Structured Results")
                st.dataframe(df, use_container_width=True)
        except Exception:
            pass
