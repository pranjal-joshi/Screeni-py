"""
Screeni-py Agent Package
Provides AI-native workflow with LLM-powered stock screening.
Lazy-imports to avoid circular imports with the openai-agents 'agents' package.
"""


def _get_screeni_agent():
    """Lazy import ScreeniAgent to avoid circular import with openai-agents package."""
    from .screeni_agent import ScreeniAgent
    return ScreeniAgent


def _get_agent_loader():
    """Lazy import AgentLoader."""
    from .agent_loader import AgentLoader
    return AgentLoader


# Only expose classes, not triggering imports at module load
__all__ = ["ScreeniAgent", "AgentLoader"]


def __getattr__(name):
    """Lazy attribute access to avoid import-time circular imports."""
    if name == "ScreeniAgent":
        return _get_screeni_agent()
    if name == "AgentLoader":
        return _get_agent_loader()
    raise AttributeError(f"module 'agents' (screenipy) has no attribute {name!r}")
