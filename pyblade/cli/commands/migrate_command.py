import os
import re
import shutil
from pathlib import Path

from ..commands.base_command import BaseCommand

_SETTINGS_PATERN = re.compile(
    r"\"\"\"(?P<banner>.*?)\"\"\"\s*.*?\s*INSTALLED_APPS\s=\s\[\s*(?P<installed_apps>.*?)\s*\]\s*.*?\s*MIDDLEWARE\s=\s\[\s*(?P<middleware>.*?)\s*\]\s*.*?\s*TEMPLATES\s=\s*\[\s*(?P<templates>\{.*?\},)\n\]",  # noqa E501
    re.DOTALL,
)


class MigrateCommand(BaseCommand):
    name = "migrate"
    description = "Migrate from Django Templates to PyBlade Templates engine"

    def handle(self):

        project_directory = self.ask(
            "Enter the path to the project directory (leave empty to use the current directory):"
        )

        project_root = Path(project_directory) or Path.cwd()

        if not project_root.exists():
            self.error("The specified project directory does not exist.")
            return

        output_directory = self.ask("Enter the path to the output directory:")

        if not output_directory:
            self.error("You must specify an output directory.")
            return

        output_directory = Path(output_directory)

        if output_directory.exists():
            confirm_overwrite = self.confirm("The output directory already exists. Do you want to overwrite it?")
            if not confirm_overwrite:
                self.info("Operation canceled.")
                return
            shutil.rmtree(output_directory)

        shutil.copytree(project_root, output_directory)
        self.info(f"Project copied to: {output_directory}")

        html_templates = []
        for root, _, files in os.walk(output_directory):
            html_templates.extend(os.path.join(root, file) for file in files if file.endswith(".html"))

        if not html_templates:
            self.warning("No .html files found in the project.")
            return

        self.line(f"{len(html_templates)} .html files found for conversion.")

        for template_path in self.track(
            html_templates, description="Converting django  template tags to pyblade dirctives..."
        ):
            with open(template_path, "r", encoding="utf-8") as file:
                file_content = file.read()

            pyblade_content = self._convert_django_to_pyblade(file_content)

            with open(template_path, "w", encoding="utf-8") as file:
                file.write(pyblade_content)

        # TODO: Update settings.py

        self.success("🎉 Migration completed successfully!")

    def _convert_django_to_pyblade(self, content):
        """
        Converts Django templates tags to PyBlade directives.
        This function replaces Django-specific syntax with PyBlade syntax.

        Parameters:
            content (str): The content of the Django template to be converted.

        Returns:
            str: The converted PyBlade content.
        """

        # Extract all comments from the content for later restoration
        extracted_comments = re.findall(r"{#.*?#}", content, flags=re.DOTALL)
        content_without_comments = re.sub(r"{#.*?#}", "{#COMMENT#}", content, flags=re.DOTALL)

        # Convert Django's {% extends %} syntax to PyBlade's @extends syntax
        content_without_comments = re.sub(
            r'{%\s*extends\s+"(.*?)\.html"\s*%}', r'@extends("\1")', content_without_comments
        )

        # Convert Django's {% block %} syntax to PyBlade's @yield and @block syntax
        if "@extends" not in content_without_comments:
            content_without_comments = re.sub(r"{%\s*block\s+(.*?)\s*%}", r'@yield("\1")', content_without_comments)
            content_without_comments = re.sub(r"{%\s*endblock\s+(.*?)\s*%}", "", content_without_comments)
        else:
            content_without_comments = re.sub(
                r"{%\s*block\s+(.*?)\s*%}(.*?){%\s*endblock\s*%}",
                lambda match: f"@block('{match.group(1)}')\n{match.group(2)}@endblock",
                content_without_comments,
                flags=re.DOTALL,
            )

        # Further conversion of Django template blocks to PyBlade syntax
        content_without_comments = re.sub(
            r"{%\s*block\s+(.*?)\s*%}(.*?){%\s*endblock\s*%}",
            lambda match: f"@block {match.group(1)}\n{match.group(2)}@endblock",
            content_without_comments,
            flags=re.DOTALL,
        )

        # Convert Django's {% include %} and {% if %} syntax to PyBlade's @include and @if syntax
        content_without_comments = re.sub(r'{%\s*include\s+"(.*?)"\s*%}', r'@include("\1")', content_without_comments)
        content_without_comments = re.sub(r"{%\s*if\s+(.*?)\s*%}", r"@if(\1)", content_without_comments)
        content_without_comments = re.sub(r"{%\s*elif\s+(.*?)\s*%}", r"@elseif(\1)", content_without_comments)
        content_without_comments = re.sub(r"{%\s*else\s*%}", r"@else", content_without_comments)
        content_without_comments = re.sub(r"{%\s*endif\s*%}", r"@endif", content_without_comments)
        content_without_comments = re.sub(
            r"{%\s*for\s+(.*?)\s+in\s+(.*?)\s*%}", r"@for(\1 : \2)", content_without_comments
        )
        content_without_comments = re.sub(r"{%\s*endfor\s*%}", r"@endfor", content_without_comments)

        # Ensure proper spacing around variables in the {{ }} syntax
        content_without_comments = re.sub(r"{{\s*(.*?)\s*}}", r"{{ \1 }}", content_without_comments)

        # Convert Django's {% trans %} syntax to PyBlade's @trans syntax
        content_without_comments = re.sub(r'{%\s*trans\s+"(.*?)"\s*%}', r'@trans("\1")', content_without_comments)
        content_without_comments = re.sub(r"{%\s*trans\s+(.*?)\s*%}", r"@trans(\1)", content_without_comments)
        content_without_comments = re.sub(
            r'{%\s*translate\s+"(.*?)"\s*%}', r'@translate("\1")', content_without_comments
        )
        content_without_comments = re.sub(r"{%\s*translate\s+(.*?)\s*%}", r"@translate(\1)", content_without_comments)
        content_without_comments = re.sub(
            r"{%\s*localize\s+(on|off)\s*%}", r'@localize("\1")', content_without_comments
        )
        content_without_comments = re.sub(r"{%\s*endlocalize\s+(.*?)\s*%}", r"@endlocalize", content_without_comments)
        content_without_comments = re.sub(r"{%\s*csrf_token\s+(.*?)\s*%}", r"@csrf_token", content_without_comments)
        content_without_comments = re.sub(r"{%\s*ifchanged\s*%}", r"@ifchanged", content_without_comments)
        content_without_comments = re.sub(r"{%\s*endifchanged\s*%}", r"@endifchanged", content_without_comments)
        content_without_comments = re.sub(r"{%\s*with\s+(.*?)\s*%}", r"@with(\1)", content_without_comments)
        content_without_comments = re.sub(r"{%\s*endwith\s*%}", r"@endwith", content_without_comments)
        content_without_comments = re.sub(r"{%\s*autoescape\s+(.*?)\s*%}", r"@autoescape(\1)", content_without_comments)
        content_without_comments = re.sub(r"{%\s*endautoescape\s*%}", r"@endautoescape", content_without_comments)
        content_without_comments = re.sub(r"{%\s*verbatim\s*%}", r"@verbatim", content_without_comments)
        content_without_comments = re.sub(r"{%\s*endverbatim\s*%}", r"@endverbatim", content_without_comments)
        content_without_comments = re.sub(r"{%\s*spaceless\s*%}", r"@spaceless", content_without_comments)
        content_without_comments = re.sub(r"{%\s*endspaceless\s*%}", r"@endspaceless", content_without_comments)
        content_without_comments = re.sub(r"{%\s*comment\s*%}", r"@comment", content_without_comments)
        content_without_comments = re.sub(r"{%\s*endcomment\s*%}", r"@endcomment", content_without_comments)
        content_without_comments = re.sub(r"{%\s*cache\s+(.*?)\s*%}", r"@cache(\1)", content_without_comments)
        content_without_comments = re.sub(r"{%\s*endcache\s*%}", r"@endcache", content_without_comments)
        content_without_comments = re.sub(r"{%\s*empty\s+(.*?)\s*%}", r"@empty(\1)", content_without_comments)
        content_without_comments = re.sub(r"{%\s*now\s+(.*?)\s*%}", r"@now(\1)", content_without_comments)
        content_without_comments = re.sub(r"{%\s*static\s+(.*?)\s*%}", r"@static(\1)", content_without_comments)

        content_without_comments = re.sub(r'{%\s*load\s+"(.*?)"\s*%}', "", content_without_comments)

        # Handle URL tag conversion
        content_without_comments = re.sub(
            r"{%\s*url\s+\'(.*?)\'\s*(.*?)\s*%}",
            lambda match: f"@url('{match.group(1)}', [{', '.join(match.group(2).split())}])",
            content_without_comments,
        )

        for comment in extracted_comments:
            content_without_comments = content_without_comments.replace("{#COMMENT#}", comment, 1)

        return content_without_comments
