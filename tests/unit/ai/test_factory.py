"""Tests for ai/factory.py - AIFactory provider creation and metadata."""

import pytest

from ai.factory import AIFactory


class TestAIFactoryProviders:
    """Tests for AIFactory.PROVIDERS metadata."""

    def test_providers_is_dict(self):
        """PROVIDERS should be a dictionary."""
        assert isinstance(AIFactory.PROVIDERS, dict)

    def test_providers_not_empty(self):
        """PROVIDERS should contain provider definitions."""
        assert len(AIFactory.PROVIDERS) > 0

    def test_expected_providers_exist(self):
        """Should contain all expected providers."""
        expected = [
            "ollama", "openai", "anthropic", "google", "azure",
            "bedrock", "groq", "mistral", "together", "cohere",
            "xai", "openrouter", "fireworks", "deepseek", "perplexity",
            "custom", "lm_studio", "llama_cpp", "huggingface", "cloudflare",
            "nvidia"
        ]
        for provider in expected:
            assert provider in AIFactory.PROVIDERS, f"Missing provider: {provider}"

    def test_provider_has_required_fields(self):
        """Each provider should have name, description, requires_api_key, requires_endpoint."""
        for name, info in AIFactory.PROVIDERS.items():
            assert "name" in info, f"{name} missing 'name'"
            assert "description" in info, f"{name} missing 'description'"
            assert "requires_api_key" in info, f"{name} missing 'requires_api_key'"
            assert "requires_endpoint" in info, f"{name} missing 'requires_endpoint'"

    def test_provider_name_is_string(self):
        """Provider name should be a string."""
        for name, info in AIFactory.PROVIDERS.items():
            assert isinstance(info["name"], str), f"{name} name is not string"
            assert len(info["name"]) > 0, f"{name} has empty name"

    def test_provider_description_is_string(self):
        """Provider description should be a string."""
        for name, info in AIFactory.PROVIDERS.items():
            assert isinstance(info["description"], str), f"{name} description is not string"

    def test_requires_api_key_is_bool(self):
        """requires_api_key should be a boolean."""
        for name, info in AIFactory.PROVIDERS.items():
            assert isinstance(info["requires_api_key"], bool), f"{name} requires_api_key is not bool"

    def test_requires_endpoint_is_bool(self):
        """requires_endpoint should be a boolean."""
        for name, info in AIFactory.PROVIDERS.items():
            assert isinstance(info["requires_endpoint"], bool), f"{name} requires_endpoint is not bool"


class TestAIFactoryListProviders:
    """Tests for AIFactory.list_providers method."""

    def test_returns_list(self):
        """list_providers should return a list."""
        result = AIFactory.list_providers()
        assert isinstance(result, list)

    def test_returns_all_provider_keys(self):
        """list_providers should return all provider keys."""
        result = AIFactory.list_providers()
        expected_count = len(AIFactory.PROVIDERS)
        assert len(result) == expected_count

    def test_contains_known_providers(self):
        """Should contain known provider names."""
        result = AIFactory.list_providers()
        assert "ollama" in result
        assert "openai" in result
        assert "anthropic" in result

    def test_all_keys_are_strings(self):
        """All provider keys should be strings."""
        result = AIFactory.list_providers()
        for key in result:
            assert isinstance(key, str)


class TestAIFactoryGetProviderInfo:
    """Tests for AIFactory.get_provider_info method."""

    def test_returns_dict_for_known_provider(self):
        """Should return a dict for known providers."""
        info = AIFactory.get_provider_info("openai")
        assert isinstance(info, dict)

    def test_returns_correct_info(self):
        """Should return correct metadata for provider."""
        info = AIFactory.get_provider_info("openai")
        assert info["name"] == "OpenAI"
        assert info["requires_api_key"] is True
        assert info["requires_endpoint"] is False

    def test_returns_empty_dict_for_unknown(self):
        """Should return empty dict for unknown provider."""
        info = AIFactory.get_provider_info("nonexistent-provider")
        assert info == {}

    def test_ollama_info(self):
        """Ollama should not require API key but require endpoint."""
        info = AIFactory.get_provider_info("ollama")
        assert info["name"] == "Ollama"
        assert info["requires_api_key"] is False
        assert info["requires_endpoint"] is True

    def test_anthropic_info(self):
        """Anthropic should require API key."""
        info = AIFactory.get_provider_info("anthropic")
        assert info["name"] == "Anthropic"
        assert info["requires_api_key"] is True
        assert info["requires_endpoint"] is False

    def test_azure_info(self):
        """Azure should require both API key and endpoint."""
        info = AIFactory.get_provider_info("azure")
        assert info["name"] == "Azure OpenAI"
        assert info["requires_api_key"] is True
        assert info["requires_endpoint"] is True

    def test_bedrock_info(self):
        """Bedrock should not require API key (uses AWS credentials)."""
        info = AIFactory.get_provider_info("bedrock")
        assert info["name"] == "AWS Bedrock"
        assert info["requires_api_key"] is False
        assert info["requires_endpoint"] is False


