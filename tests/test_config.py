"""How a project says the way it is put together.

A project describes itself in a `pyblade.toml`, or in the `[tool.pyblade]`
table of its `pyproject.toml`. Everything has a default, so the file holds only
what the project wants different, and PyBlade writes it back the same way.

What the framework says comes on top of the file, and it is asked for that only
once it is able to answer -- the thing that makes importing PyBlade before
`django.setup()` safe, which is what a management command and this very test
suite do.
"""

import json
import shutil
import tempfile
import unittest
from pathlib import Path

from django.test import override_settings

from pyblade.config import Config, find_config_file


class ConfigTestCase(unittest.TestCase):
    def setUp(self):
        self.root = Path(tempfile.mkdtemp())
        self.addCleanup(shutil.rmtree, self.root, ignore_errors=True)

    def write(self, name, content):
        path = self.root / name
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(content)

        return path

    def config(self, name="pyblade.toml"):
        return Config(config_file=self.root / name)


class TestWhatAProjectGetsWithoutSayingAnything(ConfigTestCase):
    def test_every_key_has_a_default(self):
        config = self.config()

        self.assertEqual(config.paths.templates, Path("templates"))
        self.assertEqual(config.paths.components, Path("components"))
        self.assertEqual(config.i18n.locale, "en")
        self.assertEqual(config.live.classes_dir, Path("live"))
        self.assertEqual(config.live.throttle.actions, "120/minute")

    def test_a_key_naming_a_place_comes_back_as_a_path(self):
        self.assertIsInstance(self.config().paths.templates, Path)

    def test_a_place_the_project_never_named_is_nothing_rather_than_here(self):
        """Path('') is the current directory, which is not what 'unset' means."""
        self.assertIsNone(self.config().paths.core)

    def test_a_setting_pyblade_has_never_had_says_so(self):
        with self.assertRaises(AttributeError) as caught:
            self.config().stack.nonsense

        self.assertIn("no 'stack.nonsense' setting", str(caught.exception))

    def test_a_key_asked_for_the_way_it_used_to_be_says_where_it_went(self):
        """Code written against the flat configuration is told, not left guessing."""
        with self.assertRaises(AttributeError) as caught:
            self.config().templates_dir

        self.assertIn("moved to 'paths.templates'", str(caught.exception))


class TestReadingTheFile(ConfigTestCase):
    def test_pyblade_toml_is_read(self):
        self.write("pyblade.toml", '[project]\nname = "shop"\n\n[i18n]\nlocale = "fr"\n')
        config = self.config()

        self.assertEqual(config.project.name, "shop")
        self.assertEqual(config.i18n.locale, "fr")

    def test_what_the_file_leaves_out_keeps_its_default(self):
        self.write("pyblade.toml", '[i18n]\nlocale = "fr"\n')

        self.assertEqual(self.config().i18n.fallback_locale, "en")

    def test_a_table_may_be_written_in_capitals(self):
        """Django users write settings in capitals, and are not made to stop."""
        self.write("pyblade.toml", '[I18N]\nLOCALE = "fr"\n')

        self.assertEqual(self.config().i18n.locale, "fr")

    def test_a_pyproject_may_hold_it_instead(self):
        self.write("pyproject.toml", '[project]\nname = "x"\n\n[tool.pyblade.i18n]\nlocale = "fr"\n')

        self.assertEqual(self.config("pyproject.toml").i18n.locale, "fr")

    def test_a_pyproject_holding_nothing_of_ours_is_not_a_pyblade_project(self):
        """Or every Python project on the machine would look like one."""
        self.write("pyproject.toml", '[project]\nname = "x"\n')

        self.assertIsNone(find_config_file(self.root))

    def test_the_file_is_looked_for_upwards(self):
        """A command run deep inside a project still finds the project."""
        self.write("pyblade.toml", '[project]\nname = "shop"\n')
        deep = self.root / "app" / "components" / "live"
        deep.mkdir(parents=True)

        self.assertEqual(find_config_file(deep), self.root / "pyblade.toml")

    def test_a_project_with_no_file_at_all_still_works(self):
        """Nothing describes this directory, and everything still has an answer."""
        self.assertIsNone(find_config_file(self.root))
        self.assertEqual(self.config().i18n.locale, "en")


