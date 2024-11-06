from django.template.backends.utils import csrf_input_lazy, csrf_token_lazy


class Template:
    def __init__(self, template_name, template_path, template_string=None, backend=None, engine=None):
        self.name = template_name
        self.backend = backend
        self.path = template_path
        self.template_string = template_string
        self.engine = engine

    def __str__(self):
        return self.template_string

    def render(self, context=None, request=None):
        if context is None:
            context = {}
        if request is not None:
            context["request"] = request
            context["csrf_input"] = csrf_input_lazy(request)
            context["csrf_token"] = csrf_token_lazy(request)
            for context_processor in self.backend.template_context_processors:
                context.update(context_processor(request))

        return self.engine.render(self.template_string, context)