class TestAIFactoryGetProvider:
    """Tests for AIFactory.get_provider method."""

    def test_ollama_provider_creation(self):
        """Should create OllamaProvider with config."""
        from ai.ollama import OllamaProvider

        config = {
            "provider": "ollama",
            "endpoint": "http://localhost:11434",
            "model": "llama3.2"
        }
        provider = AIFactory.get_provider(config)
        assert isinstance(provider, OllamaProvider)
        assert provider.model == "llama3.2"

    def test_openai_provider_creation(self):
        """Should create OpenAICompatibleProvider for OpenAI."""
        from ai.openai_compat import OpenAICompatibleProvider

        config = {
            "provider": "openai",
            "api_key": "test-key",
            "model": "gpt-4o-mini"
        }
        provider = AIFactory.get_provider(config)
        assert isinstance(provider, OpenAICompatibleProvider)
        assert provider.model == "gpt-4o-mini"

    def test_anthropic_provider_creation(self):
        """Should create AnthropicProvider."""
        from ai.anthropic import AnthropicProvider

        config = {
            "provider": "anthropic",
            "api_key": "test-key",
            "model": "claude-3-5-sonnet-20241022"
        }
        provider = AIFactory.get_provider(config)
        assert isinstance(provider, AnthropicProvider)
        assert provider.model == "claude-3-5-sonnet-20241022"

    def test_groq_provider_creation(self):
        """Should create OpenAICompatibleProvider for Groq."""
        from ai.openai_compat import OpenAICompatibleProvider

        config = {
            "provider": "groq",
            "api_key": "test-key",
            "model": "llama-3.3-70b-versatile"
        }
        provider = AIFactory.get_provider(config)
        assert isinstance(provider, OpenAICompatibleProvider)
        assert provider.model == "llama-3.3-70b-versatile"

    def test_default_model_ollama(self):
        """Ollama should default to llama3.2 model."""
        config = {"provider": "ollama"}
        provider = AIFactory.get_provider(config)
        assert provider.model == "llama3.2"

    def test_default_model_openai(self):
        """OpenAI should default to gpt-4o-mini model."""
        config = {"provider": "openai", "api_key": "test"}
        provider = AIFactory.get_provider(config)
        assert provider.model == "gpt-4o-mini"

    def test_default_endpoint_ollama(self):
        """Ollama should default to localhost:11434."""
        from ai.ollama import OllamaProvider

        config = {"provider": "ollama"}
        provider = AIFactory.get_provider(config)
        assert isinstance(provider, OllamaProvider)

    def test_lm_studio_adds_v1_suffix(self):
        """LM Studio should ensure /v1 suffix on endpoint."""
        from ai.openai_compat import OpenAICompatibleProvider

        config = {
            "provider": "lm_studio",
            "endpoint": "http://localhost:1234"
        }
        provider = AIFactory.get_provider(config)
        assert isinstance(provider, OpenAICompatibleProvider)

    def test_llama_cpp_adds_v1_suffix(self):
        """llama.cpp should ensure /v1 suffix on endpoint."""
        from ai.openai_compat import OpenAICompatibleProvider

        config = {
            "provider": "llama_cpp",
            "endpoint": "http://localhost:8000"
        }
        provider = AIFactory.get_provider(config)
        assert isinstance(provider, OpenAICompatibleProvider)

    def test_unknown_provider_raises(self):
        """Should raise ValueError for unknown provider."""
        config = {"provider": "nonexistent_provider"}
        with pytest.raises(ValueError, match="Unknown provider"):
            AIFactory.get_provider(config)

    def test_empty_config_defaults_to_ollama(self):
        """Empty config should default to ollama provider."""
        from ai.ollama import OllamaProvider

        config = {}
        provider = AIFactory.get_provider(config)
        assert isinstance(provider, OllamaProvider)

    def test_google_provider_creation(self):
        """Should create GoogleVertexProvider."""
        from ai.google_vertex import GoogleVertexProvider

        config = {
            "provider": "google",
            "api_key": "test-key",
            "model": "gemini-2.0-flash"
        }
        provider = AIFactory.get_provider(config)
        assert isinstance(provider, GoogleVertexProvider)

    def test_azure_provider_creation(self):
        """Should create AzureProvider."""
        from ai.azure import AzureProvider

        config = {
            "provider": "azure",
            "endpoint": "https://test.openai.azure.com",
            "api_key": "test-key",
            "model": "gpt-4o"
        }
        provider = AIFactory.get_provider(config)
        assert isinstance(provider, AzureProvider)

    def test_cohere_provider_creation(self):
        """Should create CohereProvider."""
        from ai.cohere import CohereProvider

        config = {
            "provider": "cohere",
            "api_key": "test-key",
            "model": "command-r-plus"
        }
        provider = AIFactory.get_provider(config)
        assert isinstance(provider, CohereProvider)

    def test_bedrock_provider_creation(self):
        """Should create BedrockProvider."""
        from ai.bedrock import BedrockProvider

        config = {
            "provider": "bedrock",
            "region": "us-east-1",
            "model": "anthropic.claude-3-sonnet-20240229-v1:0"
        }
        provider = AIFactory.get_provider(config)
        assert isinstance(provider, BedrockProvider)

    def test_mistral_provider_creation(self):
        """Should create OpenAICompatibleProvider for Mistral."""
        from ai.openai_compat import OpenAICompatibleProvider

        config = {
            "provider": "mistral",
            "api_key": "test-key",
            "model": "mistral-large-latest"
        }
        provider = AIFactory.get_provider(config)
        assert isinstance(provider, OpenAICompatibleProvider)

    def test_deepseek_provider_creation(self):
        """Should create OpenAICompatibleProvider for DeepSeek."""
        from ai.openai_compat import OpenAICompatibleProvider

        config = {
            "provider": "deepseek",
            "api_key": "test-key",
            "model": "deepseek-chat"
        }
        provider = AIFactory.get_provider(config)
        assert isinstance(provider, OpenAICompatibleProvider)


