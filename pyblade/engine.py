# Core template rendering logic.

import re
import html

from pyblade.exceptions import UndefinedVariableError


class PyBlade:

    def render(self, template: str, context: dict | None = None) -> str:
        """
        :param template: A string containing the template with placeholders in the form of {{ variable }}
        :param context: A dictionary where keys correspond to the placeholder names in the template and values are the
            data to replace those placeholders.
        :return: The template string where placeholders have been replaced with the corresponding values
            from the context.
        """

        # Function to replace placeholders
        def replace_placeholder(match) -> str:
            variable_name = match.group(1).strip()
            if variable_name not in context:
                raise UndefinedVariableError(variable_name)
            return self.escape(str(context[variable_name]))

        # Regular expression to match placeholders like {{ variable }} or {{variable}}
        pattern = r'\{\{\s*(\w+)\s*\}\}'
        unescaped_pattern = r'\{\{\!\!\s*(\w+)\s*\!\!\}\}'

        template = self.load_template(template)

        result = re.sub(pattern, replace_placeholder, template)
        return result

    def escape(self, text: str) -> str:
        """
        Escape HTML characters to prevent XSS attacks.
        """
        return html.escape(text)

    def load_template(self, template_name):
        """
        Load the template text content
        :param template_name: The template file name to load
        :return: The template file text content
        """

        with open(f"{template_name}", "r") as file:
            text = file.read()

        return text

