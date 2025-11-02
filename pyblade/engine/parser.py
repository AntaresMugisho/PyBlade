import re

from pyblade.engine.exceptions import DirectiveParsingError, TemplateRenderError

from .nodes import ForNode, IfNode, TextNode, VarNode


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
                elif directive_name == "for":
                    ast.append(self._parse_for(directive_args_str))
                elif directive_name in ["elif", "else", "endif", "empty", "endfor"]:
                    # These are control flow directives handled by their parent block parsers.
                    # Encountering them at the top level or out of sequence is a syntax error.
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
                elif directive_name == "for":
                    body.append(self._parse_for(directive_args_str))
                else:
                    raise DirectiveParsingError(
                        f"Unexpected directive '@{directive_name}' inside a block.",
                        line=token.line,
                        column=token.column,
                    )
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

    def _extract_expression_from_args(self, args_str, directive_name=""):
        """Extracts the Python expression string from directive arguments like '(expression)'."""
        match = re.match(r"^\s*\((.*)\)\s*$", args_str)
        if not match:
            raise DirectiveParsingError(
                f"Invalid arguments for {directive_name}: '{args_str}'. "
                f"Expected parentheses, e.g., '({directive_name}(condition))'.",
            )
        return match.group(1).strip()