class TestAIFactoryGetOrDefault:
    """Tests for AIFactory._get_or_default helper method."""

    def test_returns_value_when_present(self):
        """Should return config value when present."""
        config = {"key": "value"}
        result = AIFactory._get_or_default(config, "key", "default")
        assert result == "value"

    def test_returns_default_when_missing(self):
        """Should return default when key is missing."""
        config = {}
        result = AIFactory._get_or_default(config, "key", "default")
        assert result == "default"

    def test_returns_default_when_empty(self):
        """Should return default when value is empty string."""
        config = {"key": ""}
        result = AIFactory._get_or_default(config, "key", "default")
        assert result == "default"

    def test_returns_default_when_none(self):
        """Should return default when value is None."""
        config = {"key": None}
        result = AIFactory._get_or_default(config, "key", "default")
        assert result == "default"


class TestProviderDescriptions:
    """Tests for provider description content."""

    def test_ollama_description_mentions_local(self):
        """Ollama description should mention local models."""
        info = AIFactory.get_provider_info("ollama")
        assert "local" in info["description"].lower() or "Local" in info["description"]

    def test_openai_description_mentions_gpt(self):
        """OpenAI description should mention GPT models."""
        info = AIFactory.get_provider_info("openai")
        assert "GPT" in info["description"]

    def test_anthropic_description_mentions_claude(self):
        """Anthropic description should mention Claude."""
        info = AIFactory.get_provider_info("anthropic")
        assert "Claude" in info["description"]

    def test_google_description_mentions_gemini(self):
        """Google description should mention Gemini."""
        info = AIFactory.get_provider_info("google")
        assert "Gemini" in info["description"]

    def test_groq_description_mentions_fast(self):
        """Groq description should mention fast inference."""
        info = AIFactory.get_provider_info("groq")
        assert "fast" in info["description"].lower() or "Fast" in info["description"]
