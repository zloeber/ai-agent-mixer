"""Service for loading and saving configuration from/to YAML files."""

import os
import re
from pathlib import Path
from typing import List, Tuple

import yaml
from pydantic import ValidationError

from app.schemas.config import RootConfig


def _substitute_env_vars(content: str) -> str:
    """Substitute environment variables in the format ${VAR_NAME}.
    
    Args:
        content: String content with possible ${VAR_NAME} placeholders
        
    Returns:
        Content with environment variables substituted
    """
    def replacer(match: re.Match) -> str:
        var_name = match.group(1)
        return os.environ.get(var_name, match.group(0))
    
    return re.sub(r'\$\{([A-Za-z0-9_]+)\}', replacer, content)


def load_config(filepath: str) -> RootConfig:
    """Load configuration from a YAML file.
    
    Args:
        filepath: Path to the YAML configuration file
        
    Returns:
        Validated RootConfig instance
        
    Raises:
        FileNotFoundError: If the file doesn't exist
        yaml.YAMLError: If the YAML is malformed
        ValidationError: If the configuration is invalid
    """
    file_path = Path(filepath)
    if not file_path.exists():
        raise FileNotFoundError(f"Configuration file not found: {filepath}")
    
    # Read file content
    with open(file_path, 'r', encoding='utf-8') as f:
        content = f.read()
    
    # Substitute environment variables
    content = _substitute_env_vars(content)
    
    # Parse YAML
    data = yaml.safe_load(content)
    
    # Validate with Pydantic
    config = RootConfig(**data)
    config.validate_starting_agent()
    
    return config


def save_config(config: RootConfig, filepath: str) -> None:
    """Save configuration to a YAML file.
    
    Args:
        config: RootConfig instance to save
        filepath: Path where to save the YAML file
    """
    file_path = Path(filepath)
    file_path.parent.mkdir(parents=True, exist_ok=True)
    
    # Convert to dict and then to YAML
    data = config.model_dump(mode='json', exclude_none=True)
    
    with open(file_path, 'w', encoding='utf-8') as f:
        yaml.dump(
            data,
            f,
            default_flow_style=False,
            sort_keys=False,
            allow_unicode=True,
            width=100
        )


def validate_config_yaml(yaml_content: str) -> Tuple[bool, List[str]]:
    """Validate YAML configuration content.
    
    Args:
        yaml_content: String containing YAML configuration
        
    Returns:
        Tuple of (is_valid, error_messages)
    """
    errors = []
    
    try:
        # Substitute environment variables
        content = _substitute_env_vars(yaml_content)
        
        # Parse YAML
        data = yaml.safe_load(content)
        
        if data is None:
            errors.append("Empty YAML content")
            return False, errors
        
        # Validate with Pydantic
        config = RootConfig(**data)
        config.validate_starting_agent()
        
        return True, []
        
    except yaml.YAMLError as e:
        errors.append(f"YAML parsing error: {str(e)}")
        return False, errors
        
    except ValidationError as e:
        for error in e.errors():
            loc = " -> ".join(str(l) for l in error['loc'])
            msg = error['msg']
            errors.append(f"{loc}: {msg}")
        return False, errors
        
    except Exception as e:
        errors.append(f"Unexpected error: {str(e)}")
        return False, errors


def merge_mcp_configs(
    global_servers: List[str],
    agent_servers: List[str]
) -> List[str]:
    """Merge global and agent-specific MCP server lists.
    
    Args:
        global_servers: List of global MCP server names
        agent_servers: List of agent-specific MCP server names
        
    Returns:
        Merged list of unique server names, preserving order
    """
    # Use dict.fromkeys to maintain order while removing duplicates
    merged = list(dict.fromkeys(global_servers + agent_servers))
    return merged
