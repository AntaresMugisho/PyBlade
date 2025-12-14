import re

from pyblade.engine.exceptions import DirectiveParsingError, TemplateRenderError

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


class Parser:
    """
    Parses a stream of tokens from the Lexer to build an Abstract Syntax Tree (AST).
    It understands the structure of PyBlade directives and variable display.
    """

    def __init__(self, tokens):
        # Filter out comment tokens from the main stream, as they are ignored by the parser
        self.tokens = [t for t in tokens if t.type not in ("COMMENT_START", "COMMENT_END")]
        self.pos = 0  # Current position in the token list

    def current_token(self):
        """Returns the current token without advancing."""
        if self.pos < len(self.tokens):
            return self.tokens[self.pos]
        return None

    def advance(self):
        """Advances to the next token."""
        self.pos += 1
        return self.current_token()

    def expect(self, token_type, value_prefix=None):
        """
        Consumes the current token if it matches the expected type and (optional) value prefix.
        Raises SyntaxError if not matched.
        """
        token = self.current_token()
        if not token or token.type != token_type:
            raise TemplateRenderError(
                f"Expected token of type '{token_type}' but got {token}.",
                line=token.line,
                column=token.column,
            )
        if value_prefix and not token.value.startswith(value_prefix):
            raise TemplateRenderError(
                f"Expected token value starting with '{value_prefix}' but got '{token.value}'",
                line=token.line,
                column=token.column,
            )
        self.advance()
        return token

    def parse(self):
        """Starts the parsing process and returns the root AST nodes."""
        ast = []
        while self.current_token():
            token = self.current_token()
            if token.type == "TEXT":
                ast.append(TextNode(token.value))
                self.advance()
            elif token.type == "VAR_START":
                ast.append(self._parse_variable(escaped=True))
            elif token.type == "UNESCAPED_VAR_START":
                ast.append(self._parse_variable(escaped=False))
            elif token.type == "DIRECTIVE":
                directive_full_str = token.value

                # Extract directive name and its argument string from the full directive token value
                match = re.match(r"@([a-zA-Z_][a-zA-Z0-9_]*)(.*)", directive_full_str)
                if not match:
                    raise SyntaxError(
                        f"Invalid directive format: {directive_full_str} at line {token.line}, col {token.column}"
                    )

                directive_name = match.group(1)
                directive_args_str = match.group(2).strip()  # Will include parens if present

                self.advance()  # Consume the DIRECTIVE token

                if directive_name == "if":
                    ast.append(self._parse_if(directive_args_str))
                elif directive_name == "unless":
                    ast.append(self._parse_unless(directive_args_str))
                elif directive_name == "for":
                    ast.append(self._parse_for(directive_args_str))
                elif directive_name == "switch":
                    ast.append(self._parse_switch(directive_args_str))
                elif directive_name == "auth":
                    ast.append(self._parse_auth(directive_args_str))
                elif directive_name == "guest":
                    ast.append(self._parse_guest(directive_args_str))
                elif directive_name == "include":
                    ast.append(self._parse_include(directive_args_str))
                elif directive_name == "extends":
                    ast.append(self._parse_extends(directive_args_str))
                elif directive_name == "section":
                    ast.append(self._parse_section(directive_args_str))
                elif directive_name == "yield":
                    ast.append(self._parse_yield(directive_args_str))
                elif directive_name == "component":
                    ast.append(self._parse_component(directive_args_str))
                elif directive_name == "slot":
                    ast.append(self._parse_slot(directive_args_str))
                elif directive_name == "verbatim":
                    ast.append(self._parse_verbatim(directive_args_str))
                elif directive_name == "python":
                    ast.append(self._parse_python(directive_args_str))
                elif directive_name == "comment":
                    ast.append(self._parse_comment(directive_args_str))
                elif directive_name == "cycle":
                    ast.append(self._parse_cycle(directive_args_str))
                elif directive_name == "firstof":
                    ast.append(self._parse_firstof(directive_args_str))
                elif directive_name == "url":
                    ast.append(self._parse_url(directive_args_str))
                elif directive_name == "static":
                    ast.append(self._parse_static(directive_args_str))
                elif directive_name == "csrf":
                    ast.append(CsrfNode())
                elif directive_name == "method":
                    ast.append(self._parse_method(directive_args_str))
                elif directive_name == "style":
                    ast.append(self._parse_style(directive_args_str))
                elif directive_name == "class":
                    ast.append(self._parse_class(directive_args_str))
                elif directive_name == "break":
                    ast.append(self._parse_break(directive_args_str))
                elif directive_name == "continue":
                    ast.append(self._parse_continue(directive_args_str))
                elif directive_name in ["elif", "else", "endif", "empty", "endfor"]:
                    # These are control flow directives handled by their parent block parsers.
                    # # Encountering them at the top level or out of sequence is a syntax error.
                    raise DirectiveParsingError(
                        f"Unexpected directive '@{directive_name}' at top level or outside its block.",
                        line=token.line,
                        column=token.column,
                    )
            else:
                raise TemplateRenderError(
                    f"Unexpected token type: {token.type} with value '{token.value}'",
                    line=token.line,
                    column=token.column,
                )
        return ast

    def _parse_variable(self, escaped=True):
        """Parses a {{ expression }} or {!! expression !!} block."""
        if escaped:
            self.expect("VAR_START")
            end_token_type = "VAR_END"
        else:
            self.expect("UNESCAPED_VAR_START")
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

        return VarNode(expression, escaped=escaped)

    def _parse_if(self, condition_str):
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

        return IfNode(condition, body_nodes, elif_blocks, else_body_nodes)

    def _parse_for(self, loop_expression_str):
        """Parses an @for...[@empty...]@endfor block."""
        # loop_expression_str should be like "(item in collection)"
        match = re.match(r"^\s*\(\s*([a-zA-Z_][a-zA-Z0-9_]*)\s+in\s+(.+?)\s*\)\s*$", loop_expression_str)
        if not match:
            raise SyntaxError(f"Invalid @for loop syntax: '{loop_expression_str}'. Expected '(item in collection)'.")

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

        return ForNode(item_var, collection_expr, body_nodes, empty_body_nodes)

    def _parse_until_directives(self, directives_to_stop_at):
        """
        Parses nodes within a block until one of the specified directives is encountered.
        This is used for parsing content of @if, @else, @for blocks.
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
                # If it's a directive but not one to stop at, it must be a nested block.
                # (e.g., @if inside @for)
                directive_full_str = token.value
                match = re.match(r"@([a-zA-Z_][a-zA-Z0-9_]*)(.*)", directive_full_str)
                directive_name = match.group(1) if match else ""
                directive_args_str = match.group(2).strip() if match else ""

                self.advance()  # Consume the DIRECTIVE token

                if directive_name == "if":
                    body.append(self._parse_if(directive_args_str))
                elif directive_name == "unless":
                    body.append(self._parse_unless(directive_args_str))
                elif directive_name == "for":
                    body.append(self._parse_for(directive_args_str))
                elif directive_name == "switch":
                    body.append(self._parse_switch(directive_args_str))
                elif directive_name == "auth":
                    body.append(self._parse_auth(directive_args_str))
                elif directive_name == "guest":
                    body.append(self._parse_guest(directive_args_str))
                elif directive_name == "component":
                    body.append(self._parse_component(directive_args_str))
                elif directive_name == "slot":
                    body.append(self._parse_slot(directive_args_str))
                elif directive_name == "verbatim":
                    body.append(self._parse_verbatim(directive_args_str))
                elif directive_name == "python":
                    body.append(self._parse_python(directive_args_str))
                elif directive_name == "comment":
                    body.append(self._parse_comment(directive_args_str))
                elif directive_name == "include":
                    body.append(self._parse_include(directive_args_str))
                elif directive_name == "cycle":
                    body.append(self._parse_cycle(directive_args_str))
                elif directive_name == "firstof":
                    body.append(self._parse_firstof(directive_args_str))
                elif directive_name == "url":
                    body.append(self._parse_url(directive_args_str))
                elif directive_name == "static":
                    body.append(self._parse_static(directive_args_str))
                elif directive_name == "csrf":
                    body.append(CsrfNode())
                elif directive_name == "method":
                    body.append(self._parse_method(directive_args_str))
                elif directive_name == "style":
                    body.append(self._parse_style(directive_args_str))
                elif directive_name == "class":
                    body.append(self._parse_class(directive_args_str))
                elif directive_name == "break":
                    body.append(self._parse_break(directive_args_str))
                elif directive_name == "continue":
                    body.append(self._parse_continue(directive_args_str))
                # TODO: Add more directives
                else:
                    # raise DirectiveParsingError(
                    #     f"Unexpected directive '@{directive_name}' inside a block.",
                    #     line=token.line,
                    #     column=token.column,
                    # )
                    pass

            elif token.type == "TEXT":
                body.append(TextNode(token.value))
                self.advance()
            elif token.type == "VAR_START":
                body.append(self._parse_variable(escaped=True))
            elif token.type == "UNESCAPED_VAR_START":
                body.append(self._parse_variable(escaped=False))
            else:
                raise TemplateRenderError(
                    "Unexpected token type in _parse_until_directives: "
                    f"{token.type} with value '{token.value}' at line {token.line}, col {token.column}"
                )

        # If we reach here, we hit end of file without finding a closing directive.
        raise SyntaxError(f"Expected one of {directives_to_stop_at} but reached end of template without closure.")

    def _parse_unless(self, condition_str):
        """Parses an @unless...@endunless block."""
        condition = self._extract_expression_from_args(condition_str, "@unless")
        body_nodes = self._parse_until_directives(["@endunless"])
        self.expect("DIRECTIVE", value_prefix="@endunless")
        return UnlessNode(condition, body_nodes)

    def _parse_switch(self, expression_str):
        """Parses an @switch...@endswitch block."""
        expression = self._extract_expression_from_args(expression_str, "@switch")
        cases = []
        default_body = None

        while self.current_token():
            token = self.current_token()
            if token.type == "DIRECTIVE":
                match = re.match(r"@([a-zA-Z_][a-zA-Z0-9_]*)(.*)", token.value)
                directive_name = match.group(1)
                args_str = match.group(2).strip()

                if directive_name == "case":
                    self.advance()
                    case_value = self._extract_expression_from_args(args_str, "@case")
                    case_body = self._parse_until_directives(["@case", "@default", "@endswitch"])
                    cases.append((case_value, case_body))
                elif directive_name == "default":
                    self.advance()
                    default_body = self._parse_until_directives(["@endswitch"])
                elif directive_name == "endswitch":
                    break
                else:
                    # Ignore other directives or text between cases (usually whitespace)
                    # But if it's significant content, it might be an issue.
                    # For now, we'll just skip non-case/default directives if they appear directly inside switch
                    # but typically switch only contains cases.
                    # Actually, strict switch usually only allows cases/default.
                    # Let's assume anything else is ignored or error.
                    # For robustness, we'll just advance if it's not what we expect, or maybe raise error.
                    # But _parse_until_directives handles the body of cases.
                    # The loop here is "between" cases.
                    self.advance()
            else:
                # Ignore text/variables between cases (whitespace)
                self.advance()

        self.expect("DIRECTIVE", value_prefix="@endswitch")
        return SwitchNode(expression, cases, default_body)

    def _parse_auth(self, args_str):
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
        return AuthNode(body, else_body, guard)

    def _parse_guest(self, args_str):
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
        return GuestNode(body, else_body, guard)

    def _parse_include(self, args_str):
        """Parses an @include('path', data) directive."""
        # args_str is like "('path', data)"
        # We need to parse this. It's a python expression tuple or call args.
        # Simplest way is to store the whole args string and eval it later,
        # but we want to separate path and data if possible.
        # For now, let's just store the raw args string and let the processor eval it.
        # But wait, IncludeNode expects path and data_expr.
        # Let's just store the whole args string as 'expression' in IncludeNode?
        # No, IncludeNode has path and data_expr.
        # Let's try to split it if it's simple, otherwise just pass the whole thing to be evaled.
        # Actually, the processor can eval the whole args tuple.
        # Let's change IncludeNode to just take 'expression' or 'args'.
        # But for now, let's assume we pass the raw args string and the processor handles it.
        # Wait, I defined IncludeNode(path, data_expr).
        # I should probably just store the args_str and let processor parse it.
        # Or I can try to parse it here.
        # Let's just store the args_str as 'path' for now if it's just one arg,
        # or we can change IncludeNode to be more flexible.
        # Let's stick to the plan: pass the args string.
        # But wait, IncludeNode signature is (path, data_expr).
        # I'll just pass the whole args_str as 'path' and None as data_expr,
        # and handle the splitting in processor.
        return IncludeNode(args_str)

    def _parse_extends(self, args_str):
        """Parses an @extends('layout') directive."""
        layout = self._extract_expression_from_args(args_str, "@extends")
        return ExtendsNode(layout)

    def _parse_section(self, args_str):
        """Parses an @section('name')...@endsection block."""
        name = self._extract_expression_from_args(args_str, "@section")
        body = self._parse_until_directives(["@endsection"])
        self.expect("DIRECTIVE", value_prefix="@endsection")
        return SectionNode(name, body)

    def _parse_yield(self, args_str):
        """Parses an @yield('name', default) directive."""
        # Similar to include, might have multiple args.
        return YieldNode(args_str)

    def _parse_component(self, args_str):
        """Parses an @component('name', data)...@endcomponent block."""
        # args_str could be "('alert', {'type': 'error'})"
        body = self._parse_until_directives(["@endcomponent"])
        self.expect("DIRECTIVE", value_prefix="@endcomponent")
        return ComponentNode(args_str, body=body)

    def _parse_slot(self, args_str):
        """Parses an @slot('name')...@endslot block."""
        name = self._extract_expression_from_args(args_str, "@slot")
        body = self._parse_until_directives(["@endslot"])
        self.expect("DIRECTIVE", value_prefix="@endslot")
        return SlotNode(name, body)

    def _parse_verbatim(self, args_str):
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

    def _parse_python(self, args_str):
        """Parses an @python...@endpython block."""
        # Similar to verbatim, but for python code.
        content_parts = []
        while self.current_token():
            token = self.current_token()
            if token.type == "DIRECTIVE" and token.value == "@endpython":
                break
            content_parts.append(token.value)
            self.advance()

        self.expect("DIRECTIVE", value_prefix="@endpython")
        return PythonNode("".join(content_parts))

    def _parse_comment(self, args_str):
        """Parses an @comment...@endcomment block."""
        # Just consume until endcomment
        content_parts = []
        while self.current_token():
            token = self.current_token()
            if token.type == "DIRECTIVE" and token.value == "@endcomment":
                break
            content_parts.append(token.value)
            self.advance()

        self.expect("DIRECTIVE", value_prefix="@endcomment")
        return CommentNode("".join(content_parts))

    def _parse_cycle(self, args_str):
        return CycleNode(args_str)

    def _parse_firstof(self, args_str):
        return FirstOfNode(args_str)

    def _parse_url(self, args_str):
        return UrlNode(args_str)

    def _parse_static(self, args_str):
        path = self._extract_expression_from_args(args_str, "@static")
        return StaticNode(path)

    def _parse_method(self, args_str):
        method = self._extract_expression_from_args(args_str, "@method")
        return MethodNode(method)

    def _parse_style(self, args_str):
        expression = self._extract_expression_from_args(args_str, "@style")
        return StyleNode(expression)

    def _parse_class(self, args_str):
        expression = self._extract_expression_from_args(args_str, "@class")
        return ClassNode(expression)

    def _parse_break(self, args_str):
        condition = None
        if args_str:
            condition = self._extract_expression_from_args(args_str, "@break")
        return BreakNode(condition)

    def _parse_continue(self, args_str):
        condition = None
        if args_str:
            condition = self._extract_expression_from_args(args_str, "@continue")
        return ContinueNode(condition)

    def _extract_expression_from_args(self, args_str, directive_name=""):
        """Extracts the Python expression string from directive arguments like '(expression)'."""
        match = re.match(r"^\s*\((.*)\)\s*$", args_str)
        if not match:
            raise DirectiveParsingError(
                f"Invalid arguments for {directive_name}: '{args_str}'. "
                f"Expected parentheses, e.g., '({directive_name}(condition))'.",
            )
        return match.group(1).strip()

