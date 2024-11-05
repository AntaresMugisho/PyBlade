# import os

# from django.middleware.csrf import get_token
# from django.template import TemplateDoesNotExist, TemplateSyntaxError
from django.template.backends.base import BaseEngine

# from django.template.backends.django import DjangoTemplates
from django.template.backends.utils import csrf_input_lazy, csrf_token_lazy
from django.utils.functional import cached_property
from django.utils.module_loading import import_string

from pyblade import PyBlade


class DjangoPyBlade(BaseEngine):

    app_dirname = "templates"

    def __init__(self, params):
        params = params.copy()
        options = params.pop("OPTIONS").copy()
        super().__init__(params)

        self.context_processors = options.pop("context_processors", [])

        dirs = params.get("DIRS")
        app_dirs = params.get("APP_DIRS")  # NOQA

        self.engine = PyBlade(dirs)

    def from_string(self, template_code):
        return Template(self.engine.from_string(template_code), self)

    def get_template(self, template_name):
        """Find the template in template directories."""

        parsed_template = self.engine.render(template_name, {})
        return parsed_template

    @cached_property
    def template_context_processors(self):
        return [import_string(path) for path in self.context_processors]


class Template:
    def __init__(self, template, backend):
        self.template = template
        self.backend = backend
        self.origin = Origin(name=template.filename, template_name=template.name)

    def render(self, context=None, request=None):
        if context is None:
            context = {}
        if request is not None:
            context["request"] = request
            context["csrf_input"] = csrf_input_lazy(request)
            context["csrf_token"] = csrf_token_lazy(request)
            for context_processor in self.backend.template_context_processors:
                context.update(context_processor(request))
        return self.template.render(context)


class Origin:

    def __init__(self, name, template_name):
        self.name = name
        self.template_name = template_name
