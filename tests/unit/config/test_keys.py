"""Unit tests for config/keys.py - sensitive key detection and ConfigKeys class."""

from config.keys import SENSITIVE_KEYS, ConfigKeys, is_sensitive_key


class TestSensitiveKeysSet:
    """Tests for SENSITIVE_KEYS constant."""

    def test_sensitive_keys_is_set(self):
        """SENSITIVE_KEYS should be a set."""
        assert isinstance(SENSITIVE_KEYS, set)

    def test_sensitive_keys_not_empty(self):
        """SENSITIVE_KEYS should contain at least one key."""
        assert len(SENSITIVE_KEYS) > 0

    def test_all_known_provider_api_keys_present(self):
        """Known provider API keys should be in SENSITIVE_KEYS."""
        expected_providers = [
            "openai",
            "azure",
            "xai",
            "anthropic",
            "google",
            "cohere",
            "together",
            "groq",
            "mistral",
            "deepseek",
            "openrouter",
            "fireworks",
            "perplexity",
            "lm_studio",
        ]
        for provider in expected_providers:
            assert f"ai.{provider}.api_key" in SENSITIVE_KEYS

    def test_bedrock_secret_key_present(self):
        """Bedrock secret key should be in SENSITIVE_KEYS."""
        assert "ai.bedrock.secret_key" in SENSITIVE_KEYS


class TestIsSensitiveKey:
    """Tests for is_sensitive_key() function."""

    def test_exact_match_in_sensitive_keys(self):
        """Keys explicitly in SENSITIVE_KEYS should be sensitive."""
        assert is_sensitive_key("ai.openai.api_key") is True
        assert is_sensitive_key("ai.anthropic.api_key") is True
        assert is_sensitive_key("ai.bedrock.secret_key") is True

    def test_pattern_match_api_key_suffix(self):
        """Any key ending with .api_key should be sensitive."""
        assert is_sensitive_key("ai.new_provider.api_key") is True
        assert is_sensitive_key("custom.service.api_key") is True
        assert is_sensitive_key("some.nested.path.api_key") is True

    def test_pattern_match_secret_key_suffix(self):
        """Any key ending with .secret_key should be sensitive."""
        assert is_sensitive_key("ai.some_provider.secret_key") is True
        assert is_sensitive_key("custom.service.secret_key") is True

    def test_non_sensitive_keys(self):
        """Non-sensitive keys should return False."""
        assert is_sensitive_key("theme") is False
        assert is_sensitive_key("shell") is False
        assert is_sensitive_key("ai.provider") is False
        assert is_sensitive_key("ai.openai.model") is False
        assert is_sensitive_key("ai.openai.endpoint") is False

    def test_partial_match_not_sensitive(self):
        """Keys that partially match but don't end with sensitive pattern should not be sensitive."""
        assert is_sensitive_key("api_key") is False  # No dot prefix
        assert is_sensitive_key("api_key.something") is False
        assert is_sensitive_key("secret_key.other") is False
        assert is_sensitive_key("ai.api_key_backup") is False

    def test_empty_string(self):
        """Empty string should not be sensitive."""
        assert is_sensitive_key("") is False

    def test_case_sensitivity(self):
        """Key matching should be case-sensitive."""
        # These should not match because case is different
        assert is_sensitive_key("ai.openai.API_KEY") is False
        assert is_sensitive_key("ai.openai.Api_Key") is False
        assert is_sensitive_key("AI.OPENAI.API_KEY") is False


class TestConfigKeys:
    """Tests for ConfigKeys class."""

    def test_static_attributes(self):
        """ConfigKeys should have expected static attributes."""
        assert ConfigKeys.THEME == "theme"
        assert ConfigKeys.SHELL == "shell"
        assert ConfigKeys.DISCLAIMER_ACCEPTED == "disclaimer_accepted"
        assert ConfigKeys.AI_PROVIDER == "ai.provider"
        assert ConfigKeys.AI_AGENT_MODE == "ai.agent_mode"
        assert ConfigKeys.AI_ACTIVE_PROMPT == "ai.active_prompt"

    def test_ai_model_method(self):
        """ai_model() should return correct key format."""
        assert ConfigKeys.ai_model("openai") == "ai.openai.model"
        assert ConfigKeys.ai_model("anthropic") == "ai.anthropic.model"
        assert ConfigKeys.ai_model("ollama") == "ai.ollama.model"
        assert ConfigKeys.ai_model("custom_provider") == "ai.custom_provider.model"

    def test_ai_api_key_method(self):
        """ai_api_key() should return correct key format."""
        assert ConfigKeys.ai_api_key("openai") == "ai.openai.api_key"
        assert ConfigKeys.ai_api_key("anthropic") == "ai.anthropic.api_key"
        assert ConfigKeys.ai_api_key("groq") == "ai.groq.api_key"

    def test_ai_endpoint_method(self):
        """ai_endpoint() should return correct key format."""
        assert ConfigKeys.ai_endpoint("openai") == "ai.openai.endpoint"
        assert ConfigKeys.ai_endpoint("ollama") == "ai.ollama.endpoint"
        assert ConfigKeys.ai_endpoint("lm_studio") == "ai.lm_studio.endpoint"

    def test_ai_region_method(self):
        """ai_region() should return correct key format."""
        assert ConfigKeys.ai_region("azure") == "ai.azure.region"
        assert ConfigKeys.ai_region("bedrock") == "ai.bedrock.region"
        assert ConfigKeys.ai_region("google") == "ai.google.region"

    def test_generated_keys_sensitivity(self):
        """Keys generated by ConfigKeys should have correct sensitivity."""
        # API keys should be sensitive
        assert is_sensitive_key(ConfigKeys.ai_api_key("openai")) is True
        assert is_sensitive_key(ConfigKeys.ai_api_key("custom")) is True

        # Model and endpoint keys should not be sensitive
        assert is_sensitive_key(ConfigKeys.ai_model("openai")) is False
        assert is_sensitive_key(ConfigKeys.ai_endpoint("openai")) is False
        assert is_sensitive_key(ConfigKeys.ai_region("azure")) is False

    def test_special_characters_in_provider_name(self):
        """Provider names with special characters should work."""
        assert ConfigKeys.ai_model("provider-name") == "ai.provider-name.model"
        assert ConfigKeys.ai_api_key("provider_name") == "ai.provider_name.api_key"
        assert ConfigKeys.ai_endpoint("provider123") == "ai.provider123.endpoint"
