"""
Model presets and default strategy pack for #303.

Presets ship preconfigured — no manual config required.
- Model presets: OpenAI-compatible models selectable via `model` in /v1/chat/completions.
- Default strategy pack: curated breakout + vcp skills work out of the box.
"""
from typing import List, Dict

# Model presets — selectable with no manual configuration (BYOK file optional for key,
# but the list itself is always available). Mirrors typical BYOK providers.
MODEL_PRESETS: List[Dict[str, str]] = [
    {"id": "screenipy", "name": "Screenipy Auto", "provider": "openai-compatible", "owned_by": "screenipy"},
    {"id": "gpt-4o", "name": "GPT-4o", "provider": "openai", "owned_by": "openai"},
    {"id": "gpt-4o-mini", "name": "GPT-4o Mini", "provider": "openai", "owned_by": "openai"},
    {"id": "claude-3-5-sonnet", "name": "Claude 3.5 Sonnet", "provider": "anthropic", "owned_by": "anthropic"},
    {"id": "llama3.2", "name": "Llama 3.2 (Ollama)", "provider": "openai-compatible", "owned_by": "meta"},
]

# Default strategy pack — skills that ship in src/agents/skills/
DEFAULT_STRATEGY_PACK: List[str] = ["breakout", "vcp"]

def list_model_ids() -> List[str]:
    return [m["id"] for m in MODEL_PRESETS]

def list_strategy_pack() -> List[str]:
    return list(DEFAULT_STRATEGY_PACK)
