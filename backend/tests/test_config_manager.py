"""Tests for Configuration Manager functionality."""

import os
import tempfile
from pathlib import Path
from typing import Any, Dict

import pytest
import yaml
from pydantic import ValidationError

from app.schemas.config import (
    AgentConfig,
    ConversationConfig,
    InitializationConfig,
    LoggingConfig,
    LogLevel,
    MCPServerConfig,
    MCPServersConfig,
    ModelConfig,
    RootConfig,
    TerminationConditions,
)
from app.services.config_manager import (
    load_config,
    merge_mcp_configs,
    save_config,
    validate_config_yaml,
)


@pytest.fixture
def valid_config_dict() -> Dict[str, Any]:
    """Create a valid configuration dictionary."""
    return {
        "version": "1.0",
        "metadata": {
            "name": "Test Configuration",
            "description": "A test configuration",
        },
        "conversation": {
            "starting_agent": "agent_a",
            "max_cycles": 5,
            "turn_timeout": 120,
            "termination_conditions": {
                "keyword_triggers": ["goodbye", "end"],
                "silence_detection": 3,
            },
        },
        "agents": {
            "agent_a": {
                "name": "Agent A",
                "persona": "You are a friendly assistant.",
                "model": {
                    "provider": "ollama",
                    "url": "http://localhost:11434",
                    "model_name": "llama2",
                    "thinking": False,
                    "parameters": {"temperature": 0.7},
                },
                "mcp_servers": [],
            },
            "agent_b": {
                "name": "Agent B",
                "persona": "You are a knowledgeable expert.",
                "model": {
                    "provider": "ollama",
                    "url": "http://localhost:11434",
                    "model_name": "mistral",
                    "thinking": True,
                    "parameters": {"temperature": 0.8},
                },
                "mcp_servers": ["search"],
            },
        },
        "mcp_servers": {
            "global_servers": [
                {
                    "name": "filesystem",
                    "command": "mcp-server-filesystem",
                    "args": ["/tmp"],
                    "env": {},
                }
            ],
        },
        "initialization": {
            "system_prompt_template": "You are {{ agent.name }}",
            "first_message": "Hello, let's discuss AI.",
        },
        "logging": {
            "level": "INFO",
            "include_thoughts": True,
            "output_directory": None,
        },
    }


@pytest.fixture
def temp_config_file(valid_config_dict: Dict[str, Any]) -> str:
    """Create a temporary config file with valid configuration."""
    with tempfile.NamedTemporaryFile(
        mode="w", suffix=".yaml", delete=False
    ) as f:
        yaml.dump(valid_config_dict, f)
        return f.name


class TestModelConfig:
    """Test ModelConfig validation."""

    def test_valid_model_config(self) -> None:
        """Test valid model configuration."""
        config = ModelConfig(
            provider="ollama",
            url="http://localhost:11434",
            model_name="llama2",
            thinking=True,
            parameters={"temperature": 0.7},
        )
        assert config.provider == "ollama"
        assert config.url == "http://localhost:11434"
        assert config.model_name == "llama2"
        assert config.thinking is True
        assert config.parameters["temperature"] == 0.7

    def test_invalid_url_missing_protocol(self) -> None:
        """Test that URL without protocol raises error."""
        with pytest.raises(ValidationError) as exc_info:
            ModelConfig(
                url="localhost:11434",
                model_name="llama2",
            )
        assert "URL must start with http://" in str(exc_info.value)

    def test_invalid_model_name_special_chars(self) -> None:
        """Test that model name with invalid characters raises error."""
        with pytest.raises(ValidationError) as exc_info:
            ModelConfig(
                url="http://localhost:11434",
                model_name="llama2@invalid",
            )
        assert "Model name can only contain" in str(exc_info.value)

    def test_valid_model_name_with_version(self) -> None:
        """Test model name with version format."""
        config = ModelConfig(
            url="http://localhost:11434",
            model_name="llama2:7b-chat",
        )
        assert config.model_name == "llama2:7b-chat"


