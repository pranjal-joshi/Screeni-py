"""
Tests for LLM Configuration - llm_config.py
Tests provider detection, API key validation, and ScreeniConfigError.
"""
import pytest
import os
import sys
import tempfile

# Ensure src is in path
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..', 'src')))

from agents.llm_config import ScreeniConfigError


class TestScreeniConfigError:
    """Test ScreeniConfigError is properly defined."""

    def test_error_is_exception(self):
        """ScreeniConfigError should be an Exception subclass."""
        assert issubclass(ScreeniConfigError, Exception)

    def test_error_can_be_raised(self):
        """ScreeniConfigError should be raisable."""
        with pytest.raises(ScreeniConfigError):
            raise ScreeniConfigError("Test error")

    def test_error_has_message(self):
        """ScreeniConfigError should preserve message."""
        try:
            raise ScreeniConfigError("Test message")
        except ScreeniConfigError as e:
            assert "Test message" in str(e)


class TestLoadLLMConfig:
    """Test load_llm_config function."""

    def test_raises_config_error_when_no_api_key(self, tmp_path, monkeypatch):
        """Should raise ScreeniConfigError when API key env var is not set."""
        # Create a valid screenipy.yaml
        yaml_content = """
llm:
  provider: openai
  model: gpt-4o
  api_key_env: SCREENIPY_TEST_KEY_MISSING_XYZ
"""
        yaml_path = str(tmp_path / "screenipy.yaml")
        with open(yaml_path, 'w') as f:
            f.write(yaml_content)

        # Ensure the env var is not set
        monkeypatch.delenv('SCREENIPY_TEST_KEY_MISSING_XYZ', raising=False)

        from agents import llm_config
        monkeypatch.setattr(llm_config, '_find_config_file', lambda: yaml_path)

        with pytest.raises(ScreeniConfigError) as exc_info:
            llm_config.load_llm_config()

        assert 'SCREENIPY_TEST_KEY_MISSING_XYZ' in str(exc_info.value)

    def test_returns_config_with_valid_api_key(self, tmp_path, monkeypatch):
        """Should return config dict when API key is present."""
        yaml_content = """
llm:
  provider: openai
  model: gpt-4o
  api_key_env: SCREENIPY_TEST_KEY_EXISTS
"""
        yaml_path = str(tmp_path / "screenipy.yaml")
        with open(yaml_path, 'w') as f:
            f.write(yaml_content)

        monkeypatch.setenv('SCREENIPY_TEST_KEY_EXISTS', 'sk-test-key-12345')

        from agents import llm_config
        monkeypatch.setattr(llm_config, '_find_config_file', lambda: yaml_path)

        config = llm_config.load_llm_config()

        assert config is not None
        assert config['provider'] == 'openai'
        assert config['model'] == 'gpt-4o'
        assert config['api_key'] == 'sk-test-key-12345'

    def test_raises_config_error_when_no_yaml(self, monkeypatch):
        """Should raise ScreeniConfigError when yaml file not found."""
        from agents import llm_config
        monkeypatch.setattr(llm_config, '_find_config_file', lambda: None)

        with pytest.raises(ScreeniConfigError) as exc_info:
            llm_config.load_llm_config()

        assert 'screenipy.yaml' in str(exc_info.value).lower() or 'not found' in str(exc_info.value).lower()

    def test_provider_openai(self, tmp_path, monkeypatch):
        """Provider should be 'openai' when set in yaml."""
        yaml_content = """
llm:
  provider: openai
  model: gpt-4o
  api_key_env: TEST_API_KEY
"""
        yaml_path = str(tmp_path / "screenipy.yaml")
        with open(yaml_path, 'w') as f:
            f.write(yaml_content)

        monkeypatch.setenv('TEST_API_KEY', 'test-key')

        from agents import llm_config
        monkeypatch.setattr(llm_config, '_find_config_file', lambda: yaml_path)

        config = llm_config.load_llm_config()
        assert config['provider'] == 'openai'

    def test_provider_anthropic(self, tmp_path, monkeypatch):
        """Provider should be 'anthropic' when set in yaml."""
        yaml_content = """
llm:
  provider: anthropic
  model: claude-3-5-sonnet-20241022
  api_key_env: TEST_ANTHROPIC_KEY
"""
        yaml_path = str(tmp_path / "screenipy.yaml")
        with open(yaml_path, 'w') as f:
            f.write(yaml_content)

        monkeypatch.setenv('TEST_ANTHROPIC_KEY', 'sk-ant-test')

        from agents import llm_config
        monkeypatch.setattr(llm_config, '_find_config_file', lambda: yaml_path)

        config = llm_config.load_llm_config()
        assert config['provider'] == 'anthropic'
        assert config['model'] == 'claude-3-5-sonnet-20241022'

    def test_provider_openai_compatible(self, tmp_path, monkeypatch):
        """Provider should be 'openai-compatible' with base_url set."""
        yaml_content = """
llm:
  provider: openai-compatible
  model: llama3.2
  base_url: http://localhost:11434/v1
  api_key_env: TEST_OLLAMA_KEY
"""
        yaml_path = str(tmp_path / "screenipy.yaml")
        with open(yaml_path, 'w') as f:
            f.write(yaml_content)

        monkeypatch.setenv('TEST_OLLAMA_KEY', 'ollama-key')

        from agents import llm_config
        monkeypatch.setattr(llm_config, '_find_config_file', lambda: yaml_path)

        config = llm_config.load_llm_config()
        assert config['provider'] == 'openai-compatible'
        assert config['base_url'] == 'http://localhost:11434/v1'
        assert config['model'] == 'llama3.2'

    def test_default_provider_is_openai(self, tmp_path, monkeypatch):
        """Default provider should be 'openai' when not specified."""
        yaml_content = """
llm:
  model: gpt-4o
  api_key_env: TEST_KEY_DEFAULT
"""
        yaml_path = str(tmp_path / "screenipy.yaml")
        with open(yaml_path, 'w') as f:
            f.write(yaml_content)

        monkeypatch.setenv('TEST_KEY_DEFAULT', 'key')

        from agents import llm_config
        monkeypatch.setattr(llm_config, '_find_config_file', lambda: yaml_path)

        config = llm_config.load_llm_config()
        assert config['provider'] == 'openai'

    def test_error_message_contains_instructions(self, tmp_path, monkeypatch):
        """Error message should contain helpful instructions."""
        yaml_content = """
llm:
  api_key_env: MISSING_KEY_XYZ123
"""
        yaml_path = str(tmp_path / "screenipy.yaml")
        with open(yaml_path, 'w') as f:
            f.write(yaml_content)

        monkeypatch.delenv('MISSING_KEY_XYZ123', raising=False)

        from agents import llm_config
        monkeypatch.setattr(llm_config, '_find_config_file', lambda: yaml_path)

        with pytest.raises(ScreeniConfigError) as exc_info:
            llm_config.load_llm_config()

        error_msg = str(exc_info.value)
        # Should contain the env var name and/or instructions
        assert 'MISSING_KEY_XYZ123' in error_msg or 'export' in error_msg.lower()


