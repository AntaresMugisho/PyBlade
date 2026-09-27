"""Templates and components in the apps of a Django project.

A Django project keeps templates in its apps as well as in the project, and the
components of a project may live there too. `--app` says which app a file is
made for, and the engine finds what an app brings after what the project has.
"""

import importlib
import os
import shutil
import sys
import tempfile
import unittest
from pathlib import Path
from types import SimpleNamespace
from unittest import mock

from pyblade.config import config
from pyblade.engine.nodes import ComponentNode

make_template = importlib.import_module("pyblade.cli.commands.make:template")
make_component = importlib.import_module("pyblade.cli.commands.make:component")
make_live = importlib.import_module("pyblade.cli.commands.make:live")


class AProjectWithAnApp(unittest.TestCase):
    """A project directory with one app in it, `blog`, and Django told about it."""

    def setUp(self):
        self.root = Path(tempfile.mkdtemp()).resolve()
        self.addCleanup(shutil.rmtree, self.root, ignore_errors=True)

        self.app_dir = self.root / "apps" / "blog"
        self.app_dir.mkdir(parents=True)
        (self.root / "apps" / "__init__.py").write_text("")
        (self.app_dir / "__init__.py").write_text("")

        cwd = os.getcwd()
        os.chdir(self.root)
        self.addCleanup(os.chdir, cwd)

        self.app = SimpleNamespace(name="apps.blog", label="blog", path=str(self.app_dir))

        for patch in (
            mock.patch("pyblade.cli.locations.setup_django"),
            mock.patch("django.apps.apps.get_app_config", side_effect=self._get_app_config),
            mock.patch("django.apps.apps.get_app_configs", return_value=[self.app]),
            mock.patch("pyblade.engine.roots.django_apps", return_value=[self.app]),
            config.override({"stack.framework": "django", "paths.root": self.root}),
        ):
            patch.__enter__()
            self.addCleanup(patch.__exit__, None, None, None)

        # The app is importable, as an installed one is
        sys.path.insert(0, str(self.root))
        self.addCleanup(sys.path.remove, str(self.root))
        self.modules = set(sys.modules)
        self.addCleanup(self.forget_modules)

    def forget_modules(self):
        for name in set(sys.modules) - self.modules:
            del sys.modules[name]

    def _get_app_config(self, label):
        if label != "blog":
            raise LookupError(label)

        return self.app

    def written(self):
        return sorted(str(path.relative_to(self.root)) for path in self.root.rglob("*") if path.is_file())


class TestWritingFromTheRootOfTheProject(AProjectWithAnApp):
    def test_files_go_where_the_project_says_wherever_the_command_is_run_from(self):
        (self.root / "sub").mkdir()
        os.chdir(self.root / "sub")

        make_template.Command().handle(name="home")
        make_component.Command().handle(name="alert")
        make_live.Command().handle(name="counter")

        self.assertEqual(
            self.written(),
            [
                "apps/__init__.py",
                "apps/blog/__init__.py",
                "components/alert.html",
                "components/counter/counter.html",
                "components/counter/counter.py",
                "templates/home.html",
            ],
        )


class TestWritingInAnApp(AProjectWithAnApp):
    def test_a_template_goes_in_the_templates_of_the_app(self):
        make_template.Command().handle(name="blog.post", app="blog")

        self.assertIn("apps/blog/templates/blog/post.html", self.written())
        self.assertNotIn("templates/blog/post.html", self.written())

    def test_a_component_goes_in_the_components_of_the_app(self):
        make_component.Command().handle(name="ui.alert", app="blog")

        self.assertIn("apps/blog/components/ui/alert.html", self.written())

    def test_a_live_component_goes_in_the_components_of_the_app(self):
        make_live.Command().handle(name="counter", app="blog")

        self.assertIn("apps/blog/components/counter/counter.py", self.written())
        self.assertIn("apps/blog/components/counter/counter.html", self.written())

    def test_the_app_reaches_a_live_component_made_through_make_component(self):
        make_component.Command().handle(name="counter", app="blog", live=True)

        self.assertIn("apps/blog/components/counter/counter.py", self.written())

    def test_an_app_that_does_not_exist_is_refused_saying_which_there_are(self):
        with mock.patch.object(make_template.Command, "error") as error:
            make_template.Command().handle(name="home", app="shop")

        self.assertIn("blog", error.call_args.args[0])
        self.assertEqual([path for path in self.written() if path.endswith(".html")], [])

    def test_an_app_means_nothing_without_django(self):
        with config.override({"stack.framework": "flask"}), mock.patch.object(make_template.Command, "error") as error:
            make_template.Command().handle(name="home", app="blog")

        self.assertIn("Django", error.call_args.args[0])


class TestFindingWhatAnAppBrings(AProjectWithAnApp):
    def component(self, directory, name, content):
        path = directory / "components" / name
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(content, encoding="utf-8")

        return path

    def test_a_component_only_an_app_has_is_found(self):
        html = self.component(self.app_dir, "badge.html", "<span>app</span>")

        found = ComponentNode("'unused'")._resolve_component("badge")

        self.assertEqual(found["type"], "static")
        self.assertEqual(found["html"], html)

    def test_the_project_has_the_first_word(self):
        self.component(self.root, "badge.html", "<span>project</span>")
        self.component(self.app_dir, "badge.html", "<span>app</span>")

        found = ComponentNode("'unused'")._resolve_component("badge")

        self.assertEqual(found["html"].resolve(), self.root / "components" / "badge.html")

    def test_what_is_rendered_is_the_file_that_was_found(self):
        self.component(self.root, "badge.html", "<span>project</span>")
        html = self.component(self.app_dir, "tag.html", "<span>app</span>")

        node = ComponentNode("'unused'")
        rendered = node._render_static_component("tag", {}, {}, html)

        self.assertIn("app", rendered)

    def test_a_live_component_of_an_app_is_reached_through_the_name_of_the_app(self):
        self.component(
            self.app_dir,
            "counter/counter.py",
            "from pyblade import LiveComponent\n\n\nclass Counter(LiveComponent):\n    count = 3\n",
        )
        self.component(self.app_dir, "counter/counter.html", "<div>{{ count }}</div>")

        found = ComponentNode("'unused'")._resolve_component("counter")

        self.assertEqual(found["type"], "live")
        self.assertEqual(found["module"], "apps.blog.components.counter.counter")

        cls = importlib.import_module(found["module"]).Counter
        component = cls("pb-test")

        self.assertEqual(component.get_template_name(), "counter.counter")
        self.assertIn("3", component.render_template())

    def test_two_components_of_one_name_each_render_their_own_template(self):
        for directory, word in ((self.root, "project"), (self.app_dir, "app")):
            self.component(
                directory,
                "card/card.py",
                "from pyblade import LiveComponent\n\n\nclass Card(LiveComponent):\n    pass\n",
            )
            self.component(directory, "card/card.html", f"<div>{word}</div>")

        # Reached the two ways a class is: from where the project runs, and by the name of the app
        project_card = importlib.import_module("components.card.card").Card("pb-a")
        app_card = importlib.import_module("apps.blog.components.card.card").Card("pb-b")

        self.assertIn("project", project_card.render_template())
        self.assertIn("app", app_card.render_template())
        self.assertNotIn("project", app_card.render_template())