class TestMCPServerConfig:
    """Test MCPServerConfig validation."""

    def test_valid_mcp_config(self) -> None:
        """Test valid MCP server configuration."""
        config = MCPServerConfig(
            name="test_server",
            command="mcp-server-test",
            args=["arg1", "arg2"],
            env={"KEY": "value"},
        )
        assert config.name == "test_server"
        assert len(config.args) == 2
        assert config.env["KEY"] == "value"

    def test_invalid_server_name_special_chars(self) -> None:
        """Test that server name with invalid characters raises error."""
        with pytest.raises(ValidationError) as exc_info:
            MCPServerConfig(
                name="server@invalid!",
                command="test",
            )
        assert "Server name can only contain" in str(exc_info.value)

    def test_mcp_config_with_defaults(self) -> None:
        """Test MCP config with default values."""
        config = MCPServerConfig(name="minimal", command="test")
        assert config.args == []
        assert config.env == {}


class TestRootConfig:
    """Test RootConfig validation."""

    def test_valid_root_config(self, valid_config_dict: Dict[str, Any]) -> None:
        """Test valid root configuration."""
        config = RootConfig(**valid_config_dict)
        assert config.version == "1.0"
        assert len(config.agents) == 2
        assert "agent_a" in config.agents
        assert "agent_b" in config.agents

    def test_insufficient_agents(self, valid_config_dict: Dict[str, Any]) -> None:
        """Test that less than two agents raises error."""
        valid_config_dict["agents"] = {
            "agent_a": valid_config_dict["agents"]["agent_a"]
        }
        with pytest.raises(ValidationError) as exc_info:
            RootConfig(**valid_config_dict)
        assert "At least two agents must be configured" in str(exc_info.value)

    def test_invalid_starting_agent(
        self, valid_config_dict: Dict[str, Any]
    ) -> None:
        """Test that invalid starting agent raises error."""
        valid_config_dict["conversation"]["starting_agent"] = "nonexistent_agent"
        config = RootConfig(**valid_config_dict)
        with pytest.raises(ValueError) as exc_info:
            config.validate_starting_agent()
        assert "Starting agent 'nonexistent_agent' not found" in str(exc_info.value)

    def test_valid_starting_agent(self, valid_config_dict: Dict[str, Any]) -> None:
        """Test valid starting agent validation."""
        config = RootConfig(**valid_config_dict)
        config.validate_starting_agent()  # Should not raise


class TestLoadConfig:
    """Test load_config function."""

    def test_load_valid_config(self, temp_config_file: str) -> None:
        """Test loading a valid configuration file."""
        config = load_config(temp_config_file)
        assert isinstance(config, RootConfig)
        assert config.version == "1.0"
        assert len(config.agents) == 2

        # Cleanup
        os.unlink(temp_config_file)

    def test_load_nonexistent_file(self) -> None:
        """Test loading a file that doesn't exist."""
        with pytest.raises(FileNotFoundError) as exc_info:
            load_config("/nonexistent/file.yaml")
        assert "Configuration file not found" in str(exc_info.value)

    def test_load_malformed_yaml(self) -> None:
        """Test loading a malformed YAML file."""
        with tempfile.NamedTemporaryFile(
            mode="w", suffix=".yaml", delete=False
        ) as f:
            f.write("invalid: yaml: content: [unclosed")
            temp_file = f.name

        try:
            with pytest.raises(yaml.YAMLError):
                load_config(temp_file)
        finally:
            os.unlink(temp_file)

    def test_load_invalid_config(self) -> None:
        """Test loading a YAML file with invalid configuration."""
        invalid_config = {"version": "1.0", "agents": {}}  # Missing required fields

        with tempfile.NamedTemporaryFile(
            mode="w", suffix=".yaml", delete=False
        ) as f:
            yaml.dump(invalid_config, f)
            temp_file = f.name

        try:
            with pytest.raises(ValidationError):
                load_config(temp_file)
        finally:
            os.unlink(temp_file)

    def test_environment_variable_substitution(
        self, valid_config_dict: Dict[str, Any]
    ) -> None:
        """Test that environment variables are substituted correctly."""
        # Set environment variable
        os.environ["TEST_OLLAMA_URL"] = "http://test.example.com:11434"

        # Create config with env var placeholder
        valid_config_dict["agents"]["agent_a"]["model"]["url"] = "${TEST_OLLAMA_URL}"

        with tempfile.NamedTemporaryFile(
            mode="w", suffix=".yaml", delete=False
        ) as f:
            yaml.dump(valid_config_dict, f)
            temp_file = f.name

        try:
            config = load_config(temp_file)
            assert config.agents["agent_a"].model.url == "http://test.example.com:11434"
        finally:
            os.unlink(temp_file)
            del os.environ["TEST_OLLAMA_URL"]

    def test_missing_environment_variable(
        self, valid_config_dict: Dict[str, Any]
    ) -> None:
        """Test that missing environment variables are left as-is."""
        # Create config with env var placeholder that doesn't exist
        valid_config_dict["agents"]["agent_a"]["model"]["url"] = (
            "${NONEXISTENT_VAR}"
        )

        with tempfile.NamedTemporaryFile(
            mode="w", suffix=".yaml", delete=False
        ) as f:
            yaml.dump(valid_config_dict, f)
            temp_file = f.name

        try:
            # Should fail validation since ${NONEXISTENT_VAR} is not a valid URL
            with pytest.raises(ValidationError):
                load_config(temp_file)
        finally:
            os.unlink(temp_file)


