"""
ScreeniAgent - AI-native stock screening agent powered by openai-agents.
Supports OpenAI, Anthropic, and OpenAI-compatible LLM providers.
Integrates Kite MCP for live market data when configured.
"""
import asyncio
import logging
import os
import sys

_src_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if _src_dir not in sys.path:
    sys.path.insert(0, _src_dir)

from agents.llm_config import load_llm_config, load_kite_config, ScreeniConfigError
from agents.screener_tools import TOOL_MAP, ALL_TOOLS

logger = logging.getLogger(__name__)

# Avoid name collision with the 'agents' package from openai-agents
try:
    import sys as _sys
    import importlib as _il

    _SITE_PACKAGES = '/home/node/.local/lib/python3.11/site-packages'

    def _load_real_openai_agents_for_agent():
        """Load openai-agents bypassing local src/agents/ shadow."""
        import site as _site
        _sp_paths = []
        try:
            _sp_paths.extend(_site.getsitepackages())
        except Exception:
            pass
        try:
            _sp_paths.append(_site.getusersitepackages())
        except Exception:
            pass
        _sp_paths.append(_SITE_PACKAGES)

        _our_agents = _sys.modules.pop('agents', None)
        _valid_sp = [p for p in _sp_paths if __import__('os').path.exists(p)]
        for _sp in _valid_sp:
            _sys.path.insert(0, _sp)
        try:
            _mod = _il.import_module('agents')
            return _mod
        finally:
            for _sp in _valid_sp:
                try:
                    _sys.path.remove(_sp)
                except ValueError:
                    pass
            if _our_agents is not None:
                _sys.modules['agents'] = _our_agents

    _agents_pkg = _load_real_openai_agents_for_agent()
    Agent = _agents_pkg.Agent
    Runner = _agents_pkg.Runner
    _AGENTS_AVAILABLE = True
except (ImportError, AttributeError, Exception) as _e:
    _AGENTS_AVAILABLE = False
    Agent = None
    Runner = None


def _build_openai_model(llm_cfg: dict):
    """Build an openai-agents compatible model string for OpenAI provider."""
    return llm_cfg['model']


def _build_anthropic_model(llm_cfg: dict):
    """Build model string for Anthropic via litellm prefix."""
    model = llm_cfg['model']
    if not model.startswith('anthropic/'):
        model = f"anthropic/{model}"
    return model


def _build_openai_compatible_model(llm_cfg: dict):
    """Build model for OpenAI-compatible endpoints (Ollama, LiteLLM, etc.)."""
    return llm_cfg['model']


class ScreeniAgent:
    """
    AI-native stock screener agent.
    Wraps openai-agents Agent + Runner with Screeni-py tools and optional Kite MCP.
    """

    def __init__(self, persona_config: dict, llm_config: dict = None):
        """
        Initialize ScreeniAgent with persona and LLM config.
        
        Args:
            persona_config: Dict from persona YAML (name, instructions, tools, index)
            llm_config: Dict from llm_config.load_llm_config(). If None, loads from yaml.
        """
        if not _AGENTS_AVAILABLE:
            raise ImportError(
                "openai-agents package is required. Install with: pip install openai-agents"
            )

        if llm_config is None:
            llm_config = load_llm_config()

        self.persona_config = persona_config
        self.llm_config = llm_config
        self._agent = None
        self._setup_agent()

    def _setup_agent(self):
        """Build the underlying Agent instance."""
        provider = self.llm_config.get('provider', 'openai')
        api_key = self.llm_config.get('api_key')
        model_name = self.llm_config.get('model', 'gpt-4o')
        base_url = self.llm_config.get('base_url')

        # Set API key env var for the agents SDK
        if provider == 'openai':
            os.environ['OPENAI_API_KEY'] = api_key
            model = _build_openai_model(self.llm_config)
        elif provider == 'anthropic':
            os.environ['ANTHROPIC_API_KEY'] = api_key
            # Use litellm prefix for anthropic compatibility
            model = _build_anthropic_model(self.llm_config)
        elif provider == 'openai-compatible':
            os.environ['OPENAI_API_KEY'] = api_key
            if base_url:
                os.environ['OPENAI_BASE_URL'] = base_url
            model = _build_openai_compatible_model(self.llm_config)
        else:
            os.environ['OPENAI_API_KEY'] = api_key
            model = model_name

        # Filter tools based on persona config
        persona_tools_list = self.persona_config.get('tools', [])
        if persona_tools_list:
            selected_tools = [
                TOOL_MAP[name] for name in persona_tools_list
                if name in TOOL_MAP
            ]
        else:
            selected_tools = ALL_TOOLS

        # Build instructions
        instructions = self.persona_config.get('instructions', '')
        persona_index = self.persona_config.get('index', 'Nifty 500')
        if persona_index and 'index' not in instructions.lower():
            instructions = f"{instructions}\n\nDefault index: {persona_index}"

        # Add Kite MCP if configured
        mcp_servers = []
        kite_cfg = load_kite_config()
        if kite_cfg.get('enabled') and kite_cfg.get('url'):
            try:
                from agents.mcp import MCPServerStreamableHttp
                kite_server = MCPServerStreamableHttp(url=kite_cfg['url'])
                mcp_servers.append(kite_server)
                logger.info(f"Kite MCP enabled: {kite_cfg['url']}")
            except Exception as e:
                logger.warning(f"Could not initialize Kite MCP server: {e}")

        # Create the agent
        kwargs = {
            'name': self.persona_config.get('name', 'ScreeniAgent'),
            'instructions': instructions,
            'tools': selected_tools,
        }
        if mcp_servers:
            kwargs['mcp_servers'] = mcp_servers

        # model can be passed as string for OpenAI; for other providers may need model object
        try:
            self._agent = Agent(model=model, **kwargs)
        except TypeError:
            # Fallback: some versions may not accept model as kwarg
            self._agent = Agent(**kwargs)

    async def run(self, query: str) -> str:
        """
        Run the agent asynchronously with the given query.
        
        Args:
            query: Natural language query for the agent
            
        Returns:
            Agent response as string
        """
        try:
            result = await Runner.run(self._agent, query)
            return result.final_output
        except Exception as e:
            logger.error(f"Agent run failed: {e}")
            return f"Error: {e}"

    def run_sync(self, query: str) -> str:
        """
        Run the agent synchronously.
        
        Args:
            query: Natural language query for the agent
            
        Returns:
            Agent response as string
        """
        try:
            result = Runner.run_sync(self._agent, query)
            return result.final_output
        except Exception as e:
            logger.error(f"Agent run_sync failed: {e}")
            return f"Error: {e}"
