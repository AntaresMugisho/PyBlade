import re


class PyBladeDirectives:
    def __init__(self):
        self.directives = {}

    def register(self, name: str, func):
        """
        Register a custom directive.

        :param name: The directive name
        :param func: The function that will process the directive
        :void:
        """
        self.directives[name] = func

    def parse_directives(self, template: str, context: dict):
        """
        Process all directives within a template.
        
        :param template: 
        :param context: 
        :return: 
        """
        
        template = self._parse_if(template, context)
        template = self._parse_for(template, context)
        return template

    def _parse_if(self, template, context):
        """
        Handle, @if, @elif, @else and @endif directives.
        
        :param template: 
        :param context: 
        :return: 
        """
        pattern = re.compile(r"@if\s*\((.*?)\)\s*(.*?)@endif", re.DOTALL)
        return pattern.sub(lambda match: eval(match.group(1), {}, context) and match.group(2) or '', template)

    def _parse_for(self, template, context):
        """
        Handle @for, @empty and @endfor directives.
        
        :param template: 
        :param context: 
        :return: 
        """
        pattern = re.compile(r"@for\s*\((.*?)\s+in\s+(.*?)\)\s*(.*?)@endfor", re.DOTALL)
        return pattern.sub(lambda match: self._handle_for(match, context), template)

    def _handle_for(self, match, context):
        """Executes the foreach logic."""
        iterable = eval(match.group(1), {}, context)
        variable = match.group(2)
        block = match.group(3)

        result = []
        for item in iterable:
            local_context = context.copy()
            local_context[variable] = item
            result.append(self._render_block(block, local_context))
        return ''.join(result)

    def _render_block(self, block, context):
        """Render the inner block of each loop iteration."""
        # Just a basic rendering logic for now, later integrate with the main render function
        return block.format(**context)