class TestSaveConfig:
    """Test save_config function."""

    def test_save_and_load_roundtrip(
        self, valid_config_dict: Dict[str, Any]
    ) -> None:
        """Test that saving and loading config produces identical result."""
        config = RootConfig(**valid_config_dict)

        with tempfile.NamedTemporaryFile(
            mode="w", suffix=".yaml", delete=False
        ) as f:
            temp_file = f.name

        try:
            # Save config
            save_config(config, temp_file)

            # Load it back
            loaded_config = load_config(temp_file)

            # Compare key fields
            assert loaded_config.version == config.version
            assert loaded_config.conversation.starting_agent == config.conversation.starting_agent
            assert len(loaded_config.agents) == len(config.agents)
            assert (
                loaded_config.agents["agent_a"].model.url
                == config.agents["agent_a"].model.url
            )
        finally:
            if os.path.exists(temp_file):
                os.unlink(temp_file)

    def test_save_creates_directory(
        self, valid_config_dict: Dict[str, Any]
    ) -> None:
        """Test that save_config creates parent directories if needed."""
        config = RootConfig(**valid_config_dict)

        with tempfile.TemporaryDirectory() as temp_dir:
            nested_path = Path(temp_dir) / "nested" / "dirs" / "config.yaml"

            save_config(config, str(nested_path))

            assert nested_path.exists()
            assert nested_path.is_file()


class TestValidateConfigYAML:
    """Test validate_config_yaml function."""

    def test_validate_valid_yaml(self, valid_config_dict: Dict[str, Any]) -> None:
        """Test validating valid YAML content."""
        yaml_content = yaml.dump(valid_config_dict)
        is_valid, errors = validate_config_yaml(yaml_content)

        assert is_valid is True
        assert errors == []

    def test_validate_empty_yaml(self) -> None:
        """Test validating empty YAML content."""
        is_valid, errors = validate_config_yaml("")

        assert is_valid is False
        assert len(errors) > 0
        assert "Empty YAML content" in errors[0]

    def test_validate_malformed_yaml(self) -> None:
        """Test validating malformed YAML."""
        is_valid, errors = validate_config_yaml("invalid: yaml: [unclosed")

        assert is_valid is False
        assert len(errors) > 0
        assert "YAML parsing error" in errors[0]

    def test_validate_invalid_config(self) -> None:
        """Test validating YAML with invalid configuration."""
        invalid_yaml = """
version: "1.0"
conversation:
  starting_agent: "agent_a"
  max_cycles: 0
agents: {}
"""
        is_valid, errors = validate_config_yaml(invalid_yaml)

        assert is_valid is False
        assert len(errors) > 0

    def test_validate_missing_required_fields(self) -> None:
        """Test validating YAML with missing required fields."""
        incomplete_yaml = """
version: "1.0"
agents:
  agent_a:
    name: "Agent A"
"""
        is_valid, errors = validate_config_yaml(incomplete_yaml)

        assert is_valid is False
        assert len(errors) > 0

    def test_validate_with_env_vars(self) -> None:
        """Test validation with environment variable substitution."""
        os.environ["TEST_URL"] = "http://localhost:11434"

        yaml_with_env = """
version: "1.0"
conversation:
  starting_agent: "agent_a"
  max_cycles: 5
agents:
  agent_a:
    name: "Agent A"
    persona: "Test"
    model:
      url: "${TEST_URL}"
      model_name: "llama2"
  agent_b:
    name: "Agent B"
    persona: "Test"
    model:
      url: "http://localhost:11434"
      model_name: "llama2"
initialization:
  first_message: "Hello"
"""

        try:
            is_valid, errors = validate_config_yaml(yaml_with_env)
            assert is_valid is True
            assert errors == []
        finally:
            del os.environ["TEST_URL"]


