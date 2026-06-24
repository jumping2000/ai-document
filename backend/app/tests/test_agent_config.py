"""Tests for agent_config loader."""

from __future__ import annotations

from app.core.agent_config import load_agent_config


class TestLoadAgentConfig:
    def test_load_requirement_config_returns_dict(self) -> None:
        config = load_agent_config("requirement")
        assert isinstance(config, dict)
        assert config["agent"] == "requirement"
        assert "system_prompt" in config
        assert "output_schema" in config
        assert "critical_fields" in config

    def test_load_procurement_config_has_standards(self) -> None:
        config = load_agent_config("procurement")
        assert config["agent"] == "procurement"
        assert "parameters" in config
        assert "standards" in config["parameters"]
        assert len(config["parameters"]["standards"]) >= 5

    def test_load_quality_config_has_checklist(self) -> None:
        config = load_agent_config("quality")
        assert config["agent"] == "quality"
        assert "quality_checklist" in config
        assert len(config["quality_checklist"]) == 8
        assert "quality_threshold" in config["parameters"]

    def test_load_lead_writer_has_templates(self) -> None:
        config = load_agent_config("lead_writer")
        assert config["agent"] == "lead_writer"
        assert "default_template_capitolato" in config["parameters"]
        assert "default_template_requisiti" in config["parameters"]

    def test_load_orchestrator_has_retries(self) -> None:
        config = load_agent_config("orchestrator")
        assert config["agent"] == "orchestrator"
        assert "max_retries" in config["parameters"]
        assert "quality_threshold" in config["parameters"]

    def test_missing_config_returns_empty_dict(self) -> None:
        config = load_agent_config("nonexistent")
        assert config == {}

    def test_config_is_cached(self) -> None:
        config1 = load_agent_config("requirement")
        config2 = load_agent_config("requirement")
        assert config1 is config2  # Same object from lru_cache
