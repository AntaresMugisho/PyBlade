import re

from pyblade.engine.exceptions import DirectiveParsingError, TemplateRenderError

from .lexer import Lexer
from .nodes import (
    AttributeNode,
    AuthNode,
    AutocompleteNode,
    AutoescapeNode,
    BlockNode,
    BlockTranslateNode,
    BreakNode,
    ClassNode,
    CommentNode,
    ComponentNode,
    ContinueNode,
    CsrfNode,
    CycleNode,
    DebugNode,
    ErrorNode,
    ExtendsNode,
    FieldNode,
    FirstOfNode,
    ForNode,
    GetMediaPrefixNode,
    GetStaticPrefixNode,
    GuestNode,
    IfChangedNode,
    IfNode,
    IncludeNode,
    LiveBladeNode,
    LoremNode,
    MethodNode,
    NowNode,
    ParentNode,
    PropsNode,
    PybladeScriptsNode,
    PybladeStylesNode,
    QuerystringNode,
    RatioNode,
    RegroupNode,
    ResetCycleNode,
    SectionNode,
    SlotNode,
    SpacelessNode,
    StaticNode,
    StyleNode,
    SwitchNode,
    TextNode,
    TranslateNode,
    UnlessNode,
    UrlNode,
    VarNode,
    VerbatimNode,
    WithNode,
    YieldNode,
    split_slots,
)


