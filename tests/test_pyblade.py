import unittest

from pyblade.engine import PyBlade
from pyblade.exceptions import UndefinedVariableError


class TestPyBlade(unittest.TestCase):
    def setUp(self):
        self.engine = PyBlade()

    def test_render_simple_variable(self):
        context = {"variable": "Hello, World!"}
        template = "{{ variable }}"
        result = self.engine.render(template, context)
        self.assertEqual(result, "Hello, World!")

    def test_render_multiple_variables(self):
        context = {"name": "Alice", "day": "Friday"}
        template = "Hello, {{ name }}! Today is {{ day }}."
        result = self.engine.render(template, context)
        self.assertEqual(result, "Hello, Alice! Today is Friday.")

        context2 = {"name": "Bob", "day": "Monday"}
        template2 = "Hello, {{name}}! Today is {{day}}."
        result2 = self.engine.render(template2, context2)
        self.assertEqual(result2, "Hello, Bob! Today is Monday.")

    def test_render_non_existent_variable(self):
        context = {}
        template = "Hello, {{ name }}!"
        with self.assertRaises(UndefinedVariableError) as cm:
            self.engine.render(template, context)
        self.assertEqual(str(cm.exception), "Undefined variable 'name'")

    def test_render_with_html_escape(self):
        context = {
            "name": "Alice",
            "message": "<script>alert('XSS');</script>"
        }
        template = "Hello, {{ name }}! Your message: {{ message }}."
        result = self.engine.render(template, context)
        expected = "Hello, Alice! Your message: &lt;script&gt;alert(&#x27;XSS&#x27;);&lt;/script&gt;."
        self.assertEqual(result, expected)


if __name__ == "__main__":
    unittest.main()
