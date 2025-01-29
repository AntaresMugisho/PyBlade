import json
import os
from pathlib import Path


class PyBladeSettingsManager:
    def __init__(self):
        self.pyblade_settings = self.deserialize()
        self.pyblade_root = self.find_project_root()

    def deserialize(self):
        settings = {}
        try:
            with open("pyblade.json", "r") as f:
                settings = json.load(f)
        except FileNotFoundError:
            pass

        return settings

    def serialize(self, settings):
        pyblade_dir = self.pyblade_root
        with open(pyblade_dir / "pyblade.json", "w") as f:
            json.dump(settings, f, indent=4)

    @property
    def pyblade_version(self):
        return self.pyblade_settings.get("version")

    @property
    def framework(self):
        return self.pyblade_settings.get("framework")

    @property
    def css_framework(self):
        return self.pyblade_settings.get("css_framework")

    @property
    def project_name(self):
        return self.pyblade_settings.get("name")

    def find_project_root(self, marker_file="pyblade.json"):
        """Find project root folder"""

        # First try environment variable if set
        if "PYBLADE_ROOT" in os.environ:
            root = Path(os.environ["PYBLADE_ROOT"])
            if root.exists():
                return root

        # Otherwise search upwards for marker file
        current = Path.cwd()
        while current != current.parent:
            if (current / marker_file).exists():
                return current
            current = current.parent

        return None

    def is_empty(self):
        return not self.pyblade_settings


settings = PyBladeSettingsManager()
