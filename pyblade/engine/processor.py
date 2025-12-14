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
    def render_trans(self, node: TransNode) -> str:
        # node.message is the args string, e.g. "'Hello'" or "'Hello' context 'ctx'"
        # We need to parse/eval it.
        try:
            # Simplified: just eval the first arg as message
            # TODO: Handle context, noop, etc. properly
            args = self.eval(f"({node.message})", self.context)
            if isinstance(args, tuple):
                message = args[0]
            else:
                message = args
            
            # TODO: Translation hook
            return str(message)
        except Exception as e:
            return f"<!-- Error translating '{node.message}': {e} -->"

    def render_blocktranslate(self, node: BlockTranslateNode) -> str:
        # Render body
        output = []
        for child_node in node.body:
            result = self.render_node(child_node)
            if result:
                output.append(result)
        content = "".join(output)
        
        # TODO: Translation hook with count/context
        return content

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
                print(f"DEBUG: Regrouped into {as_name}: {len(groups)} groups")
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
        # node.kwargs_expr is "a=1, b=2"
        # We want to update current query params with these.
        # But we don't have access to request.GET here easily unless in context.
        # Let's assume request is in context.
        request = self.context.get('request')
        query_dict = {}
        if request:
            query_dict = request.GET.copy().dict()
        
        try:
            updates = self.eval(f"dict({node.kwargs_expr})", self.context)
            query_dict.update(updates)
            
            # Encode
            from urllib.parse import urlencode
            return "?" + urlencode(query_dict)
        except:
            return ""

    def render_liveblade(self, node: LiveBladeNode) -> str:
        # Inject livewire/liveblade scripts
        return '<script src="/liveblade.js"></script>'

    def render_block(self, node: BlockNode) -> str:
        # Similar to section/yield.
        # In Django, block defines a block that can be overridden.
        # If we are extending, we store the block content.
        # If we are parent, we render the block content (either from child or default).
        
        name = self.eval(node.name, self.context)
        
        # Check if we have an override from a child
        # We need a way to pass blocks from child to parent.
        # In render_extends, we said we'd handle this.
        # But actually, inheritance usually works by rendering the child first,
        # collecting blocks, and then rendering the parent.
        # So if we are in a child (extending), we render the block body and store it.
        # If we are in the parent, we check if we have a stored block.
        
        blocks = self.context.get('__blocks', {})
        
        if '__extends' in self.context:
            # We are in a child template (or parsing one)
            # Render default content
            output = []
            for child_node in node.body:
                result = self.render_node(child_node)
                if result:
                    output.append(result)
            content = "".join(output)
            
            # Store it. If child defines it, it overrides.
            # But wait, if we are in child, we are defining the override.
            # So we store it.
            # But if we are in parent, we use it.
            # The issue is order. Child is rendered first?
            # If child is rendered first, it sets __blocks['name'] = content.
            # Then parent is rendered. It sees __blocks['name'] and uses it.
            # If not present, it renders its own body.
            
            # So here:
            # If we are rendering, we check if we have an override.
            if name in blocks:
                return blocks[name]
            
            # If not, we render our body.
            # But wait, if we are the child, we ARE defining the block.
            # So we should store our body into blocks[name].
            # But we only do that if we are extending?
            # Yes.
            
            # Actually, the logic is:
            # 1. Child renders. It sees @extends. It sets __extends.
            # 2. Child sees @block. It renders body and puts into __blocks.
            # 3. Child finishes.
            # 4. Processor sees __extends. It loads parent.
            # 5. Processor renders parent.
            # 6. Parent sees @block. It checks __blocks. If found, returns it. Else renders body.
            
            # So:
            # If we are in "recording mode" (child), we store.
            # If we are in "rendering mode" (parent), we use.
            # How do we know?
            # We can check if we are currently extending?
            # But render_extends sets __extends.
            
            # Let's assume if we are in the "first pass" (child), we store.
            # But we don't have passes.
            # We just render.
            
            # If we are extending, we shouldn't output anything except blocks?
            # Yes.
            
            # So:
            output = []
            for child_node in node.body:
                result = self.render_node(child_node)
                if result:
                    output.append(result)
            content = "".join(output)
            
            # Always store/update?
            # If we are child, we want to override.
            # If we are parent, we want to use override if exists.
            
            # If name is already in blocks, it means a child (or previous block) defined it.
            # So we use it?
            # No, if we are parent, we use it.
            # If we are child, we define it.
            
            # This implies we need to know if we are "defining" or "using".
            # In Django, the child template is parsed, blocks are extracted.
            # Then parent is rendered with those blocks.
            
            # Here we are executing directives.
            # If we are in child, we execute @block.
            # We should store it.
            
            # If we are in parent, we execute @block.
            # We should check if stored, else use default.
            
            # How to distinguish?
            # Maybe we can just always store if not present?
            # No.
            
            # Let's look at `render_section`.
            # It stores in `__sections`.
            # And `render_yield` uses it.
            # `@block` is like a combination of section and yield.
            
            # If we have `__blocks` in context, check if `name` is there.
            if name in blocks:
                return blocks[name]
            
            # If not, render body.
            # But we also need to store it in case a parent needs it?
            # No, parent is rendered AFTER child?
            # If parent is rendered after child, then child has already populated `blocks`.
            # So when parent runs, `name` IS in `blocks`.
            # So parent returns `blocks[name]`.
            # This works!
            
            # BUT, what if we are the child?
            # We render body. We store it in `blocks`.
            # And we return "" (because child output is discarded except blocks).
            
            # So:
            # 1. Render body -> content.
            # 2. If `name` NOT in `blocks` (or we want to override?):
            #    Actually, if we are child, we want to SET `blocks[name]`.
            #    If we are parent, we want to GET `blocks[name]`.
            
            # The problem is we use the SAME `render_block` function.
            
            # If we are child, we run first. `blocks` is empty.
            # We set `blocks[name] = content`.
            # We return "" (because `render_extends` suppresses output? No, `render_extends` returns "", but other nodes might return string).
            # But if we are extending, the main `render` loop should probably discard output that is not in a block?
            # Or `render_block` returns "" if extending?
            
            # If we are parent, we run second. `blocks` has content.
            # We check `blocks`. It has content. We return it.
            
            # This seems to work for 1 level of inheritance.
            # Child: `blocks[name] = content`. Returns "".
            # Parent: `blocks[name]` exists. Returns it.
            
            # What if parent has default content?
            # Parent runs. `blocks[name]` exists (from child). Returns it.
            # Parent body is NOT rendered?
            # Correct.
            
            # What if child didn't define it?
            # Parent runs. `blocks[name]` not in `blocks`.
            # Parent renders its own body. Returns it.
            
            # So the logic is:
            # 1. If `name` in `blocks`: return `blocks[name]`.
            # 2. Else:
            #    Render body -> content.
            #    If we are extending (child), store `blocks[name] = content` and return "".
            #    If we are not extending (base/standalone), return `content`.
            
            # Wait, if we are child, we run FIRST.
            # So `name` is NOT in `blocks`.
            # We render body.
            # We store in `blocks`.
            # We return "".
            
            # Then parent runs.
            # `name` IS in `blocks`.
            # We return `blocks[name]`.
            
            # This looks correct!
            
            # One catch: `{{ block.super }}`.
            # If child wants to include parent content.
            # This requires access to parent's block content.
            # But parent hasn't rendered yet!
            # This is the tricky part of inheritance.
            # Usually requires 2 passes or lazy rendering.
            # For now, let's ignore `block.super` or implement simple override.
            
            if name in blocks:
                return blocks[name]
            
            # Render body
            output = []
            for child_node in node.body:
                result = self.render_node(child_node)
                if result:
                    output.append(result)
            content = "".join(output)
            
            # If we are extending, store and hide.
            # How do we know if we are extending?
            # `render_extends` sets `__extends`.
            # But `render_extends` might be at the top of the file.
            # So `__extends` should be set.
            
            if self.context.get('__extends'):
                self.context.setdefault('__blocks', {})[name] = content
                return ""
            
            # If not extending, just return content
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