class TestWritingTheFile(ConfigTestCase):
    def test_only_what_differs_from_a_default_is_written(self):
        """So that a project follows PyBlade when PyBlade changes its mind."""
        config = self.config()
        config.project.name = "shop"
        config.save()

        written = (self.root / "pyblade.toml").read_text()

        self.assertIn('name = "shop"', written)
        self.assertNotIn("fallback_locale", written)
        self.assertNotIn("120/minute", written)

    def test_it_is_written_in_the_order_the_schema_declares(self):
        config = self.config()
        config.i18n.locale = "fr"
        config.project.name = "shop"
        config.stack.framework = "django"
        config.save()

        written = (self.root / "pyblade.toml").read_text()

        self.assertLess(written.index("[project]"), written.index("[stack]"))
        self.assertLess(written.index("[stack]"), written.index("[i18n]"))

    def test_each_table_is_written_with_a_word_about_what_it_is_for(self):
        config = self.config()
        config.project.name = "shop"
        config.save()

        self.assertIn("# What this project is called.", (self.root / "pyblade.toml").read_text())

    def test_what_is_written_reads_back_the_same(self):
        config = self.config()
        config.project.name = "shop"
        config.stack.framework = "django"
        config.live.throttle.enabled = False
        config.live.throttle.max_streams = 4
        config.i18n.languages = ["en", "fr"]
        config.save()

        again = self.config()

        self.assertEqual(again.project.name, "shop")
        self.assertEqual(again.stack.framework, "django")
        self.assertIs(again.live.throttle.enabled, False)
        self.assertEqual(again.live.throttle.max_streams, 4)
        self.assertEqual(again.i18n.languages, ["en", "fr"])

    def test_a_path_is_written_as_the_text_of_a_path(self):
        config = self.config()
        config.paths.core = Path("shop")
        config.save()

        self.assertIn('core = "shop"', (self.root / "pyblade.toml").read_text())

    def test_pyblade_will_not_rewrite_a_pyproject_it_does_not_own(self):
        self.write("pyproject.toml", '[project]\nname = "x"\n\n[tool.pyblade.i18n]\nlocale = "fr"\n')
        config = self.config("pyproject.toml")

        with self.assertRaises(RuntimeError) as caught:
            config.save()

        self.assertIn("pyblade.toml", str(caught.exception))


class TestWhatTheFrameworkSays(ConfigTestCase):
    """A Django project may configure PyBlade in its own settings.

    Which is the reason this had to be got right: PyBlade is imported long
    before Django is ready to be asked anything, so it is asked late, and asked
    again until it answers.
    """

    def test_django_settings_win_over_the_file(self):
        self.write("pyblade.toml", '[i18n]\nlocale = "fr"\n')

        with override_settings(PYBLADE={"i18n": {"locale": "sw"}}):
            self.assertEqual(self.config().i18n.locale, "sw")

    def test_it_may_be_written_in_capitals_as_django_settings_are(self):
        with override_settings(PYBLADE={"I18N": {"LOCALE": "sw"}}):
            self.assertEqual(self.config().i18n.locale, "sw")

    def test_it_says_nothing_about_the_keys_it_does_not_mention(self):
        self.write("pyblade.toml", '[project]\nname = "shop"\n')

        with override_settings(PYBLADE={"i18n": {"locale": "sw"}}):
            config = self.config()

            self.assertEqual(config.project.name, "shop")
            self.assertEqual(config.i18n.fallback_locale, "en")

    def test_a_config_read_before_the_settings_changed_follows_them(self):
        """The same object, not reloaded: what a long-lived process has."""
        config = self.config()
        self.assertEqual(config.i18n.locale, "en")

        with override_settings(PYBLADE={"i18n": {"locale": "sw"}}):
            self.assertEqual(config.i18n.locale, "sw")

        self.assertEqual(config.i18n.locale, "en")

    def test_what_it_says_is_never_written_back_into_the_file(self):
        """It is the project's settings talking, not the project's file."""
        config = self.config()
        config.project.name = "shop"

        with override_settings(PYBLADE={"i18n": {"locale": "sw"}}):
            config.save()

        self.assertNotIn('locale = "sw"', (self.root / "pyblade.toml").read_text())


