import unittest
from unittest.mock import MagicMock, patch
import sys

# Mock questionary if needed (though we are testing engine)
sys.modules["questionary"] = MagicMock()

from pyblade.engine.processor import TemplateProcessor

class TestTranslationWith(unittest.TestCase):
    def setUp(self):
        self.processor = TemplateProcessor()

    def _render(self, template, context=None):
        return self.processor.render(template, context or {})

    @patch('pyblade.engine.processor.gettext')
    def test_trans(self, mock_gettext):
        mock_gettext.gettext.side_effect = lambda x: f"Translated<{x}>"
        mock_gettext.pgettext.side_effect = lambda c, x: f"CtxTranslated<{c}:{x}>"
        
        # Simple
        template = "@trans('Hello')"
        self.assertEqual(self._render(template), "Translated<Hello>")
        
        # Context
        template = "@trans('Hello', context='greeting')"
        self.assertEqual(self._render(template), "CtxTranslated<greeting:Hello>")
        
        # Noop
        template = "@trans('Hello', noop=True)"
        self.assertEqual(self._render(template), "Hello")

    @patch('pyblade.engine.processor.gettext')
    def test_blocktranslate(self, mock_gettext):
        mock_gettext.gettext.side_effect = lambda x: f"Block<{x}>"
        mock_gettext.ngettext.side_effect = lambda s, p, n: f"Plural<{s}|{p}|{n}>"
        
        # Simple
        template = "@blocktranslate\nHello\n@endblocktranslate"
        output = self._render(template).strip()
        self.assertEqual(output, "Block<\nHello\n>")
        
        # Trimmed
        template = "@blocktranslate(trimmed=True)\n  Hello  \n@endblocktranslate"
        output = self._render(template)
        self.assertEqual(output, "Block<Hello>")
        
        # Plural
        template = """
        @blocktranslate(count=cnt, trimmed=True)
        One apple
        @plural
        %(count)s apples
        @endblocktranslate
        """
        context = {'cnt': 1}
        # ngettext will be called with "One apple", "%(count)s apples", 1
        # Our mock returns "Plural<One apple|%(count)s apples|1>"
        # Then substitution happens: %(count)s -> 1
        output = self._render(template, context).strip()
        self.assertEqual(output, "Plural<One apple|1 apples|1>")
        
        context = {'cnt': 5}
        output = self._render(template, context).strip()
        self.assertEqual(output, "Plural<One apple|5 apples|5>")

    def test_with_python_args(self):
        template = """
        @with(a=1, b=3)
        {{ a }} + {{ b }} = {{ a + b }}
        @endwith
        """
        output = self._render(template).strip()
        self.assertEqual(output, "1 + 3 = 4")

    def test_with_complex_args(self):
        template = """
        @with(user={'name': 'John'}, active=True)
        User: {{ user.name }}, Active: {{ active }}
        @endwith
        """
        output = self._render(template).strip()
        self.assertEqual(output, "User: John, Active: True")

if __name__ == "__main__":
    unittest.main()
