import json
from copy import deepcopy
from pathlib import Path
from typing import Dict, Self


class Config:
    CONFIG_FILE = Path("/home/antares/coding/pyblade/pyblade/pyblade.json")

    DEFAULTS = {
        "templates_dir": "templates",
        "components_dir": "templates.components",
        "liveblade": {"paginator": "undefined", "components_dir": "liveblade", "templates_dir": "templates.liveblade"},
    }

    def __init__(
        self, data: Dict | None = None, parent: Self | None = None, key: str | None = None, defaults: Dict | None = None
    ):
        self._parent = parent
        self._key = key
        self._defaults = defaults if defaults is not None else deepcopy(Config.DEFAULTS)
        self._data = data if data is not None else {}

        if parent is None:
            self.load()

    def load(self):
        if Config.CONFIG_FILE.exists():
            with open(Config.CONFIG_FILE, "r") as file:
                self._data = json.load(file)

    def save(self):
        if self._parent:
            return self._parent.save()

        with open(Config.CONFIG_FILE, "w") as file:
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
            return Config(data=self._data.get(key, {}), parent=self, key=key, defaults=self._defaults.get(key, {}))

        return value

    def __setattr__(self, key, value):
        if key in {"_data", "_parent", "_key", "_defaults", "CONFIG_FILE"}:
            return super().__setattr__(key, value)

        self._data[key] = value
        if self._parent and self._key:
            self._parent._data[self._key] = self._data


settings = Config()
