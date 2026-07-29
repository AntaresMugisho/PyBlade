import json
from copy import deepcopy
from pathlib import Path
from typing import Dict, Self

from pyblade.utils import get_project_root


class Config:

    DEFAULTS = {
        "templates_dir": "templates",
        "components_dir": "components",
        "commands_dir": "management/commands",
        "default_locale": "en",
        "locale_dir": "locale",
        "stubs_dir": str(Path(__file__).parent / "cli/stubs"),
        "live": {
            "paginator": None,
            "classes_dir": "live",
            "templates_dir": "live",
        },
    }

    def __init__(
        self,
        config_file: str = str(get_project_root() / "pyblade.json"),
        data: Dict | None = None,
        parent: Self | None = None,
        key: str | None = None,
        defaults: Dict | None = None,
    ):
        self._config_file = Path(config_file)
        self._data = data if data is not None else {}
        self._parent = parent
        self._key = key
        self._defaults = defaults if defaults is not None else deepcopy(Config.DEFAULTS)

        if parent is None:
            self.load()

    def load(self):
        if self._config_file.exists():
            with open(self._config_file, "r") as file:
                self._data = json.load(file)
        else:
            self._data = deepcopy(self._defaults)

    def save(self):
        if self._parent:
            return self._parent.save()

        with open(self._config_file, "w") as file:
            json.dump({k: v for k, v in self._data.items() if k not in self._defaults}, file, indent=4)

    def __str__(self):
        if self._parent and self.name:
            return self.name

        return super().__str__()

    def __getattribute__(self, key):

        if key.startswith("_") or key in {"load", "save", "DEBUG"}:
            return super().__getattribute__(key)

        value = self._data.get(key, self._defaults.get(key))

        if key.endswith(("_dir", "_path")):
            return Path(value)

        if isinstance(value, dict):
            return Config(
                config_file=self._config_file,
                data=self._data.get(key, {}),
                parent=self,
                key=key,
                defaults=self._defaults.get(key, {}),
            )

        return value

    def __setattr__(self, key, value):
        if key in {"_data", "_parent", "_key", "_defaults", "_config_file"}:
            return super().__setattr__(key, value)

        self._data[key] = value
        if self._parent and self._key:
            self._parent._data[self._key] = self._data

    @property
    def DEBUG(self) -> bool:
        """Auto-detect debug mode from framework if not explicitly set."""

        if self.framework == "django":
            try:
                from django.conf import settings

                return settings.DEBUG
            except Exception:
                return False

        elif self.framework == "flask":
            try:
                from flask import current_app

                return current_app.debug
            except Exception:
                return False

        elif self.framework == "fastapi":
            # FastAPI doesn't have built-in DEBUG, so we check environment
            import os

            return os.getenv("DEBUG", "False").lower() == "true"

        return False


settings = Config()


# The content above will be replaced with this one cause we are migrating from pyblade.json to pyblade.toml

import sys
from pathlib import Path
from typing import Any, Dict
from django.conf import settings

# Native TOML parser for Python 3.11+
if sys.version_info >= (3, 11):
    import tomllib
else:
    import tomli as tomllib


# Default framework configuration in lowercase
DEFAULT_CONFIG: Dict[str, Any] = {
    "core": {
        "inject_assets": True,
        "assets_url": "/pyblade/assets/pyblade.js",
    },
    "security": {
        "verify_checksum": True,
    },
    "compiler": {
        "cache_templates": True,
    },
}


class ConfigObject:
    """
    Wrapper class allowing attribute-style dot notation access to settings.
    Example: config.core.inject_assets
    """

    def __init__(self, data: Dict[str, Any]) -> None:
        for key, value in data.items():
            key_lower = key.lower()
            if isinstance(value, dict):
                # Recursively wrap nested dictionaries
                setattr(self, key_lower, ConfigObject(value))
            else:
                setattr(self, key_lower, value)

    def __getattr__(self, name: str) -> Any:
        # Fallback for undefined attributes
        return None

    def __repr__(self) -> str:
        return f"<PyBladeConfig {self.__dict__}>"

    def get(self, key_path: str, default: Any = None) -> Any:
        """
        Accesses nested dictionary keys using dot notation.
        Example: config.get("core.inject_assets")
        """
        return getattr(self, key_path, default)


def _lowercase_keys(dictionary: Dict[str, Any]) -> Dict[str, Any]:
    """
    Recursively converts all dictionary keys to lowercase.
    Allows support for uppercase Django settings or ENV-like dictionaries.
    """
    lowercased = {}
    for key, value in dictionary.items():
        key_lower = key.lower()
        if isinstance(value, dict):
            lowercased[key_lower] = _lowercase_keys(value)
        else:
            lowercased[key_lower] = value
    return lowercased


def _deep_merge(base: Dict[str, Any], override: Dict[str, Any]) -> Dict[str, Any]:
    """
    Recursively merges user overrides into the base configuration dictionary.
    """
    merged = base.copy()
    for key, value in override.items():
        if isinstance(value, dict) and key in merged and isinstance(merged[key], dict):
            merged[key] = _deep_merge(merged[key], value)
        else:
            merged[key] = value
    return merged


def _load_toml_overrides() -> Dict[str, Any]:
    """
    Reads configuration overrides from 'pyblade.toml' or '[tool.pyblade]' inside 'pyproject.toml'.
    """
    # 1. Standalone pyblade.toml
    pyblade_toml = Path("pyblade.toml")
    if pyblade_toml.exists():
        with open(pyblade_toml, "rb") as f:
            return tomllib.load(f)

    # 2. Section inside pyproject.toml
    pyproject_toml = Path("pyproject.toml")
    if pyproject_toml.exists():
        with open(pyproject_toml, "rb") as f:
            data = tomllib.load(f)
            return data.get("tool", {}).get("pyblade", {})

    return {}


def build_config() -> ConfigObject:
    """
    Builds the final ConfigObject by merging defaults, TOML overrides,
    and optional Django settings.
    """
    merged = DEFAULT_CONFIG.copy()

    # Merge TOML overrides
    toml_overrides = _load_toml_overrides()
    if toml_overrides:
        merged = _deep_merge(merged, _lowercase_keys(toml_overrides))

    # Merge Django settings if defined (e.g., PYBLADE = {"CORE": {"INJECT_ASSETS": False}})
    django_overrides = getattr(settings, "PYBLADE", {})
    if django_overrides:
        merged = _deep_merge(merged, _lowercase_keys(django_overrides))

    # Convert final dictionary into dot-accessible object
    return ConfigObject(merged)


# Global singleton instance
config = build_config()
