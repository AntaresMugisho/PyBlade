import os

from django.middleware.csrf import get_token
from django.template import TemplateDoesNotExist
from django.template.backends.base import BaseEngine

from pyblade import PyBlade


class PyBladeTemplates(BaseEngine):
    def __init__(self, params):
        super().__init__(params)

        self.template_dirs = params.get("DIRS", [])
        self.options = params.get("OPTIONS", {})
        self.engine = PyBlade()

    def get_template(self, template_name):
        """Find the template in template directories."""

        # Optionally remove .html extension if added
        template_name = template_name.rstrip(".html")

        for directory in self.template_dirs:
            folders = [a for a in template_name.split(".")]
            for folder in folders:
                template_path = f"{directory.joinpath(folder)}.html"

                if os.path.exists(template_path):
                    with open(template_path, "r") as file:
                        return file.read()

        raise TemplateDoesNotExist(template_name)

    def render(self, template_name, context=None, request=None):
        """Override the render method to use PyBlade."""

        context = context or {}
        if request:
            context["csrf_token"] = get_token(request)

        # Load the template
        # template_content = self.get_template(template_name)

        # Render with PyBlade
        return self.engine.render(template_name, context)
