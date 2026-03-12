"""Unit tests for gtin_extractor.config module."""

from __future__ import annotations

from gtin_extractor.config import DEFAULTS, Config, load_config


class TestConfigDefaults:
    """Verify default values on a freshly created Config."""

    def test_image_dir_default(self):
        cfg = Config()
        assert cfg.image_dir == DEFAULTS["image_dir"]

    def test_gemini_model_default(self):
        cfg = Config()
        assert cfg.gemini_model == DEFAULTS["gemini_model"]

    def test_max_retries_default(self):
        cfg = Config()
        assert cfg.max_retries == DEFAULTS["max_retries"]

    def test_log_level_default(self):
        cfg = Config()
        assert cfg.log_level == DEFAULTS["log_level"]

    def test_csv_output_none_by_default(self):
        cfg = Config()
        assert cfg.csv_output is None

    def test_gemini_api_key_none_by_default(self):
        cfg = Config()
        assert cfg.gemini_api_key is None


class TestLoadConfigFromYaml:
    """load_config should pick up values from a YAML file."""

    def test_yaml_overrides_defaults(self, tmp_config_dir):
        config_file = tmp_config_dir / "config.yaml"
        config_file.write_text(
            "image_dir: my_images\nlog_level: DEBUG\ngemini_model: gemini-1.5-pro\n",
            encoding="utf-8",
        )
        cfg = load_config(config_file=str(config_file))
        assert cfg.image_dir == "my_images"
        assert cfg.log_level == "DEBUG"
        assert cfg.gemini_model == "gemini-1.5-pro"

    def test_missing_yaml_file_uses_defaults(self, tmp_config_dir):
        cfg = load_config(config_file=str(tmp_config_dir / "nonexistent.yaml"))
        assert cfg.image_dir == DEFAULTS["image_dir"]

    def test_yaml_numeric_types_are_cast(self, tmp_config_dir):
        config_file = tmp_config_dir / "config.yaml"
        config_file.write_text("max_retries: 3\nbase_delay: 5.0\n", encoding="utf-8")
        cfg = load_config(config_file=str(config_file))
        assert cfg.max_retries == 3
        assert cfg.base_delay == 5.0

    def test_extra_yaml_keys_stored_in_extra(self, tmp_config_dir):
        config_file = tmp_config_dir / "config.yaml"
        config_file.write_text("custom_key: custom_value\n", encoding="utf-8")
        cfg = load_config(config_file=str(config_file))
        assert cfg.extra.get("custom_key") == "custom_value"


class TestLoadConfigFromEnv:
    """load_config should pick up GTIN_* environment variables."""

    def test_env_overrides_yaml(self, tmp_config_dir, monkeypatch):
        config_file = tmp_config_dir / "config.yaml"
        config_file.write_text("image_dir: from_yaml\n", encoding="utf-8")

        monkeypatch.setenv("GTIN_IMAGE_DIR", "from_env")
        cfg = load_config(config_file=str(config_file))
        assert cfg.image_dir == "from_env"

    def test_gemini_key_from_env(self, monkeypatch):
        monkeypatch.setenv("GTIN_GEMINI_API_KEY", "test-api-key")
        cfg = load_config(config_file="nonexistent_config.yaml")
        assert cfg.gemini_api_key == "test-api-key"

    def test_limit_from_env_is_int(self, monkeypatch):
        monkeypatch.setenv("GTIN_LIMIT", "10")
        cfg = load_config(config_file="nonexistent_config.yaml")
        assert cfg.limit == 10

    def test_env_cleanup_after_test(self, monkeypatch):
        """Environment variables set via monkeypatch are cleaned up automatically."""
        monkeypatch.setenv("GTIN_LOG_LEVEL", "WARNING")
        cfg = load_config(config_file="nonexistent_config.yaml")
        assert cfg.log_level == "WARNING"
