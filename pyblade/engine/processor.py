"""
Core template processing functionality.
"""

import html
from typing import Any, Dict

from pyblade.config import settings

from .cache import TemplateCache
from .contexts import LoopContext
from .evaluator import ExpressionEvaluator
from .lexer import Lexer
from .nodes import (
    AuthNode,
    BreakNode,
    ClassNode,
    CommentNode,
    ComponentNode,
    ContinueNode,
    CsrfNode,
    CycleNode,
    ExtendsNode,
    FirstOfNode,
    ForNode,
    GuestNode,
    IfNode,
    IncludeNode,
    MethodNode,
    Node,
    PythonNode,
    SectionNode,
    SlotNode,
    StaticNode,
    StyleNode,
    SwitchNode,
    TextNode,
    UnlessNode,
    UrlNode,
    VarNode,
    VerbatimNode,
    YieldNode,
)
from .exceptions import (
    BreakLoop,
    ContinueLoop,
    DirectiveParsingError,
    TemplateRenderError,
)
from .parser import Parser


class TemplateProcessor:
    """
    Main template processing class that coordinates parsing, caching,
    and rendering of templates.
    """

    def __init__(self, cache_size: int = 1000, cache_ttl: int = 3600, debug: bool = None, framework: str = None):
        self.cache = TemplateCache(max_size=cache_size, ttl=cache_ttl)
        self.framework = settings.framework  # 'django', 'fastapi', 'flask', or None
        self._debug = debug
        self.context = {}

    def render(
        self, template: str, context: Dict[str, Any], template_name: str = None, template_path: str = None
    ) -> str:
        """
        Render a template with the given context.

        Args:
            template: The template string to render
            context: The context dictionary
            template_name: Optional name of the template file

        Returns:
            The rendered template

        Raises:
            TemplateRenderError: If there's an error during rendering
        """
        self.context = context

        # Check cache first
        cached_result = self.cache.get(template, context)
        if cached_result is not None:
            return cached_result

        try:
            lexer = Lexer(template)
            tokens = lexer.tokenize()

            parser = Parser(tokens)
            ast = parser.parse()

            output = []
            for node in ast:
                result = self.render_node(node)
                if result is not None:
                    output.append(str(result))

            result = "".join(output)

            # Save cache
            self.cache.set(template, context, result)

            return result

        except Exception as e:
            raise e

    def clear_cache(self) -> None:
        """Clear the template cache."""
        self.cache.clear()

    def invalidate_template(self, template: str, context: Dict[str, Any]) -> None:
        """
        Invalidate a specific template in the cache.

        Args:
            template: The template string
            context: The context dictionary
        """
        self.cache.invalidate(template, context)

    def eval(self, expression: str, context: Dict[str, Any]) -> Any:
        evaluator = ExpressionEvaluator(context)
        return evaluator.evaluate(expression)

    # Directive renderers

    def render_node(self, node: Node) -> str:
        """Render a single node"""
        if isinstance(node, TextNode):
            return node.content

        elif isinstance(node, VarNode):
            return self.render_variable(node)

        elif isinstance(node, IfNode):
            return self.render_if(node)

        elif isinstance(node, ForNode):
            return self.render_for(node)

        elif isinstance(node, UnlessNode):
            return self.render_unless(node)

        elif isinstance(node, SwitchNode):
            return self.render_switch(node)

        elif isinstance(node, AuthNode):
            return self.render_auth(node)

        elif isinstance(node, GuestNode):
            return self.render_guest(node)

        elif isinstance(node, IncludeNode):
            return self.render_include(node)

        elif isinstance(node, ExtendsNode):
            return self.render_extends(node)

        elif isinstance(node, SectionNode):
            return self.render_section(node)

        elif isinstance(node, YieldNode):
            return self.render_yield(node)

        elif isinstance(node, ComponentNode):
            return self.render_component(node)

        elif isinstance(node, SlotNode):
            return self.render_slot(node)

        elif isinstance(node, VerbatimNode):
            return self.render_verbatim(node)

        elif isinstance(node, PythonNode):
            return self.render_python(node)

        elif isinstance(node, CommentNode):
            return self.render_comment(node)

        elif isinstance(node, CycleNode):
            return self.render_cycle(node)

        elif isinstance(node, FirstOfNode):
            return self.render_firstof(node)

        elif isinstance(node, UrlNode):
            return self.render_url(node)

        elif isinstance(node, StaticNode):
            return self.render_static(node)

        elif isinstance(node, CsrfNode):
            return self.render_csrf(node)

        elif isinstance(node, MethodNode):
            return self.render_method(node)

        elif isinstance(node, StyleNode):
            return self.render_style(node)

        elif isinstance(node, ClassNode):
            return self.render_class(node)

        elif isinstance(node, BreakNode):
            return self.render_break(node)

        elif isinstance(node, ContinueNode):
            return self.render_continue(node)

        return ""

    # RENDERER FUNCTIONS
    def render_variable(self, node: Node):
        try:
            # Use ExpressionEvaluator for method chaining support
            evaluator = ExpressionEvaluator(self.context)
            result = evaluator.evaluate(node.expression)

            # Convert wrapper objects to strings
            result_str = str(result)

            # Auto-escape HTML unless it's raw interpolation
            if node.escaped:
                return html.escape(result_str)
            else:
                return result_str

        except Exception as e:
            return f"<!-- Error rendering '{node.expression}': {e} -->"

    def render_if(self, node: IfNode) -> str:
        """Process @if, @elif, and @else directives."""

        try:
            condition_result = self.eval(node.condition, self.context)
            if condition_result:
                output = []
                for child_node in node.body:
                    result = self.render_node(child_node)
                    if result:
                        output.append(result)
                return "".join(output)
            else:
                found_elif = False
                for elif_cond, elif_body in node.elif_blocks:
                    elif_condition_result = self.eval(elif_cond, self.context)
                    if elif_condition_result:
                        output = []
                        for child_node in elif_body:
                            result = self.render_node(child_node)
                            if result:
                                output.append(result)
                        return "".join(output)
                        found_elif = True
                        break
                if not found_elif and node.else_body:
                    output = []
                    for child_node in node.else_body:
                        result = self.render_node(child_node)
                        if result:
                            output.append(result)
                    return "".join(output)
        except Exception as e:
            return f"<!-- Error evaluating if condition '{node.condition}': {e} -->"

        return ""

    def render_for(self, node: ForNode) -> str:
        try:
            from .wrappers import DictWrapper, ListWrapper, wrap_value

            iterable = self.eval(node.collection_expr, self.context)

            # Unwrap if it's a wrapper object
            if isinstance(iterable, DictWrapper):
                iterable = iterable._value
            elif isinstance(iterable, ListWrapper):
                iterable = iterable._value

            if not hasattr(iterable, '__iter__'):
                raise TypeError(f"'{node.collection_expr}' is not iterable.")

            if not iterable and node.empty_body:
                output = []
                for child_node in node.empty_body:
                    result = self.render_node(child_node)
                    if result:
                        output.append(result)
                return "".join(output)

            # Ensure collection is iterable for iteration
            items_to_iterate = list(iterable.items()) if isinstance(iterable, dict) else list(iterable)

            # Backup potential variable name in the context
            old_value = self.context.get(node.item_var)
            old_loop = self.context.get("loop")

            loop = LoopContext(items_to_iterate, parent=old_loop)

            output = []
            for i, item in enumerate(items_to_iterate):
                loop.index = i
                wrapped_item = wrap_value(item)
                self.context[node.item_var] = wrapped_item
                self.context["loop"] = loop

                try:
                    for child_node in node.body:
                        result = self.render_node(child_node)
                        if result:
                            output.append(result)
                except BreakLoop:
                    break
                except ContinueLoop:
                    continue

            # Restore old values
            if old_value is not None:
                self.context[node.item_var] = old_value
            else:
                self.context.pop(node.item_var, None)

            if old_loop is not None:
                self.context["loop"] = old_loop
            else:
                self.context.pop("loop", None)

            return "".join(output)

        except Exception as e:
            return f"<!-- Error evaluating for loop '{node.collection_expr}': {e} -->"
    def render_unless(self, node: UnlessNode) -> str:
        """Process @unless directive."""
        try:
            condition_result = self.eval(node.condition, self.context)
            if not condition_result:
                output = []
                for child_node in node.body:
                    result = self.render_node(child_node)
                    if result:
                        output.append(result)
                return "".join(output)
        except Exception as e:
            return f"<!-- Error evaluating unless condition '{node.condition}': {e} -->"
        return ""

    def render_switch(self, node: SwitchNode) -> str:
        """Process @switch directive."""
        try:
            switch_value = self.eval(node.expression, self.context)
            
            for case_val_expr, case_body in node.cases:
                case_value = self.eval(case_val_expr, self.context)
                if switch_value == case_value:
                    output = []
                    for child_node in case_body:
                        result = self.render_node(child_node)
                        if result:
                            output.append(result)
                    return "".join(output)
            
            if node.default_body:
                output = []
                for child_node in node.default_body:
                    result = self.render_node(child_node)
                    if result:
                        output.append(result)
                return "".join(output)
                
        except Exception as e:
            return f"<!-- Error evaluating switch '{node.expression}': {e} -->"
        return ""

    def render_auth(self, node: AuthNode) -> str:
        """Process @auth directive."""
        # Check if user is authenticated
        # We assume 'user' or 'request' is in context
        user = self.context.get("user")
        request = self.context.get("request")
        
        is_authenticated = False
        if user:
            is_authenticated = getattr(user, "is_authenticated", False)
            if callable(is_authenticated):
                is_authenticated = is_authenticated()
        elif request:
            user = getattr(request, "user", None)
            if user:
                is_authenticated = getattr(user, "is_authenticated", False)
                if callable(is_authenticated):
                    is_authenticated = is_authenticated()
        
        # TODO: Handle guard if provided
        
        if is_authenticated:
            output = []
            for child_node in node.body:
                result = self.render_node(child_node)
                if result:
                    output.append(result)
            return "".join(output)
        elif node.else_body:
            output = []
            for child_node in node.else_body:
                result = self.render_node(child_node)
                if result:
                    output.append(result)
            return "".join(output)
        return ""

    def render_guest(self, node: GuestNode) -> str:
        """Process @guest directive."""
        # Inverse of auth
        user = self.context.get("user")
        request = self.context.get("request")
        
        is_authenticated = False
        if user:
            is_authenticated = getattr(user, "is_authenticated", False)
            if callable(is_authenticated):
                is_authenticated = is_authenticated()
        elif request:
            user = getattr(request, "user", None)
            if user:
                is_authenticated = getattr(user, "is_authenticated", False)
                if callable(is_authenticated):
                    is_authenticated = is_authenticated()
        
        if not is_authenticated:
            output = []
            for child_node in node.body:
                result = self.render_node(child_node)
                if result:
                    output.append(result)
            return "".join(output)
        elif node.else_body:
            output = []
            for child_node in node.else_body:
                result = self.render_node(child_node)
                if result:
                    output.append(result)
            return "".join(output)
        return ""

    def render_include(self, node: IncludeNode) -> str:
        """Process @include directive."""
        # node.path contains the args string, e.g. "'partials.header', {'a': 1}"
        # We need to parse/eval this to get path and data.
        # This is a bit hacky, but we can eval the whole tuple.
        try:
            args_tuple = self.eval(f"({node.path})", self.context)
            if not isinstance(args_tuple, tuple):
                args_tuple = (args_tuple,)
            
            path = args_tuple[0]
            data = args_tuple[1] if len(args_tuple) > 1 else {}
            
            # Load template
            # We need a way to load template. Processor doesn't have loader directly?
            # It imports loader? No, it imports TemplateCache.
            # We need to import loader.
            from . import loader
            
            # Convert dot notation to path if needed (simple heuristic)
            if not path.endswith(".html") and "." in path:
                path = path.replace(".", "/") + ".html"
                
            template = loader.load_template(path)
            
            # Merge context
            new_context = self.context.copy()
            new_context.update(data)
            
            # Render included template
            # We can create a new processor or use current one?
            # Using current one might be tricky with recursion limit, but fine for now.
            # Actually, loader.load_template returns a Template object which has a render method.
            return template.render(new_context)
            
        except Exception as e:
            return f"<!-- Error including '{node.path}': {e} -->"

    def render_extends(self, node: ExtendsNode) -> str:
        """Process @extends directive."""
        try:
            layout_path = self.eval(node.layout, self.context)
            self.context['__extends'] = layout_path
            return ""
        except Exception as e:
            return f"<!-- Error extending '{node.layout}': {e} -->"

    def render_section(self, node: SectionNode) -> str:
        """Process @section directive."""
        # Render body
        output = []
        for child_node in node.body:
            result = self.render_node(child_node)
            if result:
                output.append(result)
        content = "".join(output)
        
        # Store in context
        name = self.eval(node.name, self.context)
        self.context.setdefault('__sections', {})[name] = content
        
        return ""

    def render_yield(self, node: YieldNode) -> str:
        """Process @yield directive."""
        name = self.eval(node.name, self.context)
        sections = self.context.get('__sections', {})
        content = sections.get(name)
        
        if content is None:
            # Default
            if node.default:
                return self.eval(node.default, self.context)
            return ""
        return content

    def render_component(self, node: ComponentNode) -> str:
        """Process @component directive."""
        # Similar to include but with slots.
        # node.name contains args string.
        try:
            args_tuple = self.eval(f"({node.name})", self.context)
            if not isinstance(args_tuple, tuple):
                args_tuple = (args_tuple,)
            
            name = args_tuple[0]
            data = args_tuple[1] if len(args_tuple) > 1 else {}
            
            # Load component template
            from . import loader
            
            # Render body (default slot)
            output = []
            for child_node in node.body:
                result = self.render_node(child_node)
                if result:
                    output.append(result)
            slot_content = "".join(output)
            
            new_context = self.context.copy()
            new_context.update(data)
            new_context['slot'] = slot_content
            
            # Let's try to load template
            # If name is "alert", it might be "components/alert.html"
            path = f"components/{name}.html" # Simplified
            template = loader.load_template(path)
            
            return template.render(new_context)
            
        except Exception as e:
            return f"<!-- Error rendering component '{node.name}': {e} -->"

    def render_slot(self, node: SlotNode) -> str:
        """Process @slot directive."""
        # Render body
        output = []
        for child_node in node.body:
            result = self.render_node(child_node)
            if result:
                output.append(result)
        content = "".join(output)
        
        name = self.eval(node.name, self.context)
        self.context[name] = content
        return ""

    def render_verbatim(self, node: VerbatimNode) -> str:
        return node.content

    def render_python(self, node: PythonNode) -> str:
        # Execute python code?
        # For now, maybe just ignore or comment?
        # Docs said "not to include raw Python code execution".
        # But we added it.
        # Let's try to exec it?
        # exec(node.code, {}, self.context)
        return ""

    def render_comment(self, node: CommentNode) -> str:
        return ""

    def render_cycle(self, node: CycleNode) -> str:
        # node.values is args string e.g. "('odd', 'even')"
        try:
            values = self.eval(f"({node.values})", self.context)
            if not isinstance(values, (list, tuple)):
                values = [values]
            
            # We need to track state.
            # Use a unique key for this cycle? Or just loop index?
            # Cycle usually depends on loop.
            loop = self.context.get('loop')
            if loop:
                index = loop.index
                return str(values[index % len(values)])
            return str(values[0])
        except Exception as e:
            return ""

    def render_firstof(self, node: FirstOfNode) -> str:
        try:
            args = self.eval(f"({node.values})", self.context)
            if not isinstance(args, tuple):
                args = (args,)
            
            for arg in args:
                if arg:
                    return str(arg)
            return ""
        except:
            return ""

    def render_url(self, node: UrlNode) -> str:
        # node.name is args string
        # We can reuse directives.py logic or simplified
        return ""

    def render_static(self, node: StaticNode) -> str:
        path = self.eval(node.path, self.context)
        # Return static url
        return f"/static/{path}"

    def render_csrf(self, node: CsrfNode) -> str:
        token = self.context.get('csrf_token', '')
        return f'<input type="hidden" name="csrfmiddlewaretoken" value="{token}">'

    def render_method(self, node: MethodNode) -> str:
        method = self.eval(node.method, self.context)
        return f'<input type="hidden" name="_method" value="{method}">'

    def render_style(self, node: StyleNode) -> str:
        try:
            styles = self.eval(node.expression, self.context)
            if isinstance(styles, dict):
                final_styles = []
                for k, v in styles.items():
                    if v:
                        final_styles.append(k.strip())
                
                if final_styles:
                    return f'style="{" ".join(final_styles)}"'
        except:
            pass
        return ""

    def render_class(self, node: ClassNode) -> str:
        try:
            classes = self.eval(node.expression, self.context)
            if isinstance(classes, dict):
                class_list = [k for k, v in classes.items() if v]
                if class_list:
                    return f'class="{" ".join(class_list)}"'
        except:
            pass
        return ""

    def render_break(self, node: BreakNode) -> str:
        if node.condition:
            if self.eval(node.condition, self.context):
                raise BreakLoop()
        else:
            raise BreakLoop()
        return ""

    def render_continue(self, node: ContinueNode) -> str:
        if node.condition:
            if self.eval(node.condition, self.context):
                raise ContinueLoop()
        else:
            raise ContinueLoop()
        return ""