class TestSayingSomethingElseForAWhile(ConfigTestCase):
    """What a test needs: a project laid out somewhere other than where it is."""

    def test_an_override_holds_for_the_block_and_no_longer(self):
        config = self.config()

        with config.override({"paths.templates": "/tmp/somewhere"}):
            self.assertEqual(config.paths.templates, Path("/tmp/somewhere"))

        self.assertEqual(config.paths.templates, Path("templates"))

    def test_it_wins_over_the_file_and_over_the_framework(self):
        self.write("pyblade.toml", '[i18n]\nlocale = "fr"\n')
        config = self.config()

        with override_settings(PYBLADE={"i18n": {"locale": "sw"}}):
            with config.override({"i18n.locale": "de"}):
                self.assertEqual(config.i18n.locale, "de")

    def test_it_is_never_written_into_the_file(self):
        config = self.config()
        config.project.name = "shop"

        with config.override({"i18n.locale": "de"}):
            config.save()

        self.assertNotIn('locale = "de"', (self.root / "pyblade.toml").read_text())

    def test_what_it_restores_is_what_was_said_before_it(self):
        config = self.config()

        with config.override({"i18n.locale": "de"}):
            with config.override({"i18n.locale": "sw"}):
                self.assertEqual(config.i18n.locale, "sw")
            self.assertEqual(config.i18n.locale, "de")


class TestWhereTheProjectIs(ConfigTestCase):
    def test_the_root_is_the_directory_the_file_is_in(self):
        self.write("pyblade.toml", '[project]\nname = "shop"\n')

        self.assertEqual(self.config().root, self.root)

    def test_a_run_may_say_the_root_is_somewhere_else(self):
        """What `pyblade init` needs, having just made the project beside it."""
        config = self.config()
        config.paths.root = Path("shop")

        self.assertEqual(config.root, Path("shop"))

    def test_and_that_is_never_written_into_the_file(self):
        """An absolute path would follow the file onto another machine."""
        config = self.config()
        config.project.name = "shop"
        config.paths.root = self.root

        config.save()

        self.assertNotIn("root =", (self.root / "pyblade.toml").read_text())

    def test_the_stubs_are_pyblades_own_and_not_a_projects_to_say(self):
        stubs = self.config().paths.stubs

        self.assertTrue((stubs / "templates").is_dir())


class TestBeingImportedBeforeTheFrameworkIsReady(unittest.TestCase):
    """The reason the framework is asked late.

    PyBlade is imported by `manage.py`, by the CLI and by this suite's own
    conftest, all of which run before `django.setup()`. Reading a Django setting
    then raises, so the configuration must not read one until it can -- and must
    pick them up once it can, without being reloaded.

    Django is already configured by the time this suite runs, so this is asked
    of a fresh interpreter, which is the only place the question exists.
    """

    SCRIPT = """
import json

# Imported first, with Django installed and not configured
from pyblade.config import Config

config = Config()
before = {"locale": config.i18n.locale, "debug": config.DEBUG}

import django
from django.conf import settings

settings.configure(
    DEBUG=True,
    INSTALLED_APPS=[],
    PYBLADE={"i18n": {"locale": "sw"}},
)
django.setup()

# The very same object, never reloaded
after = {"locale": config.i18n.locale, "debug": config.DEBUG}

print(json.dumps({"before": before, "after": after}))
"""

    def test_it_reads_nothing_of_djangos_until_django_can_answer(self):
        import subprocess
        import sys

        result = subprocess.run(
            [sys.executable, "-c", self.SCRIPT],
            capture_output=True,
            text=True,
            cwd=Path(__file__).resolve().parent.parent,
        )

        self.assertEqual(result.returncode, 0, result.stderr)

        read = json.loads(result.stdout)

        # Before: no error, and the defaults, because nothing was serving yet
        self.assertEqual(read["before"], {"locale": "en", "debug": False})

        # After: what the project's settings say, picked up without a reload
        self.assertEqual(read["after"], {"locale": "sw", "debug": True})
