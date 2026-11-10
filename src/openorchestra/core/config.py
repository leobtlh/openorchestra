"""Project configuration loading for OpenOrchestra."""

import logging
from pathlib import Path
from typing import Any, Dict, Optional, Union

import yaml

logger = logging.getLogger(__name__)

DEFAULT_CONFIG_PATH = ".openorchestra/config.yaml"


def load_config(path: Optional[Union[str, Path]] = None) -> Dict[str, Any]:
    """Load a YAML configuration mapping, returning an empty mapping on failure."""
    config_path = Path(path) if path is not None else Path(DEFAULT_CONFIG_PATH)
    if not config_path.is_file():
        return {}

    try:
        data = yaml.safe_load(config_path.read_text(encoding="utf-8"))
    except (OSError, UnicodeError, yaml.YAMLError) as exc:
        logger.warning("Could not load configuration from %s: %s", config_path, exc)
        return {}

    if not isinstance(data, dict):
        logger.warning("Ignoring configuration without a mapping: %s", config_path)
        return {}
    return data
