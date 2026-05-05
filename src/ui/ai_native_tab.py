"""
AI-Native Tab UI for Screeni-py Streamlit app.
Provides an interactive AI-powered stock screening interface with persona selection,
LLM configuration, and streaming agent output.
"""
import os
import sys
import streamlit as st

_src_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if _src_dir not in sys.path:
    sys.path.insert(0, _src_dir)


def render():
    """
    Render the AI-Native screening tab in the Streamlit UI.
    
    Features:
    - LLM provider and model configuration sidebar
    - Persona selector dropdown from YAML personas
    - Free-text query input or "Run selected persona" button
    - Streaming agent response output
    - Results table if structured output is available
    """
    st.header("🤖 AI-Native Screening")
    st.markdown(
        "Use AI-powered agent personas to screen for stocks with natural language queries."
    )

    # ---- Load personas ----
    personas = []
    persona_names = []
    try:
        from agents.agent_loader import AgentLoader
        loader = AgentLoader()
        personas = loader.load_all()
        persona_names = [p.get('name', 'Unknown') for p in personas]
    except Exception as e:
        st.warning(f"Could not load personas: {e}")

    # ---- Sidebar: LLM config ----
    with st.sidebar:
        st.markdown("### 🧠 LLM Configuration")
        provider = st.selectbox(
            "Provider",
            options=['openai', 'anthropic', 'openai-compatible'],
            key='ai_provider',
            help="Select your LLM provider",
        )
        model = st.text_input(
            "Model",
            value='gpt-4o' if provider == 'openai' else ('claude-sonnet-4-5' if provider == 'anthropic' else 'gpt-4o'),
            key='ai_model',
        )
        api_key = st.text_input(
            "API Key",
            type="password",
            value=os.environ.get('SCREENIPY_API_KEY', ''),
            key='ai_api_key',
            help="Your API key for the selected provider",
        )
        base_url = None
        if provider == 'openai-compatible':
            base_url = st.text_input(
                "Base URL",
                value='http://localhost:11434/v1',
                key='ai_base_url',
                help="Base URL for OpenAI-compatible endpoint (e.g., Ollama)",
            )

    # ---- Main panel ----
    col1, col2 = st.columns([1, 2])

    with col1:
        if persona_names:
            selected_persona_name = st.selectbox(
                "🎭 Select Persona",
                options=persona_names,
                key='ai_persona_selector',
            )
            selected_persona = next(
                (p for p in personas if p.get('name') == selected_persona_name), None
            )
            if selected_persona:
                st.markdown(f"**Description:** {selected_persona.get('description', 'N/A')}")
                st.markdown(f"**Default Index:** {selected_persona.get('index', 'Nifty 500')}")
                tools_list = selected_persona.get('tools', [])
                if tools_list:
                    st.markdown(f"**Tools:** {', '.join(tools_list)}")
        else:
            st.warning("No personas found. Check `src/agents/personas/` directory.")
            selected_persona = None

    with col2:
        query = st.text_area(
            "💬 What do you want to screen for?",
            placeholder=(
                "e.g. 'Find the top 10 Nifty 500 stocks showing breakout with high volume today' "
                "or leave blank and click 'Run Persona' to use the persona's default strategy."
            ),
            height=120,
            key='ai_query',
        )

        run_col, persona_run_col = st.columns([1, 1])
        run_query_btn = run_col.button(
            "🚀 Run Query",
            use_container_width=True,
            disabled=(not selected_persona or not query.strip()),
        )
        run_persona_btn = persona_run_col.button(
            "🎭 Run Persona Strategy",
            use_container_width=True,
            disabled=(not selected_persona),
        )

    # ---- Output area ----
    st.markdown("---")
    output_placeholder = st.empty()
    results_placeholder = st.empty()

    if run_query_btn or run_persona_btn:
        if not api_key:
            st.error("⚠️ Please enter your API key in the sidebar.")
            return

        if selected_persona is None:
            st.error("⚠️ Please select a persona.")
            return

        # Build query
        if run_persona_btn or not query.strip():
            final_query = (
                f"Run your complete {selected_persona.get('name')} strategy for "
                f"{selected_persona.get('index', 'Nifty 500')}. "
                f"Identify the top 10 opportunities and explain each setup briefly with entry, stop, and target."
            )
        else:
            final_query = query.strip()

        with output_placeholder.container():
            st.markdown(f"**Running:** `{final_query[:120]}{'...' if len(final_query) > 120 else ''}`")
            with st.spinner("🤖 Agent is thinking..."):
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

                    st.markdown("### 📊 Agent Response")
                    st.markdown(result)

                    # Try to parse structured output as dataframe
                    _try_show_structured_results(result, results_placeholder)

                except ImportError as e:
                    st.error(f"❌ Missing dependency: {e}")
                    st.info("Install with: `pip install openai-agents`")
                except Exception as e:
                    error_msg = str(e)
                    if 'api_key' in error_msg.lower() or 'authentication' in error_msg.lower():
                        st.error("❌ API key error. Please check your API key.")
                    else:
                        st.error(f"❌ Agent error: {e}")
                    st.exception(e)


def _try_show_structured_results(result: str, placeholder):
    """
    Attempt to parse agent output as structured data and show as dataframe.
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
            with placeholder.container():
                st.markdown("### 📋 Structured Results")
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
                with placeholder.container():
                    st.markdown("### 📋 Structured Results")
                    st.dataframe(df, use_container_width=True)
        except Exception:
            pass
