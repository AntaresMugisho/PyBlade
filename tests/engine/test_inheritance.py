import shutil
import tempfile
import unittest
from pathlib import Path

from pyblade.config import settings
from pyblade.engine import loader
from pyblade.engine.exceptions import TemplateRenderError
from pyblade.engine.processor import TemplateProcessor


class TestTemplateInheritance(unittest.TestCase):
    """Covers @extends / @block / @endblock / @parent and the default slot."""

    def setUp(self):
        self.templates_dir = Path(tempfile.mkdtemp())
        self.components_dir = self.templates_dir / "components"
        self.components_dir.mkdir()

        self._saved_dirs = list(loader._default_loader._template_dirs)
        loader._default_loader.add_directories([self.templates_dir])

        self._saved_components_dir = settings._data.get("components_dir")
        settings._data["components_dir"] = str(self.components_dir)

        self.processor = TemplateProcessor()

    def tearDown(self):
        loader._default_loader._template_dirs = self._saved_dirs
        if self._saved_components_dir is None:
            settings._data.pop("components_dir", None)
        else:
            settings._data["components_dir"] = self._saved_components_dir
        shutil.rmtree(self.templates_dir, ignore_errors=True)

    def _write(self, name, content, directory=None):
        """Write a template file, `name` using dot notation (e.g. 'layouts.base')."""
        path = (directory or self.templates_dir) / f"{name.replace('.', '/')}.html"
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(content, encoding="utf-8")
        return path

    def _render(self, template, context=None):
        return self.processor.render(template, context or {})

    # Basic block replacement

    def test_child_block_replaces_parent_block(self):
        self._write("layouts.base", "<div>@block('content')Default content@endblock</div>")

        result = self._render("@extends('layouts.base')@block('content')Child content@endblock")

        self.assertEqual(result, "<div>Child content</div>")

    # Default parent blocks

    def test_parent_block_kept_when_child_does_not_override_it(self):
        self._write(
            "layouts.base",
            "<aside>@block('sidebar')Default navigation@endblock</aside>"
            "<main>@block('content')Default content@endblock</main>",
        )

        result = self._render("@extends('layouts.base')@block('content')Child content@endblock")

        self.assertEqual(result, "<aside>Default navigation</aside><main>Child content</main>")

    # @parent

    def test_parent_directive_keeps_original_block_content(self):
        self._write("layouts.base", "<aside>@block('sidebar')<nav>Default navigation</nav>@endblock</aside>")

        result = self._render("@extends('layouts.base')@block('sidebar')@parent<p>Appended</p>@endblock")

        self.assertEqual(result, "<aside><nav>Default navigation</nav><p>Appended</p></aside>")

    def test_parent_directive_can_be_surrounded_by_child_content(self):
        self._write("layouts.base", "<aside>@block('sidebar')DEFAULT@endblock</aside>")

        result = self._render("@extends('layouts.base')@block('sidebar')before-@parent-after@endblock")

        self.assertEqual(result, "<aside>before-DEFAULT-after</aside>")

    # Child content becoming the default slot

    def test_child_content_outside_blocks_becomes_the_slot(self):
        self._write("layouts.base", "<main>@block('content')Default@endblock{{ slot }}</main>")

        child = (
            "@extends('layouts.base')\n\n"
            "@block('content')Body@endblock\n\n"
            "<h1>Child page</h1>\n"
            "<div>Random content</div>\n"
        )

        result = self._render(child)

        self.assertEqual(result, "<main>Body<h1>Child page</h1>\n<div>Random content</div></main>")

    def test_slot_keeps_template_nodes_and_is_rendered_in_the_parent_context(self):
        self._write("layouts.base", "<main>{{ slot }}</main>")

        result = self._render("@extends('layouts.base')<p>{{ name }}</p>", {"name": "<Antares>"})

        # The slot markup itself is not escaped, but expressions inside it are.
        self.assertEqual(result, "<main><p>&lt;Antares&gt;</p></main>")

    def test_slot_is_empty_when_child_only_defines_blocks(self):
        self._write("layouts.base", "<main>{{ slot }}</main>")

        result = self._render("@extends('layouts.base')@block('content')Body@endblock")

        self.assertEqual(result, "<main></main>")

    # Nested inheritance

    def test_nested_inheritance(self):
        self._write(
            "layouts.base",
            "<html>@block('head')base-head@endblock<body>@block('content')base-content@endblock</body></html>",
        )
        self._write("layouts.app", "@extends('layouts.base')@block('head')@parent app-head@endblock")

        result = self._render("@extends('layouts.app')@block('content')page-content@endblock")

        self.assertEqual(result, "<html>base-head app-head<body>page-content</body></html>")

    def test_nested_inheritance_lets_the_deepest_child_win(self):
        self._write("layouts.base", "<body>@block('content')base@endblock</body>")
        self._write("layouts.app", "@extends('layouts.base')@block('content')app@endblock")

        result = self._render("@extends('layouts.app')@block('content')page@endblock")

        self.assertEqual(result, "<body>page</body>")

    def test_parent_directive_resolves_to_the_closest_ancestor_block(self):
        self._write("layouts.base", "<body>@block('content')base@endblock</body>")
        self._write("layouts.app", "@extends('layouts.base')@block('content')@parent+app@endblock")

        result = self._render("@extends('layouts.app')@block('content')@parent+page@endblock")

        self.assertEqual(result, "<body>base+app+page</body>")

    # Named slots

    def test_named_slots_are_available_as_variables_in_the_parent(self):
        self._write("layouts.base", "<title>{{ title }}</title><h2>{{ subtitle }}</h2>")

        child = (
            "@extends('layouts.base')"
            '<pb-slot name="title">My Awesome Title</pb-slot>'
            "@slot('subtitle')My Second Title@endslot"
        )

        self.assertEqual(self._render(child), "<title>My Awesome Title</title><h2>My Second Title</h2>")

    def test_named_slots_are_not_part_of_the_default_slot(self):
        self._write("layouts.base", "<main>{{ slot }}</main>")

        child = "@extends('layouts.base')@slot('title')Hidden@endslot<p>Visible</p>"

        self.assertEqual(self._render(child), "<main><p>Visible</p></main>")

    def test_undefined_named_slot_falls_back_to_the_parent_default(self):
        self._write("layouts.base", '<title>{{ title or "Default title" }}</title>')

        result = self._render("@extends('layouts.base')<p>Body</p>", {"title": None})

        self.assertEqual(result, "<title>Default title</title>")

    # Compatibility with other features

    def test_blocks_support_expressions_directives_and_includes(self):
        self._write("partials.footer", "<footer>{{ year }}</footer>")
        self._write("layouts.base", "<body>@block('content')nothing@endblock</body>")

        child = (
            "@extends('layouts.base')"
            "@block('content')"
            "@if(logged_in)Hello {{ user }}@else Guest @endif"
            "@include('partials.footer')"
            "@endblock"
        )

        result = self._render(child, {"logged_in": True, "user": "Antares", "year": 2026})

        self.assertEqual(result, "<body>Hello Antares<footer>2026</footer></body>")

    def test_components_work_inside_blocks_and_slot(self):
        self._write("alert", '<div class="alert">{{ slot }}</div>', directory=self.components_dir)
        self._write("layouts.base", "<body>@block('content')nothing@endblock<main>{{ slot }}</main></body>")

        child = (
            "@extends('layouts.base')"
            "@block('content')<pb-alert>Boom</pb-alert>@endblock"
            "<pb-alert>Outside</pb-alert>"
        )

        result = self._render(child)

        self.assertEqual(
            result,
            '<body><div class="alert">Boom</div><main><div class="alert">Outside</div></main></body>',
        )

    def test_layout_features_still_work_when_extended(self):
        self._write(
            "layouts.base",
            "<ul>@for(item in items)<li>{{ item }}</li>@endfor</ul>@block('content')nothing@endblock",
        )

        result = self._render("@extends('layouts.base')@block('content')done@endblock", {"items": ["a", "b"]})

        self.assertEqual(result, "<ul><li>a</li><li>b</li></ul>done")

    def test_template_without_extends_renders_its_own_blocks(self):
        result = self._render("<div>@block('content')Default@endblock</div>")

        self.assertEqual(result, "<div>Default</div>")

    def test_parent_directive_renders_nothing_outside_of_inheritance(self):
        result = self._render("<div>@block('content')@parent Default@endblock</div>")

        self.assertEqual(result, "<div> Default</div>")

    def test_included_template_can_extend_a_layout(self):
        self._write("layouts.base", "<section>@block('content')nothing@endblock</section>")
        self._write("partials.card", "@extends('layouts.base')@block('content'){{ label }}@endblock")

        result = self._render("<div>@include('partials.card')</div>", {"label": "Card"})

        self.assertEqual(result, "<div><section>Card</section></div>")

    def test_blocks_named_by_a_variable_are_matched_on_their_expression(self):
        self._write("layouts.base", "<body>@block(block_name)base@endblock</body>")

        result = self._render("@extends('layouts.base')@block(block_name)page@endblock", {"block_name": "content"})

        self.assertEqual(result, "<body>page</body>")

    def test_rendered_result_is_cached_under_the_original_context(self):
        self._write("layouts.base", "<section>@block('content')nothing@endblock</section>")
        template = "@extends('layouts.base')@block('content'){{ label }}@endblock"
        context = {"label": "Card"}

        result = self._render(template, context)

        self.assertEqual(self.processor.cache.get(template, context), result)

    def test_circular_inheritance_is_reported(self):
        self._write("layouts.base", "@extends('layouts.app')")
        self._write("layouts.app", "@extends('layouts.base')")

        with self.assertRaises(TemplateRenderError) as raised:
            self._render("@extends('layouts.base')")

        self.assertIn("Circular template inheritance", raised.exception.message)


if __name__ == "__main__":
    unittest.main()