class Parser:
    """
    Parses a stream of tokens from the Lexer to build an Abstract Syntax Tree (AST).
    It understands the structure of PyBlade directives and variable display.
    """

    def __init__(self, tokens):
        self.tokens = tokens
        self.pos = 0  # Current position in the token list

    def current_token(self):
        """Returns the current token without advancing."""
        if self.pos < len(self.tokens):
            return self.tokens[self.pos]
        return None

    def advance(self, steps: int = 1):
        """Advances to the next token."""
        self.pos += steps
        return self.current_token()

    def expect(self, token_type, value_prefix=None):
        """
        Consumes the current token if it matches the expected type and (optional) value prefix.
        Raises SyntaxError if not matched.
        """
        token = self.current_token()
        if not token or token.type != token_type:
            line = token.line if token else None
            raise TemplateRenderError(
                f"Expected token of type '{token_type}' but got {token}.",
                line=line,
            )
        if value_prefix and not token.value.startswith(value_prefix):
            raise TemplateRenderError(
                f"Expected token value starting with '{value_prefix}' but got '{token.value}'",
                line=token.line,
            )
        self.advance()
        return token

    def parse(self):
        """Starts the parsing process and returns the root AST nodes."""
        ast = []
        while self.current_token():
            token = self.current_token()
            if token.type == "COMMENT_START":
                # Handle inline comments {# ... #}
                # Collect comment content
                comment_parts = []
                comment_line = token.line
                comment_column = token.column
                while self.current_token() and self.current_token().type != "COMMENT_END":
                    comment_parts.append(self.current_token().value)
                    self.advance()
                self.expect("COMMENT_END")
                ast.append(
                    CommentNode("".join(comment_parts[1:]), line=comment_line, column=comment_column)
                )  # The first part is the comment start marker {#
            elif token.type == "TEXT":
                ast.append(TextNode(token.value, line=token.line, column=token.column))
                self.advance()
            elif token.type == "VAR_START":
                ast.append(self._parse_variable(escaped=True))
            elif token.type == "UNESCAPED_VAR_START":
                ast.append(self._parse_variable(escaped=False))
            elif token.type == "PB_TAG_START":
                ast.append(self._parse_pb_component(token, paired=True))
            elif token.type == "PB_TAG_SELF_CLOSE":
                ast.append(self._parse_pb_component(token, paired=False))
            elif token.type == "PB_TAG_END":
                raise DirectiveParsingError(
                    f"Unexpected closing tag '{token.value}' without matching opening tag",
                    line=token.line,
                    column=token.column,
                )
            elif token.type == "DIRECTIVE":
                name, args = self._split_directive(token)
                self.advance()  # Consume the DIRECTIVE token
                ast.append(self._parse_directive(name, args, token))
            else:
                raise TemplateRenderError(
                    f"Unexpected token type: {token.type} with value '{token.value}'",
                    line=token.line,
                )
        return ast

    # Directives rendering an HTML attribute of the same name
    _attribute_directives = ("checked", "selected", "disabled", "readonly", "required", "multiple", "autofocus")

    # Directives closing a block, handled by the parser of the block they belong to.
    # Meeting one anywhere else means it is misplaced.
    _closing_directives = (
        "elif",
        "else",
        "empty",
        "case",
        "default",
        "plural",
        "endif",
        "endifchanged",
        "endfor",
        "endunless",
        "endswitch",
        "endmatch",
        "endauth",
        "endguest",
        "endcomponent",
        "endslot",
        "endverbatim",
        "endcomment",
        "endblocktranslate",
        "endwith",
        "endblock",
        "endsection",
        "enderror",
        "endspaceless",
        "endautoescape",
    )

    def _split_directive(self, token):
        """Splits a directive token into its name and its argument string, parentheses included."""
        match = re.match(r"@([a-zA-Z_][a-zA-Z0-9_]*)(.*)", token.value, re.DOTALL)
        if not match:
            raise DirectiveParsingError(
                f"Invalid directive format: {token.value}",
                line=token.line,
                column=token.column,
            )

        return match.group(1), match.group(2).strip()

    def _parse_directive(self, name, args, token):
        """Builds the node of a directive.

        The top level of a template and the body of a block both go through here, so
        that a directive means the same thing wherever it is written.
        """
        if name == "comment":
            return self._parse_comment(args, token)
        elif name == "pbscripts":
            return PybladeScriptsNode(line=token.line, column=token.column)
        elif name == "pbstyles":
            return PybladeStylesNode(line=token.line, column=token.column)
        elif name == "if":
            return self._parse_if(args, token)
        elif name == "unless":
            return self._parse_unless(args, token)
        elif name == "for":
            return self._parse_for(args, token)
        elif name in ("match", "switch"):
            return self._parse_switch(args, token, name)
        elif name == "auth":
            return self._parse_auth(args, token)
        elif name in ("guest", "anonymous"):
            return self._parse_guest(args, token)
        elif name == "ifchanged":
            return self._parse_ifchanged(args, token)
        elif name == "include":
            return self._parse_include(args, token)
        elif name == "extends":
            return self._parse_extends(args, token)
        elif name == "section":
            return self._parse_section(args, token)
        elif name == "yield":
            return self._parse_yield(args, token)
        elif name == "block":
            return self._parse_block(args, token)
        elif name == "parent":
            return ParentNode(line=token.line, column=token.column)
        elif name == "component":
            return self._parse_component(args, token)
        elif name == "props":
            return self._parse_props(args, token)
        elif name == "slot":
            return self._parse_slot(args, token)
        elif name == "with":
            return self._parse_with(args, token)
        elif name == "verbatim":
            return self._parse_verbatim(args, token)
        elif name == "cycle":
            return self._parse_cycle(args, token)
        elif name == "resetcycle":
            return self._parse_resetcycle(args, token)
        elif name == "firstof":
            return self._parse_firstof(args, token)
        elif name == "url":
            return self._parse_url(args, token)
        elif name == "static":
            return self._parse_static(args, token)
        elif name == "csrf":
            return CsrfNode(line=token.line, column=token.column)
        elif name == "method":
            return self._parse_method(args, token)
        elif name == "style":
            return self._parse_style(args, token)
        elif name == "class":
            return self._parse_class(args, token)
        elif name == "break":
            return self._parse_break(args, token)
        elif name == "continue":
            return self._parse_continue(args, token)
        elif name == "debug":
            return DebugNode(line=token.line, column=token.column)
        elif name == "lorem":
            return self._parse_lorem(args, token)
        elif name == "spaceless":
            return self._parse_spaceless(args, token)
        elif name in ("translate", "trans"):
            return self._parse_trans(args, token)
        elif name in ("blocktranslate", "blocktrans"):
            return self._parse_blocktranslate(args, token)
        elif name == "now":
            return self._parse_now(args, token)
        elif name == "regroup":
            return self._parse_regroup(args, token)
        elif name == "autoescape":
            return self._parse_autoescape(args, token)
        elif name in self._attribute_directives:
            return self._parse_attribute(name, args, token)
        elif name == "autocomplete":
            return self._parse_autocomplete(args, token)
        elif name == "field":
            return self._parse_field(args, token)
        elif name == "error":
            return self._parse_error(args, token)
        elif name == "ratio":
            return self._parse_ratio(args, token)
        elif name in ("get_static_prefix", "gsp"):
            return self._parse_get_static_prefix(args, token)
        elif name in ("get_media_prefix", "gmp"):
            return self._parse_get_media_prefix(args, token)
        elif name == "querystring":
            return self._parse_querystring(args, token)
        elif name == "live":
            return LiveBladeNode()
        elif name in self._closing_directives:
            raise DirectiveParsingError(
                f"Unexpected directive '@{name}' found. It might be missing an opening directive or misplaced.",
                line=token.line,
                column=token.column,
                help="You may have used a closing directive without \
                     it's opening correspondant. Check your template syntax.",
            )

        # Unknown directive, render as plain text
        return TextNode(token.value, line=token.line, column=token.column)

    def _parse_variable(self, escaped=True):
        """Parses a {{ expression }} or {!! expression !!} block."""
        if escaped:
            start_token = self.expect("VAR_START")
            end_token_type = "VAR_END"
        else:
            start_token = self.expect("UNESCAPED_VAR_START")
            end_token_type = "UNESCAPED_VAR_END"

        expr_parts = []
        # Collect all tokens inside {{ }} or {!! !!} as the expression string
        while self.current_token() and self.current_token().type != end_token_type:
            expr_parts.append(self.current_token().value)
            self.advance()
        expression = "".join(expr_parts).strip()

        if escaped:
            self.expect("VAR_END")
        else:
            self.expect("UNESCAPED_VAR_END")

        return VarNode(
            expression,
            escaped=escaped,
            line=start_token.line,
            column=start_token.column,
        )

    def _parse_if(self, condition_str, token):
        """Parses an @if...[@elif...]@else...@endif block."""
        # condition_str should be like "(user.is_admin)"
        condition = self._extract_expression_from_args(condition_str, "@if")

        body_nodes = []
        elif_blocks = []
        else_body_nodes = None

        # Parse the main @if block's content
        body_nodes = self._parse_until_directives(["@elif", "@else", "@endif"])

        while self.current_token() and self.current_token().type == "DIRECTIVE":
            directive_token = self.current_token()
            directive_full_str = directive_token.value
            match = re.match(r"@([a-zA-Z_][a-zA-Z0-9_]*)(.*)", directive_full_str)
            current_directive_name = match.group(1) if match else ""
            directive_args_str = match.group(2).strip() if match else ""

            if current_directive_name == "elif":
                self.advance()  # Consume @elif directive token
                elif_condition = self._extract_expression_from_args(directive_args_str, "@elif")
                elif_body = self._parse_until_directives(["@elif", "@else", "@endif"])
                elif_blocks.append((elif_condition, elif_body))
            elif current_directive_name == "else":
                self.advance()  # Consume @else directive token
                if directive_args_str:  # @else should not have arguments
                    raise DirectiveParsingError(
                        "Directive '@else' should not have arguments.",
                        line=directive_token.line,
                        column=directive_token.column,
                    )

                else_body_nodes = self._parse_until_directives(["@endif"])
            elif current_directive_name == "endif":
                break  # Found @endif, exit loop to consume it
            else:
                raise DirectiveParsingError(
                    f"Unexpected directive '@{current_directive_name}' inside @if block.",
                    line=directive_token.line,
                    column=directive_token.column,
                )

        self.expect("DIRECTIVE", value_prefix="@endif")  # Expect and consume the closing @endif

        return IfNode(
            condition,
            body_nodes,
            elif_blocks,
            else_body_nodes,
            line=directive_token.line,
            column=directive_token.column,
        )

    def _parse_for(self, loop_expression_str, token):
        """Parses an @for...[@empty...]@endfor block."""
        # loop_expression_str should be like "(item in collection)"
        match = re.match(r"^\s*\(\s*([a-zA-Z_][a-zA-Z0-9_]*)\s+in\s+(.+?)\s*\)\s*$", loop_expression_str)
        if not match:
            raise DirectiveParsingError(
                f"Invalid @for loop syntax: '@for{loop_expression_str}'. Expected '@for(item in itterable)'.",
                line=self.current_token().line,
                column=self.current_token().column,
            )

        item_var = match.group(1)  # e.g., 'fruit'
        collection_expr = match.group(2).strip()  # e.g., 'fruits'

        body_nodes = []
        empty_body_nodes = None

        # Parse the main @for loop's content
        body_nodes = self._parse_until_directives(["@empty", "@endfor"])

        if self.current_token() and self.current_token().type == "DIRECTIVE":
            directive_token = self.current_token()
            directive_name = re.match(r"@([a-zA-Z_][a-zA-Z0-9_]*).*", directive_token.value).group(1)

            if directive_name == "empty":
                self.advance()  # Consume @empty directive token
                if re.match(r"@empty\s*\(.*\)", directive_token.value):  # @empty should not have arguments
                    raise DirectiveParsingError(
                        "Directive '@empty' should not have arguments.",
                        line=directive_token.line,
                        column=directive_token.column,
                    )
                empty_body_nodes = self._parse_until_directives(["@endfor"])

        self.expect("DIRECTIVE", value_prefix="@endfor")  # Expect and consume the closing @endfor

        return ForNode(
            item_var,
            collection_expr,
            body_nodes,
            empty_body_nodes,
            line=token.line,
            column=token.column,
        )

    def _parse_until_directives(self, directives_to_stop_at):
        """
        Parses nodes within a block until one of the specified directives is encountered.
        This is used for parsing content of @if, @else, @for blocks.
        """
        body = []
        while self.current_token():
            token = self.current_token()

            if token.type == "DIRECTIVE":
                name, args = self._split_directive(token)

                if f"@{name}" in directives_to_stop_at:
                    return body  # Stop parsing this body, the directive belongs to the parent

                self.advance()  # Consume the DIRECTIVE token
                body.append(self._parse_directive(name, args, token))

            elif token.type == "TEXT":
                body.append(TextNode(token.value, line=token.line, column=token.column))
                self.advance()
            elif token.type == "VAR_START":
                body.append(self._parse_variable(escaped=True))
            elif token.type == "UNESCAPED_VAR_START":
                body.append(self._parse_variable(escaped=False))
            elif token.type == "PB_TAG_START":
                body.append(self._parse_pb_component(token, paired=True))
            elif token.type == "PB_TAG_SELF_CLOSE":
                body.append(self._parse_pb_component(token, paired=False))
            # TODO: Properly handle this case for inline comments
            # elif token.type == "COMMENT_START" or token.type == "COMMENT_END":
            #     self.advance()
            else:
                raise TemplateRenderError(
                    "Unexpected token type in _parse_until_directives: ", line=token.line, column=token.column
                )

        # If we reach here, we hit end of file without finding a closing directive.
        raise TemplateRenderError(
            f"Expected one of {directives_to_stop_at} but reached end of template without closure.",
            line=token.line,
            column=token.column,
            help="You opened a directive but did not close it. Add the corresponding closing directive.",
        )

    def _parse_unless(self, condition_str, token):
        """Parses an @unless...@endunless block."""
        condition = self._extract_expression_from_args(condition_str, "@unless")
        body_nodes = self._parse_until_directives(["@endunless"])
        self.expect("DIRECTIVE", value_prefix="@endunless")
        return UnlessNode(condition, body_nodes, line=token.line, column=token.column)

    def _parse_switch(self, expression_str, token, directive_name="match"):
        """Parses an @match...@endmatch or @switch...@endswitch block."""
        expression = self._extract_expression_from_args(expression_str, f"@{directive_name}")
        cases = []
        default_body = None
        end_directive = f"@end{directive_name}"

        while self.current_token():
            token = self.current_token()
            if token.type == "DIRECTIVE":
                match = re.match(r"@([a-zA-Z_][a-zA-Z0-9_]*)(.*)", token.value)
                dir_name = match.group(1)
                args_str = match.group(2).strip()

                if dir_name == "case":
                    self.advance()
                    case_value = self._extract_expression_from_args(args_str, "@case")
                    case_body = self._parse_until_directives(["@case", "@default", end_directive])
                    cases.append((case_value, case_body))
                elif dir_name == "default":
                    self.advance()
                    default_body = self._parse_until_directives([end_directive])
                elif dir_name == f"end{directive_name}":
                    break
                else:
                    # Ignore other directives or text between cases (usually whitespace)
                    # But if it's significant content, it might be an issue.
                    self.advance()
            else:
                # Ignore text/variables between cases (whitespace)
                self.advance()

        self.expect("DIRECTIVE", value_prefix=end_directive)
        return SwitchNode(expression, cases, default_body, line=token.line, column=token.column)

    def _parse_auth(self, args_str, token):
        """Parses an @auth...@endauth block."""
        guard = None
        if args_str:
            guard = self._extract_expression_from_args(args_str, "@auth")

        body = self._parse_until_directives(["@else", "@endauth"])
        else_body = None

        if self.current_token() and self.current_token().value.startswith("@else"):
            self.advance()
            else_body = self._parse_until_directives(["@endauth"])

        self.expect("DIRECTIVE", value_prefix="@endauth")
        return AuthNode(body, else_body, guard, line=token.line, column=token.column)

    def _parse_guest(self, args_str, token):
        """Parses an @guest...@endguest block."""
        guard = None
        if args_str:
            guard = self._extract_expression_from_args(args_str, "@guest")

        body = self._parse_until_directives(["@else", "@endguest"])
        else_body = None

        if self.current_token() and self.current_token().value.startswith("@else"):
            self.advance()
            else_body = self._parse_until_directives(["@endguest"])

        self.expect("DIRECTIVE", value_prefix="@endguest")
        return GuestNode(body, else_body, guard, line=token.line, column=token.column)

    def _parse_function_args(self, args_str):
        """Parses function-like arguments like ('path', {'data': value}) into path and data expressions.

        Returns a tuple of (path_expr, data_expr) where data_expr may be None.
        """
        # Remove parentheses and parse the function-like arguments
        match = re.match(r"^\s*\((.*)\)\s*$", args_str, re.DOTALL)
        if match:
            inner_args = match.group(1).strip()

            # Use a more sophisticated approach to handle nested structures
            # Find the first argument (path) and the rest (data)
            path_expr = None
            data_expr = None

            # Track bracket/brace nesting to properly split arguments
            bracket_count = 0
            brace_count = 0
            quote_char = None
            current_arg = ""

            for char in inner_args:
                if quote_char:
                    current_arg += char
                    if char == quote_char:
                        quote_char = None
                elif char in ('"', "'"):
                    quote_char = char
                    current_arg += char
                elif char in ("[", "("):
                    bracket_count += 1
                    current_arg += char
                elif char in ("]", ")"):
                    bracket_count -= 1
                    current_arg += char
                elif char == "{":
                    brace_count += 1
                    current_arg += char
                elif char == "}":
                    brace_count -= 1
                    current_arg += char
                elif char == "," and bracket_count == 0 and brace_count == 0:
                    # Found an argument boundary
                    if path_expr is None:
                        path_expr = current_arg.strip()
                    else:
                        data_expr = current_arg.strip()
                    current_arg = ""
                else:
                    current_arg += char

            # Add the last argument
            if current_arg.strip():
                if path_expr is None:
                    path_expr = current_arg.strip()
                else:
                    data_expr = current_arg.strip()

            return path_expr, data_expr
        else:
            # No parentheses - treat as single path argument
            return args_str.strip(), None

    def _parse_include(self, args_str, token):
        """Parses an @include('path') or @include('path', {'data': value}) directive."""
        path_expr, data_expr = self._parse_function_args(args_str)

        if not path_expr:
            raise DirectiveParsingError(
                "@include requires at least a path argument",
                line=token.line,
                column=token.column,
            )
        return IncludeNode(path_expr, data_expr, line=token.line, column=token.column)

    def _parse_extends(self, args_str, token):
        """Parses an @extends('layout') directive."""
        layout = self._extract_expression_from_args(args_str, "@extends")
        return ExtendsNode(layout, line=token.line, column=token.column)

    def _parse_section(self, args_str, token):
        """Parses an @section('name')...@endsection block."""
        name = self._extract_expression_from_args(args_str, "@section")
        body = self._parse_until_directives(["@endsection"])
        self.expect("DIRECTIVE", value_prefix="@endsection")
        return SectionNode(name, body, line=token.line, column=token.column)

    def _parse_yield(self, args_str, token):
        """Parses an @yield('name', default) directive."""
        # Parse arguments like @yield('content', 'Default content')
        name_expr, default_expr = self._parse_function_args(args_str)
        return YieldNode(name_expr, default_expr, line=token.line, column=token.column)

    def _parse_component(self, args_str, token):
        """Parses an @component('name', data)...@endcomponent block."""
        # args_str could be "('alert', {'type': 'error'})"
        path_expr, data_expr = self._parse_function_args(args_str)
        if not path_expr:
            raise DirectiveParsingError(
                "@compoent requires at least a path argument",
                line=token.line,
                column=token.column,
            )
        return ComponentNode(path_expr, data_expr, line=token.line, column=token.column)

    def _parse_slot(self, args_str, token):
        """Parses an @slot('name')...@endslot block.

        The name is optional: @slot...@endslot fills the default slot.
        """
        name = self._extract_expression_from_args(args_str, "@slot") if args_str.strip() else None
        body = self._parse_until_directives(["@endslot"])
        self.expect("DIRECTIVE", value_prefix="@endslot")
        return SlotNode(name, body, line=token.line, column=token.column)

    def _parse_props(self, args_str, token):
        """Parses an @props({...}) directive."""
        expression = self._extract_expression_from_args(args_str, "@props")
        return PropsNode(expression, line=token.line, column=token.column)

    def _parse_verbatim(self, args_str, token=None):
        """Parses an @verbatim...@endverbatim block."""
        # Verbatim content should be treated as raw text, not parsed.
        # But the lexer has already tokenized it.
        # We need to reconstruct the text from tokens until @endverbatim.
        # This is tricky because tokens are already split.
        # A better approach for verbatim is usually in Lexer, but here we are in Parser.
        # We will just consume tokens until we find @endverbatim directive.
        content_parts = []
        while self.current_token():
            token = self.current_token()
            if token.type == "DIRECTIVE" and token.value == "@endverbatim":
                break
            content_parts.append(token.value)
            self.advance()

        self.expect("DIRECTIVE", value_prefix="@endverbatim")
        return VerbatimNode("".join(content_parts))

    def _parse_comment(self, args_str, token=None):
        """Parses an @comment...@endcomment block."""
        # Just consume until endcomment
        content_parts = []
        comment_line = token.line if token else None
        comment_column = token.column if token else None
        while self.current_token():
            token = self.current_token()
            if token.type == "DIRECTIVE" and token.value == "@endcomment":
                break
            content_parts.append(token.value)
            self.advance()

        self.expect("DIRECTIVE", value_prefix="@endcomment")
        return CommentNode("".join(content_parts), line=comment_line, column=comment_column)

    def _parse_trans(self, args_str, token=None):
        """Parses an @trans('message') or @trans('message' as var) directive."""
        # Remove parentheses and parse arguments
        match = re.match(r"^\s*\((.*)\)\s*$", args_str)
        if match:
            inner_args = match.group(1).strip()
        else:
            inner_args = args_str.strip()

        # Parse arguments
        message = None
        context = None
        noop = False
        as_name = None

        # Check if there's an 'as' clause at the end
        if " as " in inner_args:
            # Split on ' as ' to separate the message from the variable name
            parts = inner_args.split(" as ", 1)
            inner_args = parts[0].strip()
            as_name = parts[1].strip()

        # Parse the remaining arguments
        # Split by commas to get individual arguments
        arg_parts = [arg.strip() for arg in inner_args.split(",") if arg.strip()]

        for i, arg in enumerate(arg_parts):
            # Check for keyword arguments
            if "=" in arg:
                key, value = arg.split("=", 1)
                key = key.strip()
                value = value.strip()

                if key == "context":
                    # Remove quotes if present
                    if (value.startswith("'") and value.endswith("'")) or (
                        value.startswith('"') and value.endswith('"')
                    ):
                        value = value[1:-1]
                    context = value
                elif key == "noop":
                    noop = value.lower() in ("true", "1")
            else:
                # This is the message (first positional argument)
                if message is None:
                    message = arg
                    # Remove quotes if present
                    if (message.startswith("'") and message.endswith("'")) or (
                        message.startswith('"') and message.endswith('"')
                    ):
                        message = message[1:-1]

        return TranslateNode(
            message,
            context=context,
            noop=noop,
            as_name=as_name,
            line=token.line if token else None,
            column=token.column if token else None,
        )

    def _parse_blocktranslate(self, args_str, token=None):
        """Parses an @blocktranslate...@endblocktranslate block."""

        # Parse parameters from args_str
        count = None
        context = None
        trimmed = False
        kwargs = {}

        if args_str.strip():
            match = re.match(r"^\s*\((.*)\)\s*$", args_str)
            if match:
                inner_args = match.group(1).strip()
            else:
                inner_args = args_str.strip()

            # Parse keyword arguments
            # Split by commas to get individual key=value pairs
            arg_pairs = [arg.strip() for arg in inner_args.split(",") if arg.strip()]

            for arg_pair in arg_pairs:
                # Check for special keywords
                if arg_pair == "trimmed":
                    trimmed = True
                    continue

                # Try to parse as key=value
                if "=" in arg_pair:
                    key, value = arg_pair.split("=", 1)
                    key = key.strip()
                    value = value.strip()

                    # Handle special keywords
                    if key == "trimmed":
                        trimmed = value.strip().lower() in ("true", "1")
                    elif key == "count":
                        count = value
                    elif key == "context":
                        # Remove quotes if present
                        if (value.startswith("'") and value.endswith("'")) or (
                            value.startswith('"') and value.endswith('"')
                        ):
                            value = value[1:-1]
                        context = value
                    else:
                        # Store as general kwargs
                        kwargs[key] = value

        # Parse until @plural or @endblocktranslate
        # Only allow text, variables, and @plural directive in blocktranslate body
        body = self._parse_blocktranslate_body(["@plural", "@endblocktranslate"])
        plural_body = None

        if self.current_token() and self.current_token().value == "@plural":
            self.advance()  # Consume @plural
            plural_body = self._parse_blocktranslate_body(["@endblocktranslate"])

        self.expect("DIRECTIVE", value_prefix="@endblocktranslate")

        return BlockTranslateNode(
            body,
            plural_body=plural_body,
            count=count,
            context=context,
            trimmed=trimmed,
            kwargs=kwargs,
            line=token.line if token else None,
            column=token.column if token else None,
        )

    def _parse_blocktranslate_body(self, directives_to_stop_at):
        """
        Parses nodes within a blocktranslate body.
        Only allows text, variables, and the @plural directive.
        Other directives are not allowed in blocktranslate bodies.
        """
        body = []
        while self.current_token():
            token = self.current_token()

            if token.type == "DIRECTIVE":
                directive_name_match = re.match(r"@([a-zA-Z_][a-zA-Z0-9_]*).*", token.value)
                if directive_name_match:
                    full_directive_name = f"@{directive_name_match.group(1)}"
                    if full_directive_name in directives_to_stop_at:
                        return body  # Stop parsing this body, the directive will be handled by the parent

                # Only allow @plural directive in blocktranslate body
                directive_full_str = token.value
                match = re.match(r"@([a-zA-Z_][a-zA-Z0-9_]*)(.*)", directive_full_str)
                directive_name = match.group(1) if match else ""

                if directive_name == "plural":
                    # This should be caught by directives_to_stop_at, but handle it here for safety
                    return body
                else:
                    raise TemplateRenderError(
                        f"Only @plural directive is allowed inside @blocktranslate, found @{directive_name}",
                        line=token.line,
                        column=token.column,
                    )

            elif token.type == "TEXT":
                body.append(TextNode(token.value, line=token.line, column=token.column))
                self.advance()
            elif token.type == "VAR_START":
                body.append(self._parse_variable(escaped=True))
            elif token.type == "UNESCAPED_VAR_START":
                body.append(self._parse_variable(escaped=False))
            else:
                raise TemplateRenderError(
                    f"Unexpected token type in @blocktranslate body: {token.type}", line=token.line, column=token.column
                )

        # If we reach here, we hit end of file without finding a closing directive.
        raise TemplateRenderError(
            f"Expected one of {directives_to_stop_at} but reached end of template without closure.",
            line=token.line if token else None,
            column=token.column if token else None,
        )

    def _parse_now(self, args_str, token):
        match = re.match(r"^\s*\((.*)\)\s*$", args_str)
        if match:
            inner_args = match.group(1).strip()
        else:
            inner_args = args_str.strip()

        if " as " in inner_args:
            fmt_str, var_name = inner_args.split(" as ", 1)
            fmt_str = fmt_str.strip()
            var_name = var_name.strip()
            return NowNode(fmt_str, as_name=var_name, line=token.line, column=token.column)
        else:
            return NowNode(inner_args, line=token.line, column=token.column)

    def _parse_with(self, args_str, token=None):
        """Parses an @with(variable=expression)...@endwith block."""
        # Extract the variable assignment expression
        variables_str = self._extract_expression_from_args(args_str, "@with")

        # Parse variables into a dictionary for better performance
        variables_dict = {}
        if variables_str.strip():
            # Remove parentheses if present
            vars_str = variables_str.strip()
            if vars_str.startswith("(") and vars_str.endswith(")"):
                vars_str = vars_str[1:-1]

            # Parse variable assignments
            parts = [part.strip() for part in vars_str.split(",") if part.strip()]
            for part in parts:
                if "=" in part:
                    var_name, var_expr = part.split("=", 1)
                    var_name = var_name.strip()
                    var_expr = var_expr.strip()
                    variables_dict[var_name] = var_expr

        body = self._parse_until_directives(["@endwith"])
        self.expect("DIRECTIVE", value_prefix="@endwith")
        return WithNode(variables_dict, body, line=token.line, column=token.column)

    def _parse_regroup(self, args_str, token):
        match = re.match(r"^\s*\((.*)\)\s*$", args_str)
        inner = match.group(1).strip() if match else args_str.strip()
        m = re.match(r"(.*?)\s+by\s+(.*?)\s+as\s+(.*)", inner)
        if m:
            return RegroupNode(
                m.group(1).strip(), m.group(2).strip(), m.group(3).strip(), line=token.line, column=token.column
            )
        return RegroupNode(inner, None, None, line=token.line, column=token.column)

    def _parse_autoescape(self, args_str, token=None):
        """Parses an @autoescape(True/False)...@endautoescape block.

        The argument is expected to be a boolean expression inside
        parentheses, e.g. "(True)" or "(False)".
        """
        enabled_expr = self._extract_expression_from_args(args_str, "@autoescape")
        # We store the expression string; AutoescapeNode will evaluate it.
        body = self._parse_until_directives(["@endautoescape"])
        self.expect("DIRECTIVE", value_prefix="@endautoescape")
        # Let the node evaluate enabled_expr via SafeEvaluator at render time.
        return AutoescapeNode(enabled_expr, body)

    def _parse_lorem(self, args_str, token=None):
        """Parses a @lorem(...) directive."""
        # We pass the raw args (without surrounding parentheses stripping here).
        # LoremNode will handle evaluation.
        inner = ""
        if args_str:
            match = re.match(r"^\s*\((.*)\)\s*$", args_str)
            if match:
                inner = match.group(1).strip()
        return LoremNode(inner, line=token.line if token else None, column=token.column if token else None)

    def _parse_spaceless(self, args_str, token=None):
        """Parses a @spaceless...@endspaceless block."""
        # Arguments are not expected; ignore if present.
        body = self._parse_until_directives(["@endspaceless"])
        self.expect("DIRECTIVE", value_prefix="@endspaceless")
        return SpacelessNode(body)

    def _parse_attribute(self, name, args_str, token):
        """Parses a directive rendering an HTML attribute, such as @checked or @disabled(condition).

        The condition is optional: written on its own, the directive always renders
        its attribute.
        """
        condition = self._extract_expression_from_args(args_str, f"@{name}") if args_str.strip() else None

        return AttributeNode(name, condition or None, line=token.line, column=token.column)

    def _parse_field(self, args_str, token):
        """Parses an @field(form.field, attributes...) directive.

        The first argument is the form field, the rest are the HTML attributes to
        render it with, written as in a tag:

            @field(form.name, class="form-control" placeholder="Your name" required)
        """
        inner = self._extract_expression_from_args(args_str, "@field")
        field_expr, _, attrs_str = inner.partition(",")

        if not field_expr.strip():
            raise DirectiveParsingError(
                "@field requires at least a field expression",
                line=token.line,
                column=token.column,
                help="Pass the field to render, as in @field(form.name).",
            )

        return FieldNode(
            field_expr.strip(),
            self._parse_attributes(attrs_str, token),
            line=token.line,
            column=token.column,
        )

    def _parse_error(self, args_str, token):
        """Parses an @error(form.field)...@enderror block."""
        field_expr = self._extract_expression_from_args(args_str, "@error")
        body = self._parse_until_directives(["@enderror"])
        self.expect("DIRECTIVE", value_prefix="@enderror")
        return ErrorNode(field_expr, body, line=token.line, column=token.column)

    _pb_tag_name_pattern = re.compile(r"</?pb-([a-zA-Z0-9_.:-]+)")

    _attribute_pattern = re.compile(
        r"(?P<bind>:)?"  # Binding the value as an expression, as in :count="1 + 1"
        r"(?P<name>[a-zA-Z_][a-zA-Z0-9_.:-]*)"  # Attribute name
        r"(?P<append>\+)?"  # Appending to the value already there, as in class+="..."
        r"(?:\s*=\s*(?:"  # Its value is optional
        r'"(?P<double>[^"]*)"'  # Double quoted, a string
        r"|'(?P<single>[^']*)'"  # Single quoted, a string too
        r"|(?P<unquoted>[^\s,>]+)"  # Unquoted, an expression
        r"))?"
    )

    def _parse_pb_component(self, token, paired=True):
        """Parses an HTML-like pb- tag into a ComponentNode or, for pb-slot, a SlotNode.

        Examples:
            <pb-alert type="error">Error message</pb-alert>
            <pb-button label="Click me" />
            <pb-ui.card title="Samsung">Card slot</pb-ui.card>
            <pb-slot:title>My title</pb-slot:title>
        """
        tag_value = token.value
        self.advance()  # Consume the PB_TAG_START or PB_TAG_SELF_CLOSE token

        tag_name = self._pb_tag_name(tag_value)
        if not tag_name:
            raise DirectiveParsingError(
                f"Invalid pb- tag format: {tag_value}",
                line=token.line,
                column=token.column,
            )

        attributes = self._parse_pb_attributes(tag_value, token)

        # The content of a paired tag is parsed, so that the component is handed
        # template nodes rather than text it would have to parse again.
        body = self._parse_pb_body(tag_name, token) if paired else []

        # <pb-slot name="title"> and <pb-slot:title> are the tag forms of @slot('title')
        if tag_name == "slot" or tag_name.startswith("slot:"):
            return self._make_pb_slot(tag_name, attributes, body, token)

        return ComponentNode(
            f'"{tag_name}"',
            attributes=attributes,
            slots=split_slots(body),
            line=token.line,
            column=token.column,
        )

    def _pb_tag_name(self, tag_value):
        """Extracts the name of a pb- tag, without its 'pb-' prefix."""
        match = self._pb_tag_name_pattern.match(tag_value)
        return match.group(1) if match else None

    def _parse_pb_body(self, tag_name, token):
        """Parses the content of a paired pb- tag, up to its matching closing tag.

        Tags of the same name may be nested, so the depth is tracked. The
        <pb-slot:title> shorthand accepts both </pb-slot:title> and </pb-slot>
        as its closing tag.
        """
        base_name = tag_name.split(":")[0]
        depth = 1
        parts = []
        start = None

        while self.current_token():
            current = self.current_token()

            if current.type == "PB_TAG_START" and self._pb_tag_name(current.value).split(":")[0] == base_name:
                depth += 1
            elif current.type == "PB_TAG_END" and self._pb_tag_name(current.value) in (tag_name, base_name):
                depth -= 1
                if depth == 0:
                    self.advance()  # Consume the closing tag
                    break

            start = start or current
            parts.append(current.value)
            self.advance()
        else:
            raise DirectiveParsingError(
                f"Unclosed <pb-{tag_name}> tag.",
                line=token.line,
                column=token.column,
                help=f"Close the tag with </pb-{tag_name}> or make it self-closing with '/>'.",
            )

        if not parts:
            return []

        # The content is tokenized again, from the position it was found at so that
        # what it holds keeps reporting the line it is written on.
        return Parser(Lexer("".join(parts), line=start.line, column=start.column).tokenize()).parse()

    def _make_pb_slot(self, tag_name, attributes, body, token):
        """Builds a SlotNode out of a <pb-slot name="..."> or <pb-slot:name> tag."""
        if ":" in tag_name:
            name = f'"{tag_name.split(":", 1)[1]}"'
        else:
            # Left out on <pb-slot>, which then fills the default slot
            name = attributes.get("name")

        return SlotNode(name, body, line=token.line, column=token.column)

    def _parse_pb_attributes(self, tag_value, token=None):
        """Parse attributes from a pb- tag string.

        Quoted values are strings, unquoted ones are expressions evaluated in the
        context of the caller, an attribute without a value is True, and a name
        prefixed with ':' has its value read as an expression.

        Example: <pb-alert type="error" :count="total + 1" dismissible>
        Returns: {'type': "'error'", 'count': 'total + 1', 'dismissible': 'True'}
        """
        attributes = {}

        # Remove the opening tag part
        match = re.match(r"<pb-[a-zA-Z0-9_.:-]+\s*(.*)>", tag_value, re.DOTALL)
        if not match:
            return attributes

        return self._parse_attributes(match.group(1).strip().rstrip("/"), token)

    def _parse_attributes(self, attrs_str, token=None):
        """Parses a list of HTML-like attributes into a name to expression mapping.

        Quoted values are strings, unquoted ones are expressions evaluated where the
        attribute is written, and an attribute with no value is True. A name ending
        with '+' appends to the value the attribute already holds. A name prefixed
        with ':' binds its value, which is then read as an expression even quoted,
        so that a component may be passed something other than a string.

        Example: type="error" :count="1 + 1" dismissible class+="mt-2"
        Returns: {'type': "'error'", 'count': '1 + 1', 'dismissible': 'True', 'class+': "'mt-2'"}
        """
        attributes = {}

        # Attributes are matched in a single pass, so that what is inside a quoted
        # value is never mistaken for an attribute of its own.
        for attribute in self._attribute_pattern.finditer(attrs_str.strip()):
            name = attribute.group("name") + (attribute.group("append") or "")
            double_quoted, single_quoted, unquoted = attribute.group("double", "single", "unquoted")

            if attribute.group("bind"):
                value = double_quoted if double_quoted is not None else single_quoted
                value = value if value is not None else unquoted

                if value is None or not value.strip():
                    raise DirectiveParsingError(
                        f"The bound attribute ':{attribute.group('name')}' has no value.",
                        line=getattr(token, "line", None),
                        column=getattr(token, "column", None),
                        help='Give it the expression to evaluate, as in :count="1 + 1", '
                        f"or drop the colon to pass the name on its own.",
                    )

                # Quoted or not, a bound value is the expression it holds
                attributes[name] = value

            elif double_quoted is not None:
                attributes[name] = repr(double_quoted)
            elif single_quoted is not None:
                attributes[name] = repr(single_quoted)
            elif unquoted is not None:
                attributes[name] = unquoted
            else:
                # An attribute with no value at all, as the 'disabled' of <pb-button disabled />
                attributes[name] = "True"

        return attributes

    def _parse_autocomplete(self, args_str, token):
        value = self._extract_expression_from_args(args_str, "@autocomplete")
        return AutocompleteNode(value, line=token.line, column=token.column)

    def _parse_ratio(self, args_str, token):
        """Parse @ratio(value, max_value, max_width) or @ratio(value, max_value, max_width as variable_name)"""
        args = self._extract_expression_from_args(args_str)

        # Check if there's an 'as' clause
        if " as " in args:
            # Split on ' as ' to separate the ratio arguments from the variable name
            ratio_args, var_name = args.split(" as ", 1)
            ratio_args = ratio_args.strip()
            var_name = var_name.strip()
            return RatioNode(ratio_args, var_name, line=token.line, column=token.column)
        else:
            return RatioNode(args, None, line=token.line, column=token.column)

    def _parse_querystring(self, args_str, token):
        """Parse @querystring(kwargs) or @querystring(kwargs as variable_name)"""
        match = re.match(r"^\s*\((.*)\)\s*$", args_str)
        inner = match.group(1).strip() if match else args_str.strip()

        # Check if there's an 'as' clause
        if " as " in inner:
            # Split on ' as ' to separate the querystring arguments from the variable name
            kwargs_str, as_name = inner.split(" as ", 1)
            kwargs_str = kwargs_str.strip()
            as_name = as_name.strip()
        else:
            kwargs_str = inner
            as_name = None

        return QuerystringNode(kwargs_str, as_name, line=token.line, column=token.column)

    def _parse_block(self, args_str, token):
        """Parses an @block('name')...@endblock block."""
        name = self._extract_expression_from_args(args_str, "@block")
        body = self._parse_until_directives(["@endblock"])
        self.expect("DIRECTIVE", value_prefix="@endblock")
        return BlockNode(name, body, line=token.line, column=token.column)

    def _parse_cycle(self, args_str, token):
        """Parse @cycle('value1', 'value2', ...) or @cycle('value1', 'value2' as variable_name)"""
        # Remove parentheses and parse arguments
        match = re.match(r"^\s*\((.*)\)\s*$", args_str)
        if match:
            inner_args = match.group(1).strip()
        else:
            inner_args = args_str.strip()

        silent = False
        if inner_args.endswith(" silent"):
            silent = True
            inner_args = inner_args[:-7].strip()

        # Check if there's an 'as' clause
        if " as " in inner_args:
            # Split on ' as ' to separate the cycle values from the variable name
            values_str, var_name = inner_args.split(" as ", 1)
            values_str = values_str.strip()
            var_name = var_name.strip()
            return CycleNode(values_str, var_name, silent=silent, line=token.line, column=token.column)
        else:
            return CycleNode(inner_args, None, silent=silent, line=token.line, column=token.column)

    def _parse_resetcycle(self, args_str, token):
        name = self._extract_expression_from_args(args_str, "@resetcycle")
        return ResetCycleNode(name, line=token.line, column=token.column)

    def _parse_firstof(self, args_str, token=None):
        match = re.match(r"^\s*\((.*)\)\s*$", args_str)
        if match:
            inner_args = match.group(1).strip()
        else:
            inner_args = args_str.strip()

        if " as " in inner_args:
            values_str, var_name = inner_args.split(" as ", 1)
            values_str = values_str.strip()
            var_name = var_name.strip()
            return FirstOfNode(
                values_str, as_name=var_name, line=token.line if token else None, column=token.column if token else None
            )
        else:
            return FirstOfNode(inner_args, line=token.line if token else None, column=token.column if token else None)

    def _parse_url(self, args_str, token):
        """Parse @url('pattern', args, kwargs) or @url('pattern', args, kwargs as variable_name)"""
        # Remove parentheses and parse the function-like arguments
        match = re.match(r"^\s*\((.*)\)\s*$", args_str)
        if match:
            inner_args = match.group(1).strip()
        else:
            inner_args = args_str.strip()

        # Check if there's an 'as' clause
        if " as " in inner_args:
            # Split on ' as ' to separate the url arguments from the variable name
            url_args_str, as_name = inner_args.split(" as ", 1)
            url_args_str = url_args_str.strip()
            as_name = as_name.strip()
        else:
            url_args_str = inner_args
            as_name = None

        # Parse the URL arguments (pattern and parameters)
        if not url_args_str:
            raise DirectiveParsingError(
                "The @url directive requires at least one argument.",
                line=token.line,
                column=token.column,
                help="Provide at least the URL name as the first argument of the @url directive. \
                    This can be either a st",
            )

        # Use the same sophisticated parsing as @include to handle nested structures
        pattern_expr = None
        positional_args = []
        keyword_args = {}

        # Track bracket/brace nesting to properly split arguments
        bracket_count = 0
        brace_count = 0
        quote_char = None
        current_arg = ""

        for char in url_args_str:
            if quote_char:
                current_arg += char
                if char == quote_char:
                    quote_char = None
            elif char in ('"', "'"):
                quote_char = char
                current_arg += char
            elif char in ("[", "("):
                bracket_count += 1
                current_arg += char
            elif char in ("]", ")"):
                bracket_count -= 1
                current_arg += char
            elif char == "{":
                brace_count += 1
                current_arg += char
            elif char == "}":
                brace_count -= 1
                current_arg += char
            elif char == "," and bracket_count == 0 and brace_count == 0:
                # Found an argument boundary
                if pattern_expr is None:
                    pattern_expr = current_arg.strip()
                elif "=" in current_arg:
                    # Keyword argument
                    key_part, value_expr = current_arg.split("=", 1)
                    key = key_part.strip()
                    value = value_expr.strip()
                    keyword_args[key] = value
                else:
                    # Positional argument
                    positional_args.append(current_arg.strip())
                current_arg = ""
            else:
                current_arg += char

        # Add the last argument
        if current_arg.strip():
            if pattern_expr is None:
                pattern_expr = current_arg.strip()
            elif "=" in current_arg:
                # Keyword argument
                key_part, value_expr = current_arg.split("=", 1)
                key = key_part.strip()
                value = value_expr.strip()
                keyword_args[key] = value
            else:
                # Positional argument
                positional_args.append(current_arg.strip())

        if positional_args and keyword_args:
            raise DirectiveParsingError(
                "@url does not support mixing positional and kayword arguments.",
                line=token.line,
                column=token.column,
                help="Provide either positional arguments or keyword arguments, not both.",
            )

        if not pattern_expr:
            raise DirectiveParsingError(
                "@url requires at least a URL pattern",
                line=token.line,
                column=token.column,
                help="Provide at least the URL name as the first argument of the @url directive.",
            )

        return UrlNode(pattern_expr, positional_args, keyword_args, as_name, line=token.line, column=token.column)

    def _parse_static(self, args_str, token):
        """Parse @static(path) or @static(path as variable_name)"""
        # Remove parentheses and parse arguments
        match = re.match(r"^\s*\((.*)\)\s*$", args_str)
        if match:
            inner_args = match.group(1).strip()
        else:
            inner_args = args_str.strip()

        # Check if there's an 'as' clause
        if " as " in inner_args:
            # Split on ' as ' to separate the path from the variable name
            path_part, as_name = inner_args.split(" as ", 1)
            path = path_part.strip()
            as_name = as_name.strip()
        else:
            path = inner_args
            as_name = None

        return StaticNode(path, as_name, line=token.line, column=token.column)

    def _parse_get_static_prefix(self, args_str, token):
        """Parse @get_static_prefix or @get_static_prefix(as variable_name)"""
        # Remove parentheses if present
        match = re.match(r"^\s*\((.*)\)\s*$", args_str)
        if match:
            inner_args = match.group(1).strip()
        else:
            inner_args = args_str.strip()

        # Check if there's an 'as' clause
        if inner_args.startswith("as "):
            as_name = inner_args[3:].strip()
            return GetStaticPrefixNode(as_name=as_name, line=token.line, column=token.column)
        else:
            return GetStaticPrefixNode(line=token.line, column=token.column)

    def _parse_get_media_prefix(self, args_str, token):
        """Parse @get_media_prefix or @get_media_prefix(as variable_name)"""
        # Remove parentheses if present
        match = re.match(r"^\s*\((.*)\)\s*$", args_str)
        if match:
            inner_args = match.group(1).strip()
        else:
            inner_args = args_str.strip()

        # Check if there's an 'as' clause
        if inner_args.startswith("as "):
            as_name = inner_args[3:].strip()
            return GetMediaPrefixNode(as_name=as_name, line=token.line, column=token.column)
        else:
            return GetMediaPrefixNode(line=token.line, column=token.column)

    def _parse_method(self, args_str, token=None):
        method = self._extract_expression_from_args(args_str, "@method")
        return MethodNode(method, line=token.line if token else None, column=token.column if token else None)

    def _parse_ifchanged(self, args_str, token):
        # args_str can be empty or "(var)"
        check_expr = None
        if args_str.strip():
            # if provided, must have parens
            check_expr = self._extract_expression_from_args(args_str, "@ifchanged")

        body = self._parse_until_directives(["@else", "@endifchanged"])
        else_body = None

        if self.current_token() and self.current_token().value.startswith("@else"):
            self.advance()
            else_body = self._parse_until_directives(["@endifchanged"])

        self.expect("DIRECTIVE", value_prefix="@endifchanged")
        return IfChangedNode(check_expr, body, else_body, line=token.line, column=token.column)

    def _parse_style(self, args_str, token):
        # Remove parentheses and parse the function-like arguments
        match = re.match(r"^\s*\((.*)\)\s*$", args_str)
        if match:
            inner_args = match.group(1).strip()
            positional, conditional = self._parse_args(inner_args)
        else:
            positional, conditional = self._parse_args(args_str.strip())

        return StyleNode(positional, conditional, line=token.line, column=token.column)

    def _parse_class(self, args_str, token):
        # Remove parentheses and parse the function-like arguments
        match = re.match(r"^\s*\((.*)\)\s*$", args_str)
        if match:
            inner_args = match.group(1).strip()
            positional, conditional = self._parse_args(inner_args)
        else:
            positional, conditional = self._parse_args(args_str.strip())

        return ClassNode(positional, conditional, line=token.line, column=token.column)

    def _parse_break(self, args_str, token):
        condition = None
        if args_str:
            condition = self._extract_expression_from_args(args_str, "@break")
        return BreakNode(condition, line=token.line, column=token.column)

    def _parse_continue(self, args_str, token):
        condition = None
        if args_str:
            condition = self._extract_expression_from_args(args_str, "@continue")
        return ContinueNode(condition, line=token.line, column=token.column)

    def _extract_expression_from_args(self, args_str, directive_name=""):
        """Extracts the Python expression string from directive arguments like '(expression)'.

        Arguments may span several lines, as a dictionary passed to @props usually does.
        """
        match = re.match(r"^\s*\((.*)\)\s*$", args_str, re.DOTALL)
        if not match:
            raise DirectiveParsingError(
                f"Invalid arguments for {directive_name}: '{args_str}'. "
                f"Expected parentheses, e.g., '({directive_name}(condition))'.",
            )
        return match.group(1).strip()

    def _parse_args(self, args_str, context=None):
        """Parse function-like arguments and return positional and conditional values.

        Args:
            args_str: String like '"list-item", "active", "favorite"=fruit.is_favorite'
            context: Template context for evaluating expressions (not used during parsing)

        Returns:
            tuple: (positional_list, conditional_dict)
        """

        positional = []
        conditional = {}

        # Split by commas and process each part
        parts = [part.strip() for part in args_str.split(",") if part.strip()]

        for part in parts:
            # Check if it's a keyword argument (has =)
            if "=" in part:
                # Split on the first = only
                key_part, value_expr = part.split("=", 1)
                key_part = key_part.strip()
                value_expr = value_expr.strip()

                # Key should be quoted - remove quotes
                if (key_part.startswith('"') and key_part.endswith('"')) or (
                    key_part.startswith("'") and key_part.endswith("'")
                ):
                    key = key_part[1:-1]
                    conditional[key] = value_expr

            else:
                # Positional argument - should be quoted
                if (part.startswith('"') and part.endswith('"')) or (part.startswith("'") and part.endswith("'")):
                    value = part[1:-1]
                    positional.append(value)

        return positional, conditional
