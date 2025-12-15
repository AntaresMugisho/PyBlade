import json
from copy import deepcopy
from pathlib import Path
from typing import Dict, Self

from pyblade.utils import get_project_root


class Config:

    DEFAULTS = {
        "templates_dir": Path("templates"),
        "components_dir": Path("components"),
        "commands_dir": Path("management/commands"),
        "stubs_dir": Path(__file__).parent / "cli/stubs",
        "liveblade": {
            "paginator": None,
            "components_dir": Path("liveblade"),
            "templates_dir": Path("liveblade"),
        },
    }

    def __init__(
        self,
        config_file: str = get_project_root() / "pyblade.json",
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
            json.dump(self._data, file, indent=4)

    def __str__(self):
        if self._parent and self.name:
            return self.name

        return super().__str__()

    def __getattribute__(self, key):

        if key.startswith("_") or key in {"load", "save"}:
            return super().__getattribute__(key)

        value = self._data.get(key, self._defaults.get(key))
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


settings = Config()
