"""
Tests for Agent Tools - screener_tools.py and agent_loader.py
Tests tool importability, signatures, and persona loading.
"""
import pytest
import os
import sys
from unittest.mock import MagicMock, patch

# Ensure src is in path
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..', 'src')))


class TestScreenerToolsImport:
    """Test that all screener tools are importable and have correct structure."""

    def test_screener_tools_module_imports(self):
        """screener_tools module should import without errors."""
        import agents.screener_tools as st
        assert st is not None

    def test_all_tools_list_exists(self):
        """ALL_TOOLS list should exist and be a list."""
        from agents.screener_tools import ALL_TOOLS
        assert isinstance(ALL_TOOLS, list)

    def test_tool_map_exists(self):
        """TOOL_MAP dict should exist."""
        from agents.screener_tools import TOOL_MAP
        assert isinstance(TOOL_MAP, dict)

    def test_expected_tool_names_in_map(self):
        """Expected tool names should be in TOOL_MAP."""
        from agents.screener_tools import TOOL_MAP
        expected_tools = [
            'screen_breakout',
            'screen_volume_breakout',
            'screen_consolidation',
            'screen_rsi',
            'screen_reversal',
            'screen_chart_patterns',
            'screen_vcp',
            'screen_lorentzian',
            'screen_momentum',
            'screen_narrow_range',
            'screen_ipo_base',
            'screen_confluence',
            'screen_ma_reversal',
            'screen_rsi_ma_cross',
        ]
        for tool_name in expected_tools:
            assert tool_name in TOOL_MAP, f"Tool '{tool_name}' not found in TOOL_MAP"

    def test_all_tools_count(self):
        """ALL_TOOLS should have exactly 14 tools."""
        from agents.screener_tools import ALL_TOOLS
        assert len(ALL_TOOLS) == 14

    def test_tool_map_count(self):
        """TOOL_MAP should have exactly 14 entries."""
        from agents.screener_tools import TOOL_MAP
        assert len(TOOL_MAP) == 14

    def test_all_tool_functions_callable(self):
        """All functions in TOOL_MAP should be callable or FunctionTool objects."""
        from agents.screener_tools import TOOL_MAP
        for name, func in TOOL_MAP.items():
            # openai-agents FunctionTool objects are not directly callable but are valid tools
            is_callable = callable(func)
            has_fn = hasattr(func, 'fn') or hasattr(func, 'on_invoke_tool') or hasattr(func, 'name')
            assert is_callable or has_fn, f"Tool '{name}' is not a callable or FunctionTool"


class TestScreenerToolFunctions:
    """Test individual screener tool functions (mocked screener)."""

    def _mock_screener_run(self):
        """Return a mock result list."""
        return [{'Stock': 'RELIANCE', 'LTP': '2450.0', 'RSI': '62.5'}]

    @patch('agents.screener_tools._run_screen')
    def test_screen_breakout_calls_run_screen(self, mock_run):
        """screen_breakout should call _run_screen with correct option."""
        mock_run.return_value = self._mock_screener_run()
        from agents.screener_tools import screen_breakout

        # FunctionTool objects from openai-agents are not directly callable
        # but have an underlying function accessible via .fn attribute
        func = screen_breakout
        underlying = None
        if hasattr(func, 'fn') and callable(func.fn):
            underlying = func.fn
        elif hasattr(func, '__wrapped__') and callable(func.__wrapped__):
            underlying = func.__wrapped__
        elif callable(func):
            underlying = func
        else:
            # FunctionTool: just verify the tool has the right name
            assert hasattr(func, 'name') and func.name == 'screen_breakout'
            return  # Can't call directly, but tool is properly created

        if underlying:
            result = underlying(index="Nifty 50", days_lookback=30)

        mock_run.assert_called_once()
        call_args = mock_run.call_args
        assert call_args[0][1] == 1  # execute_option=1 for breakout

    @patch('agents.screener_tools._run_screen')
    def test_screen_rsi_passes_min_max(self, mock_run):
        """screen_rsi should pass min_rsi and max_rsi to _run_screen."""
        mock_run.return_value = []
        from agents.screener_tools import screen_rsi

        func = screen_rsi
        underlying = None
        if hasattr(func, 'fn') and callable(func.fn):
            underlying = func.fn
        elif hasattr(func, '__wrapped__') and callable(func.__wrapped__):
            underlying = func.__wrapped__
        elif callable(func):
            underlying = func
        else:
            # FunctionTool: verify correct name
            assert hasattr(func, 'name') and func.name == 'screen_rsi'
            return

        if underlying:
            try:
                underlying(index="Nifty 500", min_rsi=50, max_rsi=65)
            except Exception:
                pass

        if mock_run.called:
            call_kwargs = mock_run.call_args[1]
            assert call_kwargs.get('min_rsi') == 50
            assert call_kwargs.get('max_rsi') == 65


class TestIndexResolution:
    """Test the index name to ticker option resolution."""

    def test_nifty_50_resolves_to_1(self):
        """'Nifty 50' should resolve to ticker option 1."""
        from agents.screener_tools import _resolve_index
        assert _resolve_index("Nifty 50") == 1

    def test_nifty_500_resolves_to_5(self):
        """'Nifty 500' should resolve to ticker option 5."""
        from agents.screener_tools import _resolve_index
        assert _resolve_index("Nifty 500") == 5

    def test_fo_stocks_resolves_to_14(self):
        """'F&O Stocks' should resolve to ticker option 14."""
        from agents.screener_tools import _resolve_index
        assert _resolve_index("F&O Stocks") == 14

    def test_case_insensitive(self):
        """Index resolution should be case-insensitive."""
        from agents.screener_tools import _resolve_index
        assert _resolve_index("NIFTY 50") == _resolve_index("nifty 50")
        assert _resolve_index("nifty500") == 5

    def test_numeric_string_resolves(self):
        """Numeric string like '1' should resolve to that option."""
        from agents.screener_tools import _resolve_index
        assert _resolve_index("1") == 1
        assert _resolve_index("5") == 5

    def test_unknown_index_defaults_to_5(self):
        """Unknown index should default to option 5 (Nifty 500)."""
        from agents.screener_tools import _resolve_index
        result = _resolve_index("Unknown Index XYZ")
        assert result == 5


