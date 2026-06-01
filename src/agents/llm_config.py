"""
LLM Configuration for Screeni-py Agent Harness.
Reads screenipy.yaml and returns an openai-agents-compatible model config.
"""
import os
import yaml


class ScreeniConfigError(Exception):
    """Raised when screenipy agent configuration is invalid or missing."""
    pass


def _find_config_file():
    """Locate screenipy.yaml in the repo root or src/ directory."""
    candidates = [
        os.path.join(os.path.dirname(__file__), '..', '..', 'screenipy.yaml'),
        os.path.join(os.path.dirname(__file__), '..', 'screenipy.yaml'),
        'screenipy.yaml',
    ]
    for path in candidates:
        path = os.path.abspath(path)
        if os.path.exists(path):
            return path
    return None


def load_llm_config():
    """
    Load LLM configuration from screenipy.yaml.
    Returns a dict with keys: provider, model, base_url, api_key.
    Raises ScreeniConfigError if configuration is invalid.
    """
    config_path = _find_config_file()
    if config_path is None:
        raise ScreeniConfigError(
            "screenipy.yaml not found. Please create it in the repo root or src/ directory. "
            "See screenipy.yaml.example for the format."
        )

    with open(config_path, 'r') as f:
        config = yaml.safe_load(f)

    llm_config = config.get('llm', {})
    provider = llm_config.get('provider', 'openai')
    model = llm_config.get('model', 'gpt-4o')
    base_url = llm_config.get('base_url', None)
    api_key_env = llm_config.get('api_key_env', 'SCREENIPY_API_KEY')

    api_key = os.environ.get(api_key_env, None)
    if not api_key:
        raise ScreeniConfigError(
            f"API key not found. Please set the '{api_key_env}' environment variable.\n"
            f"  export {api_key_env}=your_api_key_here\n"
            f"Supported providers: openai, anthropic, openai-compatible"
        )

    return {
        'provider': provider,
        'model': model,
        'base_url': base_url,
        'api_key': api_key,
        'api_key_env': api_key_env,
    }


def load_kite_config():
    """Load Kite MCP configuration from screenipy.yaml."""
    config_path = _find_config_file()
    if config_path is None:
        return {'enabled': False, 'url': None}

    with open(config_path, 'r') as f:
        config = yaml.safe_load(f)

    kite_config = config.get('kite_mcp', {})
    return {
        'enabled': kite_config.get('enabled', False),
        'url': kite_config.get('url', 'https://mcp.kite.trade/mcp'),
    }


def load_workflow_config():
    """Load workflow configuration from screenipy.yaml."""
    config_path = _find_config_file()
    if config_path is None:
        return {'default_mode': 'classic', 'schedule': []}

    with open(config_path, 'r') as f:
        config = yaml.safe_load(f)

    return {
        'default_mode': config.get('workflow', {}).get('default_mode', 'classic'),
        'schedule': config.get('schedule', []),
    }
