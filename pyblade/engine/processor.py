"""
Core template processing functionality.
"""

import html
import gettext
from typing import Any, Dict
import re


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
    AutocompleteNode,
    BlockNode,
    BlockTranslateNode,
    CheckedNode,
    GetMediaPrefixNode,
    GetStaticPrefixNode,
    LiveBladeNode,
    NowNode,
    QuerystringNode,
    RatioNode,
    RegroupNode,
    RequiredNode,
    SelectedNode,
    TransNode,
    WithNode,
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

        elif isinstance(node, TransNode):
            return self.render_trans(node)

        elif isinstance(node, BlockTranslateNode):
            return self.render_blocktranslate(node)

        elif isinstance(node, WithNode):
            return self.render_with(node)

        elif isinstance(node, NowNode):
            return self.render_now(node)

        elif isinstance(node, RegroupNode):
            return self.render_regroup(node)

        elif isinstance(node, SelectedNode):
            return self.render_selected(node)

        elif isinstance(node, RequiredNode):
            return self.render_required(node)

        elif isinstance(node, CheckedNode):
            return self.render_checked(node)

        elif isinstance(node, AutocompleteNode):
            return self.render_autocomplete(node)

        elif isinstance(node, RatioNode):
            return self.render_ratio(node)

        elif isinstance(node, GetStaticPrefixNode):
            return self.render_get_static_prefix(node)

        elif isinstance(node, GetMediaPrefixNode):
            return self.render_get_media_prefix(node)

        elif isinstance(node, QuerystringNode):
            return self.render_querystring(node)

        elif isinstance(node, LiveBladeNode):
            return self.render_liveblade(node)

        elif isinstance(node, BlockNode):
            return self.render_block(node)

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
            raise e

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
            raise e

        return ""

    def render_for(self, node: ForNode) -> str:
        try:
            from .wrappers import TDict, TList, wrap_value

            iterable = self.eval(node.collection_expr, self.context)

            # Unwrap if it's a wrapper object
            if isinstance(iterable, TDict):
                iterable = iterable._value
            elif isinstance(iterable, TList):
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
            raise e

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
            raise e

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
            raise e

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
            
            from . import loader                
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
            raise e

    def render_extends(self, node: ExtendsNode) -> str:
        """Process @extends directive."""
        try:
            layout_path = self.eval(node.layout, self.context)
            self.context['__extends'] = layout_path
            return ""
        except Exception as e:
            raise e

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
    def render_trans(self, node: TransNode) -> str:

        try:
            # 1. Normalize argument string
            args_str = node.message.strip()
            if args_str.startswith("(") and args_str.endswith(")"):
                args_str = args_str[1:-1]

            # --------------------------------------------------
            # 2. Detect Django-style: 'message' as variable
            # --------------------------------------------------
            as_variable = None

            as_match = re.search(
                r"""
                ^
                \s*
                (?P<msg>['"].+?['"])
                \s+as\s+
                (?P<var>[a-zA-Z_][a-zA-Z0-9_]*)
                \s*$
                """,
                args_str,
                re.VERBOSE,
            )

            if as_match:
                args_str = as_match.group("msg")
                as_variable = as_match.group("var")

            # --------------------------------------------------
            # 3. Safe argument extraction
            # --------------------------------------------------
            def _extract(*args, **kwargs):
                return args, kwargs

            eval_context = dict(self.context)
            eval_context["_extract"] = _extract

            extracted_args, extracted_kwargs = self.eval(
                f"_extract({args_str})",
                eval_context
            )

            # --------------------------------------------------
            # 4. Validate message
            # --------------------------------------------------
            if not extracted_args:
                raise ValueError("@trans requires a string literal")

            message = extracted_args[0]

            if not isinstance(message, str):
                raise TypeError("@trans message must be a string literal")

            msg_context = extracted_kwargs.get("context")
            noop = extracted_kwargs.get("noop", False)

            if noop:
                translated = message
            else:
                try:
                    from django.utils.translation import gettext_lazy, pgettext
                except ImportError as exc:
                    raise RuntimeError(
                        "Django is required to use @trans directive"
                    ) from exc

                if msg_context:
                    if not isinstance(msg_context, str):
                        raise TypeError("context must be a string")
                    translated = pgettext(msg_context, message)
                else:
                    translated = gettext_lazy(message)

            # --------------------------------------------------
            # 5. Assignment mode (@trans('...' as var))
            # --------------------------------------------------
            if as_variable:
                self.context[as_variable] = translated
                return ""

            # --------------------------------------------------
            # 6. Direct output
            # --------------------------------------------------
            return translated

        except Exception:
            raise


    def render_blocktranslate(self, node: BlockTranslateNode) -> str:
        # node.count holds the args string, e.g. "(count=counter, trimmed=True)"
        # Parse args
        count_val = None
        context_val = None
        trimmed_val = False
        
        try:
            if node.count:
                # Strip outer parens if present
                args_str = node.count.strip()
                if args_str.startswith("(") and args_str.endswith(")"):
                    args_str = args_str[1:-1]
                    
                # Use the same extraction trick
                def _extract(*args, **kwargs):
                    return args, kwargs
                
                # node.count might be just "count=counter" or "counter" (positional?)
                # Docs say: @blocktranslate(count=counter)
                extracted_args, extracted_kwargs = self.eval(f"_extract({args_str})", {**self.context, "_extract": _extract})
                
                # If positional args, assume first is count? Or maybe no positional args allowed?
                # Let's assume kwargs mostly.
                count_val = extracted_kwargs.get('count')
                context_val = extracted_kwargs.get('context')
                trimmed_val = extracted_kwargs.get('trimmed', False)
        except Exception:
            # Fallback or ignore error
            pass
            
        # Render body (singular)
        output = []
        for child_node in node.body:
            result = self.render_node(child_node)
            if result:
                output.append(result)
        singular_content = "".join(output)
        
        if trimmed_val:
            singular_content = singular_content.strip()
            
        # Render plural body if exists
        plural_content = None
        if node.plural_body:
            output_plural = []
            for child_node in node.plural_body:
                result = self.render_node(child_node)
                if result:
                    output_plural.append(result)
            plural_content = "".join(output_plural)
            
            if trimmed_val:
                plural_content = plural_content.strip()
        
        # Translate
        translated = ""
        if count_val is not None and plural_content is not None:
            if context_val:
                translated = gettext.npgettext(context_val, singular_content, plural_content, count_val)
            else:
                translated = gettext.ngettext(singular_content, plural_content, count_val)
        else:
            if context_val:
                translated = gettext.pgettext(context_val, singular_content)
            else:
                translated = gettext.gettext(singular_content)
                
        # Perform variable substitution
        # The translated string might contain Python-style formatting placeholders like %(name)s
        # We should format it with the current context.
        try:
            # We can use the context directly?
            # But context might have objects that are not strings.
            # And the placeholders must match context keys.
            # Also, 'count' should be available as 'count' in the format?
            # Django adds 'count' to the context for formatting.
            format_context = self.context.copy()
            if count_val is not None:
                format_context['count'] = count_val
                
            return translated % format_context
        except Exception:
            # If formatting fails (e.g. missing key), return as is or try safe format?
            # For now return as is to avoid crashing, but maybe log warning.
            return translated

    def render_with(self, node: WithNode) -> str:
        # node.variables is args string, e.g. "a=1, b=2"
        # We need to parse this into a dict.
        # We can try to eval "dict(a=1, b=2)"?
        # Or just parse it manually if it's "var as name".
        # Django uses "val as name". PyBlade usually uses Python args.
        # Let's assume Python args: @with(a=1, b=2)
        try:
            # We can't eval "dict(a=1)" directly if a is not defined?
            # No, a=1 means keyword arg a with value 1.
            # So eval("dict(" + node.variables + ")", ...) should work.
            # But we need to be careful about context.
            
            # Create a temporary scope
            new_context = self.context.copy()
            
            # Parse variables
            # If node.variables is "a=1, b=2"
            # We wrap in dict(...) but we need to be careful about parens.
            # If node.variables already has parens?
            # parser._parse_with takes args_str.
            # If @with(a=1), args_str is "a=1".
            # So dict(a=1) is valid.
            # But debug output said "dict((a=1, b=2))".
            # This means node.variables was "(a=1, b=2)".
            # So parser included parens in args_str?
            # Let's strip parens in parser or here.
            vars_str = node.variables.strip()
            if vars_str.startswith("(") and vars_str.endswith(")"):
                vars_str = vars_str[1:-1]
            
            vars_dict = self.eval(f"dict({vars_str})", self.context)
            new_context.update(vars_dict)
            
            # Render body with new context
            # We need to temporarily swap context
            old_context = self.context
            self.context = new_context
            
            output = []
            try:
                for child_node in node.body:
                    result = self.render_node(child_node)
                    if result:
                        output.append(result)
            finally:
                self.context = old_context
                
            return "".join(output)
            
        except Exception as e:
            return f"<!-- Error in @with: {e} -->"

    def render_now(self, node: NowNode) -> str:
        try:
            format_str = self.eval(node.format_string, self.context)
            from datetime import datetime
            return datetime.now().strftime(format_str)
        except Exception as e:
            return f"<!-- Error in @now: {e} -->"

    def render_regroup(self, node: RegroupNode) -> str:
        # @regroup(target, by, as_name)
        # Debug output showed: safe_eval failed for '(cities': '(' was never closed
        # This implies node.target starts with '('.
        # Parser passes args_str. If @regroup(cities by country as list), args_str is "(cities by country as list)"?
        # Or "cities by country as list"?
        # Lexer captures parens if present.
        # Let's strip parens first.
        
        args_str = node.target.strip()
        if args_str.startswith("(") and args_str.endswith(")"):
            args_str = args_str[1:-1]
            
        import re
        match = re.match(r"\s*(.+?)\s+by\s+(.+?)\s+as\s+(.+?)\s*$", args_str)
        if match:
            target_expr, by_expr, as_name = match.groups()
            
            target = self.eval(target_expr, self.context)
            # by_expr could be a key or attribute
            # We need to group target by by_expr.
            
            if not target:
                self.context[as_name] = []
                return ""
            
            # Grouping logic
            # We can use itertools.groupby but it requires sorting.
            # Or just a dict.
            # Django's regroup returns a list of namedtuples (grouper, list).
            
            groups = []
            if isinstance(target, (list, tuple)):
                # We need to get the key for each item
                # by_expr might be "date.year"
                
                # Helper to get attr/item
                def get_key(item, key_path):
                    current = item
                    for part in key_path.split('.'):
                        if isinstance(current, dict):
                            current = current.get(part)
                        else:
                            current = getattr(current, part, None)
                        if current is None: break
                    return current

                # Sort first? Django regroup expects sorted list or sorts it?
                # Django docs say "Regroup expects the list to be sorted".
                # But we can sort it here to be safe or just group consecutive?
                # "itertools.groupby ... picks out contiguous items with the same key".
                # So we should probably sort if we want full grouping, but maybe user sorted it.
                # Let's assume user sorted it or we just group consecutive.
                
                from itertools import groupby
                
                # We need to resolve key for each item
                # This is complex to do with eval inside loop.
                # Simplified: assume by_expr is a simple attribute path
                
                key_func = lambda x: get_key(x, by_expr)
                
                for key, group in groupby(target, key=key_func):
                    groups.append({'grouper': key, 'list': list(group)})
                
                self.context[as_name] = groups
                return ""
                
        return "<!-- Invalid @regroup syntax -->"

    def render_selected(self, node: SelectedNode) -> str:
        if self.eval(node.condition, self.context):
            return "selected"
        return ""

    def render_required(self, node: RequiredNode) -> str:
        if self.eval(node.condition, self.context):
            return "required"
        return ""

    def render_checked(self, node: CheckedNode) -> str:
        if self.eval(node.condition, self.context):
            return "checked"
        return ""

    def render_autocomplete(self, node: AutocompleteNode) -> str:
        val = self.eval(node.value, self.context)
        return f'autocomplete="{val}"'

    def render_ratio(self, node: RatioNode) -> str:
        # node.width is args_str "w, h" or "(w, h)"
        try:
            args = self.eval(f"({node.width})", self.context)
            if isinstance(args, (list, tuple)) and len(args) == 2:
                w, h = args
                return f'style="aspect-ratio: {w}/{h};"'
        except:
            pass
        return ""

    def render_get_static_prefix(self, node: GetStaticPrefixNode) -> str:
        return "/static/" # TODO: Get from settings

    def render_get_media_prefix(self, node: GetMediaPrefixNode) -> str:
        return "/media/" # TODO: Get from settings

    def render_querystring(self, node: QuerystringNode) -> str:
        # node.kwargs_expr is "a=1, b=2" or "(a=1, b=2)"
        request = self.context.get('request')
        query_dict = {}
        if request:
            query_dict = request.GET.copy().dict()
        
        try:
            # Strip parens if present
            kwargs_expr = node.kwargs_expr.strip()
            if kwargs_expr.startswith("(") and kwargs_expr.endswith(")"):
                kwargs_expr = kwargs_expr[1:-1]
                
            updates = self.eval(f"dict({kwargs_expr})", self.context)
            query_dict.update(updates)
            
            # Encode
            from urllib.parse import urlencode
            return "?" + urlencode(query_dict)
        except Exception as e:
            return ""

    def render_liveblade(self, node: LiveBladeNode) -> str:
        # Inject livewire/liveblade scripts
        return '<script src="/liveblade.js"></script>'

    def render_block(self, node: BlockNode) -> str:
        name = self.eval(node.name, self.context)        
        blocks = self.context.get('__blocks', {})
        
        if name in blocks:
            return blocks[name]
            
        output = []
        for child_node in node.body:
            result = self.render_node(child_node)
            if result:
                output.append(result)
        content = "".join(output)
        
        if self.context.get('__extends'):
            self.context.setdefault('__blocks', {})[name] = content
            return ""
        
        return content
            
        return "" # Should not happen if logic matches

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
