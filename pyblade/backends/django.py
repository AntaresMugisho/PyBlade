from django.template import TemplateDoesNotExist
from django.template.backends.base import BaseEngine
from django.template.backends.utils import csrf_input_lazy, csrf_token_lazy
from django.utils.functional import cached_property
from django.utils.module_loading import import_string

from pyblade.config import config
from pyblade.engine.exceptions import TemplateNotFoundError
from pyblade.engine.renderer import PyBlade
from pyblade.engine.template import Template as PyBladeTemplate


class TemplateNotFoundHere(TemplateNotFoundError, TemplateDoesNotExist):
    """A template this engine has not got.

    Both what PyBlade calls it and what Django calls it, so that whichever of
    the two is being caught, it is caught.
    """


class PyBladeEngine(BaseEngine):
    app_dirname = str(config.paths.templates)

    def __init__(self, params):
        params = params.copy()
        options = params.pop("OPTIONS").copy()
        super().__init__(params)

        self.context_processors = options.pop("context_processors", [])
        self.engine = PyBlade(dirs=self.template_dirs)

    def from_string(self, template_code):
        return Template(self.engine.from_string(template_code), self)

    def get_template(self, template_name):
        """Find the template in template directories."""

        try:
            return Template(self.engine.get_template(template_name), self)
        except TemplateNotFoundError as error:
            # Django asks each of its engines in turn, and an engine without
            # the template says so by raising TemplateDoesNotExist. Raised as
            # both, so that a template held by another engine is still reached
            # and Django still shows where it looked, while code catching
            # PyBlade's own exception goes on working.
            raise TemplateNotFoundHere(str(error)) from error

    @cached_property
    def template_context_processors(self):
        return [import_string(path) for path in self.context_processors]


class Template:
    def __init__(self, pyblade_template: PyBladeTemplate, backend: PyBladeEngine):
        self.pyblade_template = pyblade_template
        self.pyblade_template.set_backend(backend)
        self.pyblade_template.set_engine(backend.engine)
        self.backend = backend

    def render(self, context=None, request=None):
        if context is None:
            context = {}

        if request is not None:
            context["request"] = request
            context["csrf_input"] = csrf_input_lazy(request)
            context["csrf_token"] = csrf_token_lazy(request)
            for context_processor in self.backend.template_context_processors:
                context.update(context_processor(request))

        return self.pyblade_template.render(context)
