import re


class LoopContext:
    """Holds context information for loops."""

    def __init__(self, items):
        self._total_items = len(items)
        self._current_index = 0

    @property
    def index(self):
        return self._current_index

    @property
    def iteration(self):
        return self._current_index + 1

    @property
    def remaining(self):
        return self._total_items - self.iteration

    @property
    def count(self):
        return self._total_items

    @property
    def first(self):
        return self.index == 0

    @property
    def last(self):
        return self.iteration == self.count

    @property
    def even(self):
        return self.iteration % 2 == 0

    @property
    def odd(self):
        return self.iteration % 2 != 0

    def _depth(self):
        """Should return the nesting level of the current loop."""
        pass

    def _parent(self):
        """Should return the parent's loop variable, when in a nested loop."""
        pass

    def advance(self):
        self._current_index += 1


class PyBladeDirectives:

    def __init__(self):
        self.directives = {
            "if": self._parse_if,
            "for": self._parse_for
        }

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

        variable = match.group(1)
        iterable = eval(match.group(2), {}, context)

        # Empty handling if iterable is None or empty
        if iterable is None or len(iterable) == 0:
            empty_content = re.search(r'@empty(.*?)@endfor', content, re.DOTALL)
            return empty_content.group(1).strip() if empty_content else ''

        block = match.group(3)




        print(iterable)
        print(variable)
        print(block)

        result = []
        for item in iterable:
            local_context = {
                variable: item
            }

            # Create extra helpful variables in the loop

            result.append(self._render_block(block, local_context))

        # print(result)
        return ''.join(result)

    def _render_block(self, block, context):
        """Render the inner block of each loop iteration."""
        print("###")
        print(context)
        return block.format(**context)