class TestLoadKiteConfig:
    """Test load_kite_config function."""

    def test_returns_dict(self, tmp_path, monkeypatch):
        """Should return a dict with enabled and url keys."""
        yaml_content = """
kite_mcp:
  url: https://mcp.kite.trade/mcp
  enabled: true
"""
        yaml_path = str(tmp_path / "screenipy.yaml")
        with open(yaml_path, 'w') as f:
            f.write(yaml_content)

        from agents import llm_config
        monkeypatch.setattr(llm_config, '_find_config_file', lambda: yaml_path)

        config = llm_config.load_kite_config()
        assert 'enabled' in config
        assert 'url' in config
        assert config['enabled'] is True
        assert 'kite' in config['url']

    def test_disabled_kite(self, tmp_path, monkeypatch):
        """Should return enabled=False when disabled in config."""
        yaml_content = """
kite_mcp:
  enabled: false
"""
        yaml_path = str(tmp_path / "screenipy.yaml")
        with open(yaml_path, 'w') as f:
            f.write(yaml_content)

        from agents import llm_config
        monkeypatch.setattr(llm_config, '_find_config_file', lambda: yaml_path)

        config = llm_config.load_kite_config()
        assert config['enabled'] is False

    def test_no_yaml_returns_defaults(self, monkeypatch):
        """Should return defaults when yaml not found."""
        from agents import llm_config
        monkeypatch.setattr(llm_config, '_find_config_file', lambda: None)

        config = llm_config.load_kite_config()
        assert 'enabled' in config
        assert config['enabled'] is False


class TestLoadWorkflowConfig:
    """Test load_workflow_config function."""

    def test_default_mode_classic(self, tmp_path, monkeypatch):
        """Default workflow mode should be 'classic'."""
        yaml_content = """
workflow:
  default_mode: classic
"""
        yaml_path = str(tmp_path / "screenipy.yaml")
        with open(yaml_path, 'w') as f:
            f.write(yaml_content)

        from agents import llm_config
        monkeypatch.setattr(llm_config, '_find_config_file', lambda: yaml_path)

        config = llm_config.load_workflow_config()
        assert config['default_mode'] == 'classic'

    def test_mode_ai(self, tmp_path, monkeypatch):
        """Should return 'ai' when set in yaml."""
        yaml_content = """
workflow:
  default_mode: ai
"""
        yaml_path = str(tmp_path / "screenipy.yaml")
        with open(yaml_path, 'w') as f:
            f.write(yaml_content)

        from agents import llm_config
        monkeypatch.setattr(llm_config, '_find_config_file', lambda: yaml_path)

        config = llm_config.load_workflow_config()
        assert config['default_mode'] == 'ai'

    def test_empty_schedule(self, tmp_path, monkeypatch):
        """Schedule should be empty list when not configured."""
        yaml_content = """
schedule: []
"""
        yaml_path = str(tmp_path / "screenipy.yaml")
        with open(yaml_path, 'w') as f:
            f.write(yaml_content)

        from agents import llm_config
        monkeypatch.setattr(llm_config, '_find_config_file', lambda: yaml_path)

        config = llm_config.load_workflow_config()
        assert config['schedule'] == []