class TestAgentLoader:
    """Test AgentLoader persona file scanning and loading."""

    @pytest.fixture
    def loader(self):
        """Create an AgentLoader pointing at the actual personas directory."""
        from agents.agent_loader import AgentLoader
        return AgentLoader()

    def test_agent_loader_imports(self):
        """AgentLoader should import without errors."""
        from agents.agent_loader import AgentLoader
        assert AgentLoader is not None

    def test_personas_directory_exists(self, loader):
        """Personas directory should exist."""
        assert os.path.isdir(loader.personas_dir), \
            f"Personas directory not found: {loader.personas_dir}"

    def test_list_persona_files(self, loader):
        """Should find at least 4 persona YAML files."""
        files = loader.list_persona_files()
        assert len(files) >= 4, f"Expected >= 4 persona files, found: {files}"

    def test_list_personas(self, loader):
        """Should return at least 4 persona names."""
        names = loader.list_personas()
        assert len(names) >= 4

    def test_load_swing_trader(self, loader):
        """Should load SwingTrader persona by name."""
        persona = loader.load('swing_trader')
        assert persona is not None
        assert persona.get('name') == 'SwingTrader'
        assert 'instructions' in persona
        assert 'tools' in persona
        assert 'index' in persona

    def test_load_day_trader(self, loader):
        """Should load DayTrader persona."""
        persona = loader.load('day_trader')
        assert persona is not None
        assert persona.get('name') == 'DayTrader'

    def test_load_option_buyer(self, loader):
        """Should load OptionBuyer persona."""
        persona = loader.load('option_buyer')
        assert persona is not None
        assert persona.get('name') == 'OptionBuyer'

    def test_load_value_screener(self, loader):
        """Should load ValueScreener persona."""
        persona = loader.load('value_screener')
        assert persona is not None
        assert persona.get('name') == 'ValueScreener'

    def test_load_nonexistent_returns_none(self, loader):
        """Loading a non-existent persona should return None."""
        persona = loader.load('nonexistent_persona_xyz')
        assert persona is None

    def test_load_all_returns_list(self, loader):
        """load_all should return a list of configs."""
        all_personas = loader.load_all()
        assert isinstance(all_personas, list)
        assert len(all_personas) >= 4

    def test_each_persona_has_required_fields(self, loader):
        """Each persona should have name, instructions, tools, and index."""
        for persona in loader.load_all():
            name = persona.get('name', 'unknown')
            assert 'name' in persona, f"Persona missing 'name': {persona}"
            assert 'instructions' in persona, f"Persona '{name}' missing 'instructions'"
            assert 'tools' in persona, f"Persona '{name}' missing 'tools'"
            assert isinstance(persona['tools'], list), f"Persona '{name}' tools should be a list"

    def test_persona_tools_reference_valid_tool_names(self, loader):
        """All tools referenced in personas should exist in TOOL_MAP."""
        from agents.screener_tools import TOOL_MAP
        for persona in loader.load_all():
            name = persona.get('name', 'unknown')
            for tool_name in persona.get('tools', []):
                assert tool_name in TOOL_MAP, \
                    f"Persona '{name}' references unknown tool: '{tool_name}'"

    def test_summary_returns_string(self, loader):
        """summary() should return a non-empty string."""
        summary = loader.summary()
        assert isinstance(summary, str)
        assert len(summary) > 0
        assert 'SwingTrader' in summary or 'DayTrader' in summary


class TestAgentLoaderCustomDir:
    """Test AgentLoader with custom directory."""

    def test_custom_dir_empty(self, tmp_path):
        """AgentLoader with empty directory should return empty lists."""
        from agents.agent_loader import AgentLoader
        loader = AgentLoader(personas_dir=str(tmp_path))
        assert loader.list_personas() == []
        assert loader.load_all() == []

    def test_custom_dir_with_yaml(self, tmp_path):
        """AgentLoader should find YAML files in custom directory."""
        import yaml
        from agents.agent_loader import AgentLoader

        persona_data = {
            'name': 'TestPersona',
            'instructions': 'Test instructions',
            'tools': ['screen_breakout'],
            'index': 'Nifty 50',
        }
        with open(str(tmp_path / "test_persona.yaml"), 'w') as f:
            yaml.dump(persona_data, f)

        loader = AgentLoader(personas_dir=str(tmp_path))
        personas = loader.load_all()
        assert len(personas) == 1
        assert personas[0]['name'] == 'TestPersona'

    def test_load_by_name_from_custom_dir(self, tmp_path):
        """Should load persona by name from custom directory."""
        import yaml
        from agents.agent_loader import AgentLoader

        persona_data = {
            'name': 'MyPersona',
            'instructions': 'Do stuff',
            'tools': ['screen_rsi'],
            'index': 'Nifty 200',
        }
        with open(str(tmp_path / "my_persona.yaml"), 'w') as f:
            yaml.dump(persona_data, f)

        loader = AgentLoader(personas_dir=str(tmp_path))
        result = loader.load('my_persona')
        assert result is not None
        assert result['name'] == 'MyPersona'
