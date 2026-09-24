"""@script: a component's own JavaScript, run by the client with $pb at hand.

The server renders it inert, in a <template>, and gives it a key that says
which @script it is. The key comes from where the block is written, not from
what it renders to, so that a value changing inside it does not make a script
that has already run look like a new one.
"""

import re
import unittest

from pyblade.engine.exceptions import TemplateRenderError
from pyblade.engine.processor import TemplateProcessor
from pyblade.live.base import LiveComponent


def render(template, context=None):
    return TemplateProcessor().render(template, context or {})


def keys(html):
    return re.findall(r'<template pb:script="([0-9a-f]+)">', html)


class TestScript(unittest.TestCase):
    def test_the_script_is_rendered_inert(self):
        html = render("@script<script>$pb.save()</script>@endscript")

        self.assertRegex(
            html,
            r'^<template pb:script="[0-9a-f]+"><script>\$pb\.save\(\)</script></template>$',
        )

    def test_it_renders_with_the_context_it_is_written_in(self):
        self.assertIn(
            "console.log(3)",
            render("@script<script>console.log({{ n }})</script>@endscript", {"n": 3}),
        )

    def test_the_key_does_not_change_with_what_it_renders(self):
        template = "@script<script>console.log({{ n }})</script>@endscript"

        self.assertEqual(keys(render(template, {"n": 1})), keys(render(template, {"n": 2})))

    def test_two_scripts_have_two_keys(self):
        html = render("@script<script>a()</script>@endscript@script<script>a()</script>@endscript")

        self.assertEqual(len(set(keys(html))), 2)

    def test_an_unclosed_script_is_an_error(self):
        with self.assertRaises(TemplateRenderError):
            render("@script<script>a()</script>")


def component(template):
    return type(
        "Scripted",
        (LiveComponent,),
        {
            "count": 0,
            "render": lambda self: self.render_inline(template, context={}),
        },
    )


class TestScriptInALiveComponent(unittest.TestCase):
    def test_a_script_written_after_the_root_is_moved_inside_it(self):
        html = component(
            "<div><b>{{ count }}</b></div>\n\n@script\n<script>$pb.count</script>\n@endscript\n"
        ).render_initial()

        root_end = html.rindex("</div>")
        self.assertLess(html.index("<template pb:script="), root_end)
        self.assertTrue(html.rstrip().endswith("</div>"))

    def test_a_script_written_inside_the_root_stays_where_it_is(self):
        html = component("<div><b>{{ count }}</b>@script<script>x()</script>@endscript</div>").render_initial()

        self.assertRegex(
            html,
            r"<b>0</b><template pb:script=\"[0-9a-f]+\"><script>x\(\)</script></template></div>$",
        )

    def test_the_update_carries_the_script_too(self):
        cls = component("<div>{{ count }}</div>@script<script>x()</script>@endscript")
        snapshot = cls.deserialize({"_id": "c1"}).serialize()

        html = cls.update_component(snapshot["state"] | {"_id": "c1"}, "$refresh", [])["html"]

        self.assertRegex(html, r"^<div[^>]*><template pb:script=")


if __name__ == "__main__":
    unittest.main()
