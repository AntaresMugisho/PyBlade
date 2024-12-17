"""
Directive parsing implementation for the template engine.
"""
import ast
import re
from typing import Any, Dict, Match, Pattern, Tuple, Optional
from ..exceptions import DirectiveParsingError
from ..contexts import LoopContext


class DirectiveParser:
    """Handles parsing and processing of template directives."""

    # Cached regex patterns
    _FOR_PATTERN: Pattern = re.compile(
        r"@for\s*\((.*?)\s+in\s+(.*?)\)\s*(.*?)(?:@empty\s*(.*?))?@endfor",
        re.DOTALL
    )
    _IF_PATTERN: Pattern = re.compile(
        r"@(if|elif|else)(?:\s*\((?P<expression>.*?)\))?\s*(?P<content>.*?)(?=@(?:elif|else|endif)|$)",
        re.DOTALL
    )
    _UNLESS_PATTERN: Pattern = re.compile(
        r"@unless\s*\((?P<expression>.*?)\)(?P<slot>.*?)@endunless",
        re.DOTALL
    )
    _COMMENTS_PATTERN: Pattern = re.compile(r"{#(.*?)#}", re.DOTALL)

    def __init__(self):
        self._context: Dict[str, Any] = {}

    def parse_directives(self, template: str, context: Dict[str, Any]) -> str:
        """
        Process all directives within a template.
        
        Args:
            template: The template string
            context: The context dictionary
            
        Returns:
            The processed template
        """
        self._context = context

        # Process directives in order
        template = self._parse_comments(template)
        template = self._parse_for(template)
        template = self._parse_if(template)
        template = self._parse_unless(template)
        
        return template

    def _parse_for(self, template: str) -> str:
        """Process @for loops with @empty fallback."""
        return self._FOR_PATTERN.sub(
            lambda match: self._handle_for(match),
            template
        )

    def _handle_for(self, match: Match) -> str:
        """Handle @for loop logic with proper error handling."""
        try:
            variable = match.group(1)
            iterable_expression = match.group(2)
            block = match.group(3)
            empty_block = match.group(4)

            try:
                iterable = eval(iterable_expression, {}, self._context)
            except Exception as e:
                raise DirectiveParsingError(
                    f"Error evaluating iterable expression '{iterable_expression}': {str(e)}"
                )

            if not iterable:
                return empty_block if empty_block else ""

            result = []
            current_loop = self._context.get("loop")
            loop = LoopContext(iterable, parent=current_loop)

            for index, item in enumerate(iterable):
                loop.index = index
                local_context = {
                    **self._context,
                    variable: item,
                    "loop": loop,
                }

                parsed_block = self.parse_directives(block, local_context)
                should_break, parsed_block = self._parse_break(parsed_block, local_context)
                should_continue, parsed_block = self._parse_continue(parsed_block, local_context)

                if should_break:
                    break
                if should_continue:
                    continue

                result.append(parsed_block)

            return "".join(result)

        except Exception as e:
            raise DirectiveParsingError(f"Error in @for directive: {str(e)}")

    def _parse_if(self, template: str) -> str:
        """Process @if, @elif, and @else directives."""
        def replace_if(match: Match) -> str:
            try:
                directive = match.group(1)
                expression = match.group('expression')
                content = match.group('content')

                if directive == 'if' or directive == 'elif':
                    try:
                        condition = eval(expression, {}, self._context)
                    except Exception as e:
                        raise DirectiveParsingError(
                            f"Error evaluating condition '{expression}': {str(e)}"
                        )
                    return content if condition else ""
                else:  # else
                    return content

            except Exception as e:
                raise DirectiveParsingError(f"Error in @{directive} directive: {str(e)}")

        return self._IF_PATTERN.sub(replace_if, template)

    def _parse_unless(self, template: str) -> str:
        """Process @unless directives."""
        def replace_unless(match: Match) -> str:
            try:
                expression = match.group('expression')
                slot = match.group('slot')

                try:
                    condition = eval(expression, {}, self._context)
                except Exception as e:
                    raise DirectiveParsingError(
                        f"Error evaluating unless condition '{expression}': {str(e)}"
                    )

                return "" if condition else slot

            except Exception as e:
                raise DirectiveParsingError(f"Error in @unless directive: {str(e)}")

        return self._UNLESS_PATTERN.sub(replace_unless, template)

    @staticmethod
    def _parse_comments(template: str) -> str:
        """Remove template comments."""
        return DirectiveParser._COMMENTS_PATTERN.sub("", template)

    @staticmethod
    def _parse_break(template: str, context: Dict[str, Any]) -> Tuple[bool, str]:
        """Process @break directives."""
        pattern = re.compile(r"@break(?:\s*\(\s*(?P<expression>.*?)\s*\))?", re.DOTALL)
        match = pattern.search(template)

        if match:
            template = pattern.sub("", template)
            expression = match.group("expression")
            if not expression:
                return True, template
            try:
                if eval(expression, {}, context):
                    return True, template
            except Exception as e:
                raise DirectiveParsingError(f"Error in @break directive: {str(e)}")
        return False, template

    @staticmethod
    def _parse_continue(template: str, context: Dict[str, Any]) -> Tuple[bool, str]:
        """Process @continue directives."""
        pattern = re.compile(r"@continue(?:\s*\(\s*(?P<expression>.*?)\s*\))?", re.DOTALL)
        match = pattern.search(template)

        if match:
            template = pattern.sub("", template)
            expression = match.group("expression")
            if not expression:
                return True, template
            try:
                if eval(expression, {}, context):
                    return True, template
            except Exception as e:
                raise DirectiveParsingError(f"Error in @continue directive: {str(e)}")
        return False, template
