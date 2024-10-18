import re
import html


from .exceptions import UndefinedVariableError


class Pattern:
    escaped_variable_pattern = re.compile(r"\{\{\s*(.*)\s*\}\}$")
    unescaped_variable_pattern = re.compile(r"\{!!\s*(.*)\s*!!\}$")

    if_pattern = re.compile(r"@if\s*\(.*\)$")
    elif_pattern = re.compile(r"@elif\s*\(.*\)$")
    endif_pattern = re.compile(r"@endif$")

    for_pattern = re.compile(r"@for\s*\(.*\)$")
    empty_pattern = re.compile(r"@empty$")
    endfor_pattern = re.compile(r"@endfor$")


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
            # print("match")
            variable_name = match.group(1).strip()
            if variable_name not in context:
                raise UndefinedVariableError(variable_name)
            return self.escape(str(context[variable_name]))

        template = self.load_template(template)

        pattern = Pattern.escaped_variable_pattern

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

    def evaluate_expression(expression, context):
        # try:
        #     # Safely evaluate the expression in the context provided
        #     return eval(expression, {}, context)
        # except Exception as e:
        #     raise RenderException(f"Error evaluating expression: {expression}")


        #####

        output = []
        lines = template.splitlines()
        skip_block = False  # To control whether the current block should be skipped

        for i, line in enumerate(lines):
            if if_pattern.search(line):
                condition = if_pattern.search(line).group(1).strip()
                if evaluate_expression(condition, context):
                    skip_block = False
                else:
                    skip_block = True
            elif elif_pattern.search(line):
                condition = elif_pattern.search(line).group(1).strip()
                if not skip_block and evaluate_expression(condition, context):
                    skip_block = False
                else:
                    skip_block = True
            elif else_pattern.search(line):
                skip_block = not skip_block
            elif endif_pattern.search(line):
                skip_block = False
            else:
                # Perform variable replacement
                if not skip_block:
                    for key, value in context.items():
                        # Match both {{variable}} and {{ variable }} formats
                        placeholder = re.compile(rf"\{{\{{\s*{key}\s*\}}\}}")
                        line = placeholder.sub(str(value), line)
                    output.append(line)

        return "\n".join(output)
