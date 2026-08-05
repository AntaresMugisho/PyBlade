import shutil
import tempfile
import unittest
from pathlib import Path

from pyblade.config import settings
from pyblade.engine import loader
from pyblade.engine.exceptions import TemplateNotFoundError


class TestDefaultLoader(unittest.TestCase):
    """Where a template is looked for when nobody said."""

    def setUp(self):
        self.project_dir = Path(tempfile.mkdtemp())
        (self.project_dir / "templates" / "layouts").mkdir(parents=True)
        (self.project_dir / "templates" / "layouts" / "app.html").write_text("<html>{{ slot }}</html>")

        self._saved_dirs = list(loader._default_loader._template_dirs)
        loader._default_loader._template_dirs = []

        self._saved = settings._data.get("templates_dir")
        settings._data["templates_dir"] = str(self.project_dir / "templates")

    def tearDown(self):
        loader._default_loader._template_dirs = self._saved_dirs
        if self._saved is None:
            settings._data.pop("templates_dir", None)
        else:
            settings._data["templates_dir"] = self._saved
        shutil.rmtree(self.project_dir, ignore_errors=True)

    def test_the_templates_directory_of_the_project_is_searched(self):
        """A page rendered before any backend was built still finds its layout."""
        template = loader.load_template("layouts.app")

        self.assertEqual(template.content, "<html>{{ slot }}</html>")

    def test_a_template_that_is_nowhere_is_still_reported(self):
        with self.assertRaises(TemplateNotFoundError):
            loader.load_template("layouts.nowhere")

    def test_a_configured_directory_comes_first(self):
        other = self.project_dir / "other"
        (other / "layouts").mkdir(parents=True)
        (other / "layouts" / "app.html").write_text("<html>from the configured one</html>")
        loader._default_loader.add_directories([other])

        self.assertEqual(loader.load_template("layouts.app").content, "<html>from the configured one</html>")