class TestMergeMCPConfigs:
    """Test merge_mcp_configs function."""

    def test_merge_empty_lists(self) -> None:
        """Test merging two empty lists."""
        result = merge_mcp_configs([], [])
        assert result == []

    def test_merge_with_empty_global(self) -> None:
        """Test merging with empty global list."""
        agent_servers = ["server1", "server2"]
        result = merge_mcp_configs([], agent_servers)
        assert result == ["server1", "server2"]

    def test_merge_with_empty_agent(self) -> None:
        """Test merging with empty agent list."""
        global_servers = ["global1", "global2"]
        result = merge_mcp_configs(global_servers, [])
        assert result == ["global1", "global2"]

    def test_merge_no_duplicates(self) -> None:
        """Test merging lists with no duplicates."""
        global_servers = ["global1", "global2"]
        agent_servers = ["agent1", "agent2"]
        result = merge_mcp_configs(global_servers, agent_servers)
        assert result == ["global1", "global2", "agent1", "agent2"]

    def test_merge_with_duplicates(self) -> None:
        """Test merging lists with duplicates."""
        global_servers = ["server1", "server2", "server3"]
        agent_servers = ["server2", "server4"]
        result = merge_mcp_configs(global_servers, agent_servers)

        # Should maintain order and remove duplicates
        assert result == ["server1", "server2", "server3", "server4"]
        assert len(result) == 4

    def test_merge_preserves_order(self) -> None:
        """Test that merge preserves order."""
        global_servers = ["z", "y", "x"]
        agent_servers = ["w", "v"]
        result = merge_mcp_configs(global_servers, agent_servers)

        # Should preserve the order: global first, then agent
        assert result == ["z", "y", "x", "w", "v"]

    def test_merge_all_duplicates(self) -> None:
        """Test merging when all servers are duplicates."""
        global_servers = ["server1", "server2"]
        agent_servers = ["server1", "server2"]
        result = merge_mcp_configs(global_servers, agent_servers)

        assert result == ["server1", "server2"]
        assert len(result) == 2


class TestConversationConfig:
    """Test ConversationConfig validation."""

    def test_valid_conversation_config(self) -> None:
        """Test valid conversation configuration."""
        config = ConversationConfig(
            starting_agent="agent_a",
            max_cycles=10,
            turn_timeout=120,
        )
        assert config.starting_agent == "agent_a"
        assert config.max_cycles == 10
        assert config.turn_timeout == 120

    def test_invalid_max_cycles_zero(self) -> None:
        """Test that max_cycles must be at least 1."""
        with pytest.raises(ValidationError) as exc_info:
            ConversationConfig(
                starting_agent="agent_a",
                max_cycles=0,
            )
        assert "greater than or equal to 1" in str(exc_info.value)

    def test_invalid_turn_timeout_zero(self) -> None:
        """Test that turn_timeout must be at least 1."""
        with pytest.raises(ValidationError) as exc_info:
            ConversationConfig(
                starting_agent="agent_a",
                turn_timeout=0,
            )
        assert "greater than or equal to 1" in str(exc_info.value)

    def test_termination_conditions_defaults(self) -> None:
        """Test termination conditions with defaults."""
        config = ConversationConfig(
            starting_agent="agent_a",
        )
        assert config.termination_conditions is not None
        assert config.termination_conditions.keyword_triggers == []
        assert config.termination_conditions.silence_detection is None


class TestLoggingConfig:
    """Test LoggingConfig validation."""

    def test_valid_logging_config(self) -> None:
        """Test valid logging configuration."""
        config = LoggingConfig(
            level=LogLevel.DEBUG,
            include_thoughts=False,
            output_directory="/var/log/app",
        )
        assert config.level == LogLevel.DEBUG
        assert config.include_thoughts is False
        assert config.output_directory == "/var/log/app"

    def test_logging_config_defaults(self) -> None:
        """Test logging config with defaults."""
        config = LoggingConfig()
        assert config.level == LogLevel.INFO
        assert config.include_thoughts is True
        assert config.output_directory is None
