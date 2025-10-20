# PyBlade Template Engine - Enhanced Pythonic Architecture
# =========================================================

import html
import re
from abc import ABC, abstractmethod
from dataclasses import dataclass
from enum import Enum, auto
from typing import Any, Callable, Dict, List, Optional, Union

# ============================================================================
# TOKEN TYPES & LEXER
# ============================================================================


class TokenType(Enum):
    """All token types in PyBlade template language"""

    # Literals
    TEXT = auto()
    STRING = auto()
    NUMBER = auto()
    BOOLEAN = auto()
    NONE = auto()

    # Identifiers & Operators
    IDENTIFIER = auto()
    DOT = auto()
    LPAREN = auto()
    RPAREN = auto()
    COMMA = auto()
    COLON = auto()
    EQUALS = auto()

    # Comparison operators
    GT = auto()
    LT = auto()
    GTE = auto()
    LTE = auto()
    EQ = auto()
    NEQ = auto()

    # Logical operators
    AND = auto()
    OR = auto()
    NOT = auto()

    # Directives
    DIRECTIVE = auto()  # @if, @for, etc.
    END_DIRECTIVE = auto()  # @endif, @endfor, etc.
    FUNCTION_DIRECTIVE = auto()  # @url(), @static(), etc.

    # Variable interpolation
    VAR_START = auto()  # {{
    VAR_END = auto()  # }}
    RAW_VAR_START = auto()  # {!!
    RAW_VAR_END = auto()  # !!}

    # Special
    EOF = auto()
    NEWLINE = auto()


@dataclass
class Token:
    """Represents a single token"""

    type: TokenType
    value: Any
    line: int
    column: int

    def __repr__(self):
        return f"Token({self.type.name}, {self.value!r}, {self.line}:{self.column})"


class Lexer:
    """
    Lexical analyzer - converts template text into tokens.
    Handles @-directives with colons, {{ }}, {!! !!}, and plain text.
    """

    def __init__(self, text: str):
        self.text = text
        self.pos = 0
        self.line = 1
        self.column = 1
        self.length = len(text)

    def current_char(self) -> Optional[str]:
        """Get current character without advancing"""
        return self.text[self.pos] if self.pos < self.length else None

    def peek(self, offset: int = 1) -> Optional[str]:
        """Look ahead without consuming"""
        pos = self.pos + offset
        return self.text[pos] if pos < self.length else None

    def peek_string(self, length: int) -> str:
        """Look ahead multiple characters"""
        return self.text[self.pos : self.pos + length]

    def advance(self) -> Optional[str]:
        """Move to next character"""
        if self.pos >= self.length:
            return None

        char = self.text[self.pos]
        self.pos += 1

        if char == "\n":
            self.line += 1
            self.column = 1
        else:
            self.column += 1

        return char

    def skip_whitespace(self, include_newlines: bool = False):
        """Skip whitespace"""
        if include_newlines:
            while self.current_char() in " \t\r\n":
                self.advance()
        else:
            while self.current_char() in " \t\r":
                self.advance()

    def read_directive(self) -> Token:
        """Read @directive, @enddirective, or @function()"""
        start_line, start_col = self.line, self.column
        self.advance()  # consume @

        name = ""
        while self.current_char() and (self.current_char().isalnum() or self.current_char() == "_"):
            name += self.current_char()
            self.advance()

        # Skip whitespace after directive name
        self.skip_whitespace()

        # Check if it's a function directive (has opening parenthesis)
        # if self.current_char() == '(':
        #     return Token(TokenType.FUNCTION_DIRECTIVE, name, start_line, start_col)

        # Check if it's an end directive
        if name.startswith("end"):
            return Token(TokenType.END_DIRECTIVE, name, start_line, start_col)
        else:
            return Token(TokenType.DIRECTIVE, name, start_line, start_col)

    def read_string(self, quote: str) -> str:
        """Read string literal"""
        result = ""
        self.advance()  # consume opening quote

        while self.current_char() and self.current_char() != quote:
            if self.current_char() == "\\":
                self.advance()
                next_char = self.current_char()
                if next_char == "n":
                    result += "\n"
                elif next_char == "t":
                    result += "\t"
                elif next_char == "r":
                    result += "\r"
                elif next_char in (quote, "\\"):
                    result += next_char
                else:
                    result += next_char
                self.advance()
            else:
                result += self.advance()

        if self.current_char() == quote:
            self.advance()  # consume closing quote

        return result

    def read_number(self) -> Union[int, float]:
        """Read numeric literal"""
        num_str = ""
        has_dot = False

        while self.current_char() and (self.current_char().isdigit() or self.current_char() == "."):
            if self.current_char() == ".":
                if has_dot:
                    break
                has_dot = True
            num_str += self.current_char()
            self.advance()

        return float(num_str) if has_dot else int(num_str)

    def read_identifier(self) -> str:
        """Read identifier (variable name, keyword)"""
        result = ""
        while self.current_char() and (self.current_char().isalnum() or self.current_char() == "_"):
            result += self.current_char()
            self.advance()
        return result

    def tokenize(self) -> List[Token]:
        """Convert entire template into tokens"""
        tokens = []

        while self.pos < self.length:
            # Check for raw variable interpolation {!!
            if self.peek_string(3) == "{!!":
                tokens.append(Token(TokenType.RAW_VAR_START, "{!!", self.line, self.column))
                self.advance()
                self.advance()
                self.advance()
                tokens.extend(self.tokenize_expression(raw=True))
                continue

            # Check for escaped variable interpolation {{
            if self.peek_string(2) == "{{":
                tokens.append(Token(TokenType.VAR_START, "{{", self.line, self.column))
                self.advance()
                self.advance()
                tokens.extend(self.tokenize_expression(raw=False))
                continue

            # Check for directive @
            if self.current_char() == "@" and (self.peek() or " ").isalpha():
                tokens.append(self.read_directive())
                continue

            # Plain text
            text = ""
            start_line, start_col = self.line, self.column

            while self.current_char():
                # Check for start of special sequences
                if self.peek_string(3) == "{!!":
                    break
                if self.peek_string(2) == "{{":
                    break
                if self.current_char() == "@" and (self.peek() or " ").isalpha():
                    break

                text += self.advance()

            if text:
                tokens.append(Token(TokenType.TEXT, text, start_line, start_col))

        tokens.append(Token(TokenType.EOF, None, self.line, self.column))
        return tokens

    def tokenize_expression(self, raw: bool = False) -> List[Token]:
        """Tokenize expression inside {{ }} or {!! !!} or directive"""
        expr_tokens = []

        while self.current_char():
            self.skip_whitespace()

            if not self.current_char():
                break

            # Check for !!}
            if raw and self.peek_string(3) == "!!}":
                expr_tokens.append(Token(TokenType.RAW_VAR_END, "!!}", self.line, self.column))
                self.advance()
                self.advance()
                self.advance()
                break

            # Check for }}
            if not raw and self.peek_string(2) == "}}":
                expr_tokens.append(Token(TokenType.VAR_END, "}}", self.line, self.column))
                self.advance()
                self.advance()
                break

            # String literal
            if self.current_char() in "\"'":
                quote = self.current_char()
                start_line, start_col = self.line, self.column
                value = self.read_string(quote)
                expr_tokens.append(Token(TokenType.STRING, value, start_line, start_col))
                continue

            # Number
            if self.current_char().isdigit():
                start_line, start_col = self.line, self.column
                value = self.read_number()
                expr_tokens.append(Token(TokenType.NUMBER, value, start_line, start_col))
                continue

            # Identifier or keyword
            if self.current_char().isalpha() or self.current_char() == "_":
                start_line, start_col = self.line, self.column
                value = self.read_identifier()

                # Check for keywords
                if value in ("true", "True"):
                    expr_tokens.append(Token(TokenType.BOOLEAN, True, start_line, start_col))
                elif value in ("false", "False"):
                    expr_tokens.append(Token(TokenType.BOOLEAN, False, start_line, start_col))
                elif value in ("none", "None", "null"):
                    expr_tokens.append(Token(TokenType.NONE, None, start_line, start_col))
                elif value == "and":
                    expr_tokens.append(Token(TokenType.AND, "and", start_line, start_col))
                elif value == "or":
                    expr_tokens.append(Token(TokenType.OR, "or", start_line, start_col))
                elif value == "not":
                    expr_tokens.append(Token(TokenType.NOT, "not", start_line, start_col))
                elif value == "in":
                    expr_tokens.append(Token(TokenType.IDENTIFIER, "in", start_line, start_col))
                else:
                    expr_tokens.append(Token(TokenType.IDENTIFIER, value, start_line, start_col))
                continue

            # Multi-character operators
            char = self.current_char()
            next_char = self.peek()
            start_line, start_col = self.line, self.column

            if char == ">" and next_char == "=":
                expr_tokens.append(Token(TokenType.GTE, ">=", start_line, start_col))
                self.advance()
                self.advance()
            elif char == "<" and next_char == "=":
                expr_tokens.append(Token(TokenType.LTE, "<=", start_line, start_col))
                self.advance()
                self.advance()
            elif char == "=" and next_char == "=":
                expr_tokens.append(Token(TokenType.EQ, "==", start_line, start_col))
                self.advance()
                self.advance()
            elif char == "!" and next_char == "=":
                expr_tokens.append(Token(TokenType.NEQ, "!=", start_line, start_col))
                self.advance()
                self.advance()
            # Single character operators
            elif char == ".":
                expr_tokens.append(Token(TokenType.DOT, ".", start_line, start_col))
                self.advance()
            elif char == "(":
                expr_tokens.append(Token(TokenType.LPAREN, "(", start_line, start_col))
                self.advance()
            elif char == ")":
                expr_tokens.append(Token(TokenType.RPAREN, ")", start_line, start_col))
                self.advance()
            elif char == ",":
                expr_tokens.append(Token(TokenType.COMMA, ",", start_line, start_col))
                self.advance()
            elif char == ":":
                expr_tokens.append(Token(TokenType.COLON, ":", start_line, start_col))
                self.advance()
            elif char == "=":
                expr_tokens.append(Token(TokenType.EQUALS, "=", start_line, start_col))
                self.advance()
            elif char == ">":
                expr_tokens.append(Token(TokenType.GT, ">", start_line, start_col))
                self.advance()
            elif char == "<":
                expr_tokens.append(Token(TokenType.LT, "<", start_line, start_col))
                self.advance()
            elif char == "\n":
                # Newline can end directive
                break
            else:
                self.advance()

        return expr_tokens


# ============================================================================
# AST (Abstract Syntax Tree) NODES
# ============================================================================


class ASTNode(ABC):
    """Base class for all AST nodes"""

    pass


@dataclass
class TextNode(ASTNode):
    """Plain text node"""

    content: str


@dataclass
class Expression(ASTNode):
    """Base class for expressions"""

    pass


@dataclass
class VariableExpr(Expression):
    """Variable reference: user.name.slugify"""

    name: str
    properties: List[Union[str, "MethodCall"]]


@dataclass
class BinaryOpExpr(Expression):
    """Binary operation: a > b, a == b, a and b"""

    left: Expression
    operator: str
    right: Expression


@dataclass
class UnaryOpExpr(Expression):
    """Unary operation: not x"""

    operator: str
    operand: Expression


@dataclass
class LiteralExpr(Expression):
    """Literal value: 123, "string", True"""

    value: Any


@dataclass
class MethodCall:
    """Method call with arguments: excerpt(250, "...")"""

    name: str
    args: List[Any]


@dataclass
class VariableNode(ASTNode):
    """Variable interpolation: {{ user.name }} or {!! html !!}"""

    expression: Expression
    escape: bool  # True for {{}}, False for {!!!!}


@dataclass
class IfNode(ASTNode):
    """@if condition: ... @endif"""

    condition: Expression
    body: List[ASTNode]
    elif_branches: List[tuple[Expression, List[ASTNode]]]
    else_body: Optional[List[ASTNode]]


@dataclass
class ForNode(ASTNode):
    """@for item in items: ... @endfor"""

    item_var: str
    iterable: Expression
    body: List[ASTNode]


@dataclass
class BlockNode(ASTNode):
    """@block content: ... @endblock"""

    name: str
    body: List[ASTNode]


@dataclass
class ExtendsNode(ASTNode):
    """@extends('base.html')"""

    parent_template: str


@dataclass
class IncludeNode(ASTNode):
    """@include('partial.html', {'key': value})"""

    template_name: str
    context: Optional[Dict[str, Any]]


@dataclass
class FunctionDirectiveNode(ASTNode):
    """Function directives: @url('home'), @static('css/style.css')"""

    name: str
    args: List[Any]


@dataclass
class RawNode(ASTNode):
    """@raw ... @endraw - no processing"""

    content: str


# ============================================================================
# PARSER
# ============================================================================


class Parser:
    """
    Converts tokens into an Abstract Syntax Tree (AST).
    Handles nested structures and directive syntax.
    """

    def __init__(self, tokens: List[Token]):
        self.tokens = tokens
        self.pos = 0

    def current_token(self) -> Token:
        """Get current token"""
        return self.tokens[self.pos] if self.pos < len(self.tokens) else self.tokens[-1]

    def peek_token(self, offset: int = 1) -> Token:
        """Look ahead"""
        pos = self.pos + offset
        return self.tokens[pos] if pos < len(self.tokens) else self.tokens[-1]

    def advance(self) -> Token:
        """Move to next token"""
        token = self.current_token()
        if self.pos < len(self.tokens) - 1:
            self.pos += 1
        return token

    def expect(self, token_type: TokenType) -> Token:
        """Consume token of expected type or raise error"""
        token = self.current_token()
        if token.type != token_type:
            raise SyntaxError(f"Expected {token_type.name}, got {token.type.name} at {token.line}:{token.column}")
        return self.advance()

    def parse(self) -> List[ASTNode]:
        """Parse entire template"""
        return self.parse_body()

    def parse_body(self, end_tokens: Optional[List[str]] = None) -> List[ASTNode]:
        """Parse template body until end token"""
        nodes = []

        while self.current_token().type != TokenType.EOF:
            # Check for end tokens
            if end_tokens and self.current_token().type == TokenType.END_DIRECTIVE:
                if self.current_token().value in end_tokens:
                    break

            node = self.parse_statement()
            if node:
                nodes.append(node)

        return nodes

    def parse_statement(self) -> Optional[ASTNode]:
        """Parse a single statement (text, variable, directive)"""
        token = self.current_token()

        if token.type == TokenType.TEXT:
            return TextNode(self.advance().value)

        elif token.type in (TokenType.VAR_START, TokenType.RAW_VAR_START):
            return self.parse_variable()

        elif token.type == TokenType.DIRECTIVE:
            return self.parse_block_directive()

        elif token.type == TokenType.FUNCTION_DIRECTIVE:
            return self.parse_function_directive()

        elif token.type == TokenType.EOF:
            return None

        else:
            self.advance()
            return None

    def parse_variable(self) -> VariableNode:
        """Parse {{ variable }} or {!! variable !!}"""
        token = self.advance()
        escape = token.type == TokenType.VAR_START

        # Parse expression
        expr = self.parse_expression()

        # Expect closing
        if escape:
            self.expect(TokenType.VAR_END)
        else:
            self.expect(TokenType.RAW_VAR_END)

        return VariableNode(expr, escape)

    def parse_expression(self) -> Expression:
        """Parse expression with operators"""
        return self.parse_or_expression()

    def parse_or_expression(self) -> Expression:
        """Parse OR expression"""
        left = self.parse_and_expression()

        while self.current_token().type == TokenType.OR:
            self.advance()
            right = self.parse_and_expression()
            left = BinaryOpExpr(left, "or", right)

        return left

    def parse_and_expression(self) -> Expression:
        """Parse AND expression"""
        left = self.parse_not_expression()

        while self.current_token().type == TokenType.AND:
            self.advance()
            right = self.parse_not_expression()
            left = BinaryOpExpr(left, "and", right)

        return left

    def parse_not_expression(self) -> Expression:
        """Parse NOT expression"""
        if self.current_token().type == TokenType.NOT:
            self.advance()
            operand = self.parse_not_expression()
            return UnaryOpExpr("not", operand)

        return self.parse_comparison_expression()

    def parse_comparison_expression(self) -> Expression:
        """Parse comparison expression"""
        left = self.parse_primary_expression()

        token = self.current_token()
        if token.type in (TokenType.GT, TokenType.LT, TokenType.GTE, TokenType.LTE, TokenType.EQ, TokenType.NEQ):
            op = self.advance().value
            right = self.parse_primary_expression()
            return BinaryOpExpr(left, op, right)

        return left

    def parse_primary_expression(self) -> Expression:
        """Parse primary expression (variable, literal, parenthesized)"""
        token = self.current_token()

        # Parenthesized expression
        if token.type == TokenType.LPAREN:
            self.advance()
            expr = self.parse_expression()
            self.expect(TokenType.RPAREN)
            return expr

        # Literal values
        if token.type == TokenType.STRING:
            return LiteralExpr(self.advance().value)

        if token.type == TokenType.NUMBER:
            return LiteralExpr(self.advance().value)

        if token.type == TokenType.BOOLEAN:
            return LiteralExpr(self.advance().value)

        if token.type == TokenType.NONE:
            self.advance()
            return LiteralExpr(None)

        # Variable with property chain
        if token.type == TokenType.IDENTIFIER:
            return self.parse_variable_expression()

        raise SyntaxError(f"Unexpected token in expression: {token}")

    def parse_variable_expression(self) -> VariableExpr:
        """Parse variable with property chain: user.name.slugify()"""
        name = self.expect(TokenType.IDENTIFIER).value
        properties = []

        # Parse property chain
        while self.current_token().type == TokenType.DOT:
            self.advance()  # consume dot

            prop_token = self.expect(TokenType.IDENTIFIER)
            prop_name = prop_token.value

            # Check if it's a method call
            if self.current_token().type == TokenType.LPAREN:
                args = self.parse_arguments()
                properties.append(MethodCall(prop_name, args))
            else:
                properties.append(prop_name)

        return VariableExpr(name, properties)

    def parse_arguments(self) -> List[Any]:
        """Parse method/function arguments (arg1, arg2, ...)"""
        self.expect(TokenType.LPAREN)
        args = []

        while self.current_token().type != TokenType.RPAREN:
            token = self.current_token()

            if token.type == TokenType.STRING:
                args.append(self.advance().value)
            elif token.type == TokenType.NUMBER:
                args.append(self.advance().value)
            elif token.type == TokenType.BOOLEAN:
                args.append(self.advance().value)
            elif token.type == TokenType.NONE:
                self.advance()
                args.append(None)
            elif token.type == TokenType.IDENTIFIER:
                # Variable reference or keyword argument
                name = self.advance().value
                if self.current_token().type == TokenType.EQUALS:
                    # Keyword argument
                    self.advance()
                    value_token = self.current_token()
                    if value_token.type == TokenType.STRING:
                        args.append((name, self.advance().value))
                    elif value_token.type == TokenType.NUMBER:
                        args.append((name, self.advance().value))
                    elif value_token.type == TokenType.BOOLEAN:
                        args.append((name, self.advance().value))
                else:
                    args.append(name)

            # Handle comma
            if self.current_token().type == TokenType.COMMA:
                self.advance()

        self.expect(TokenType.RPAREN)
        return args

    def parse_block_directive(self) -> ASTNode:
        """Parse block directive: @if:, @for:, etc."""
        directive_token = self.advance()
        directive_name = directive_token.value

        if directive_name == "if":
            return self.parse_if()
        elif directive_name == "for":
            return self.parse_for()
        elif directive_name == "block":
            return self.parse_block()
        elif directive_name == "raw":
            return self.parse_raw()
        else:
            raise SyntaxError(f"Unknown directive: @{directive_name}")

    def parse_function_directive(self) -> FunctionDirectiveNode:
        """Parse function directive: @url('home'), @static('css/style.css')"""
        name = self.advance().value
        args = self.parse_arguments()
        return FunctionDirectiveNode(name, args)

    def parse_if(self) -> IfNode:
        """Parse @if condition: ... @elif: ... @else: ... @endif"""
        # Parse condition
        condition = self.parse_expression()

        # Expect colon
        self.expect(TokenType.COLON)

        # Parse body
        body = self.parse_body(["endif", "elif", "else"])

        # Handle elif and else
        elif_branches = []
        else_body = None

        while self.current_token().type == TokenType.DIRECTIVE:
            if self.current_token().value == "elif":
                self.advance()
                elif_condition = self.parse_expression()
                self.expect(TokenType.COLON)
                elif_body = self.parse_body(["endif", "elif", "else"])
                elif_branches.append((elif_condition, elif_body))
            elif self.current_token().value == "else":
                self.advance()
                self.expect(TokenType.COLON)
                else_body = self.parse_body(["endif"])
                break

        self.expect(TokenType.END_DIRECTIVE)  # @endif

        return IfNode(condition, body, elif_branches, else_body)

    def parse_for(self) -> ForNode:
        """Parse @for item in items: ... @endfor"""
        item_var = self.expect(TokenType.IDENTIFIER).value

        # Expect 'in' keyword
        in_token = self.expect(TokenType.IDENTIFIER)
        if in_token.value != "in":
            raise SyntaxError(f"Expected 'in' in @for directive, got '{in_token.value}'")

        # Parse iterable expression
        iterable = self.parse_expression()

        # Expect colon
        self.expect(TokenType.COLON)

        body = self.parse_body(["endfor"])
        self.expect(TokenType.END_DIRECTIVE)  # @endfor

        return ForNode(item_var, iterable, body)

    def parse_block(self) -> BlockNode:
        """Parse @block name: ... @endblock"""
        name = self.expect(TokenType.IDENTIFIER).value
        self.expect(TokenType.COLON)
        body = self.parse_body(["endblock"])
        self.expect(TokenType.END_DIRECTIVE)

        return BlockNode(name, body)

    def parse_raw(self) -> RawNode:
        """Parse @raw: ... @endraw"""
        self.expect(TokenType.COLON)
        content = ""

        # Collect all text until @endraw
        while self.current_token().type != TokenType.END_DIRECTIVE:
            if self.current_token().type == TokenType.EOF:
                raise SyntaxError("Unclosed @raw directive")

            if self.current_token().type == TokenType.TEXT:
                content += self.current_token().value

            self.advance()

        self.expect(TokenType.END_DIRECTIVE)  # @endraw
        return RawNode(content)


# ============================================================================
# TYPE-AWARE VALUE WRAPPERS
# ============================================================================


class ValueWrapper:
    """Base wrapper for adding type-specific properties"""

    def __init__(self, value: Any):
        self._value = value

    def __str__(self):
        return str(self._value)

    def __repr__(self):
        return repr(self._value)

    def __bool__(self):
        return bool(self._value)


class StringWrapper(ValueWrapper):
    """String with helper properties/methods"""

    def slugify(self) -> str:
        """Convert to URL-friendly slug"""
        value = str(self._value).lower()
        value = re.sub(r"[^\w\s-]", "", value)
        value = re.sub(r"[-\s]+", "-", value)
        return value.strip("-")

    def excerpt(self, length: int = 100, suffix: str = "...") -> str:
        """Truncate to length with suffix"""
        text = str(self._value)
        if len(text) <= length:
            return text
        return text[:length].rsplit(" ", 1)[0] + suffix

    def title_case(self) -> str:
        """Convert to title case"""
        return str(self._value).title()

    def upper(self) -> str:
        return str(self._value).upper()

    def lower(self) -> str:
        return str(self._value).lower()

    def capitalize(self) -> str:
        return str(self._value).capitalize()

    def strip(self) -> str:
        return str(self._value).strip()


class DateWrapper(ValueWrapper):
    """Date/datetime with helper properties"""

    def humanize(self) -> str:
        """Human-readable relative time"""
        from datetime import datetime, timedelta

        if not isinstance(self._value, datetime):
            return str(self._value)

        now = datetime.now()
        diff = now - self._value

        if diff < timedelta(minutes=1):
            return "just now"
        elif diff < timedelta(hours=1):
            mins = int(diff.total_seconds() / 60)
            return f"{mins} minute{'s' if mins > 1 else ''} ago"
        elif diff < timedelta(days=1):
            hours = int(diff.total_seconds() / 3600)
            return f"{hours} hour{'s' if hours > 1 else ''} ago"
        elif diff < timedelta(days=7):
            days = diff.days
            return f"{days} day{'s' if days > 1 else ''} ago"
        elif diff < timedelta(days=30):
            weeks = diff.days // 7
            return f"{weeks} week{'s' if weeks > 1 else ''} ago"
        elif diff < timedelta(days=365):
            months = diff.days // 30
            return f"{months} month{'s' if months > 1 else ''} ago"
        else:
            years = diff.days // 365
            return f"{years} year{'s' if years > 1 else ''} ago"

    def format(self, fmt: str = "%Y-%m-%d") -> str:
        """Format date with strftime"""
        if hasattr(self._value, "strftime"):
            return self._value.strftime(fmt)
        return str(self._value)


class ListWrapper(ValueWrapper):
    """List with helper properties"""

    def first(self):
        """Get first item"""
        return self._value[0] if self._value else None

    def last(self):
        """Get last item"""
        return self._value[-1] if self._value else None

    def count(self) -> int:
        """Get count"""
        return len(self._value)

    def join(self, separator: str = ", ") -> str:
        """Join items"""
        return separator.join(str(item) for item in self._value)


class NumberWrapper(ValueWrapper):
    """Number with helper properties"""

    def format(self, decimals: int = 2) -> str:
        """Format number with decimals"""
        return f"{self._value:.{decimals}f}"

    def abs(self):
        """Absolute value"""
        return abs(self._value)

    def round(self, decimals: int = 0):
        """Round number"""
        return round(self._value, decimals)


def wrap_value(value: Any) -> ValueWrapper:
    """Wrap value with appropriate wrapper"""
    from datetime import date, datetime

    if isinstance(value, str):
        return StringWrapper(value)
    elif isinstance(value, (datetime, date)):
        return DateWrapper(value)
    elif isinstance(value, (list, tuple)):
        return ListWrapper(value)
    elif isinstance(value, (int, float)):
        return NumberWrapper(value)
    else:
        return ValueWrapper(value)


# ============================================================================
# RENDERER
# ============================================================================


class Renderer:
    """Renders AST to final output"""

    def __init__(self, context: Dict[str, Any], template_loader: Optional[Callable] = None):
        self.context = context
        self.blocks = {}  # For template inheritance
        self.template_loader = template_loader

        # Register built-in function directives
        self.function_directives = {
            "url": self._directive_url,
            "static": self._directive_static,
            "csrf": self._directive_csrf,
            "asset": self._directive_asset,
        }

    def render(self, nodes: List[ASTNode]) -> str:
        """Render list of nodes"""
        output = []
        for node in nodes:
            result = self.render_node(node)
            if result is not None:
                output.append(str(result))
        return "".join(output)

    def render_node(self, node: ASTNode) -> str:
        """Render a single node"""
        if isinstance(node, TextNode):
            return node.content

        elif isinstance(node, VariableNode):
            return self.render_variable(node)

        elif isinstance(node, IfNode):
            return self.render_if(node)

        elif isinstance(node, ForNode):
            return self.render_for(node)

        elif isinstance(node, BlockNode):
            return self.render_block(node)

        elif isinstance(node, FunctionDirectiveNode):
            return self.render_function_directive(node)

        elif isinstance(node, RawNode):
            return node.content

        elif isinstance(node, ExtendsNode):
            return f"<!-- extends: {node.parent_template} -->"

        elif isinstance(node, IncludeNode):
            return f"<!-- include: {node.template_name} -->"

        return ""

    def render_variable(self, node: VariableNode) -> str:
        """Render variable with optional escaping"""
        value = self.evaluate_expression(node.expression)

        if value is None:
            return ""

        result = str(value)

        # Auto-escape HTML unless it's raw interpolation
        if node.escape:
            result = html.escape(result)

        return result

    def evaluate_expression(self, expr: Expression) -> Any:
        """Evaluate an expression to a value"""
        if isinstance(expr, LiteralExpr):
            return expr.value

        elif isinstance(expr, VariableExpr):
            return self.resolve_variable(expr)

        elif isinstance(expr, BinaryOpExpr):
            left = self.evaluate_expression(expr.left)
            right = self.evaluate_expression(expr.right)

            if expr.operator == "and":
                return left and right
            elif expr.operator == "or":
                return left or right
            elif expr.operator == ">":
                return left > right
            elif expr.operator == "<":
                return left < right
            elif expr.operator == ">=":
                return left >= right
            elif expr.operator == "<=":
                return left <= right
            elif expr.operator == "==":
                return left == right
            elif expr.operator == "!=":
                return left != right

        elif isinstance(expr, UnaryOpExpr):
            operand = self.evaluate_expression(expr.operand)
            if expr.operator == "not":
                return not operand

        return None

    def resolve_variable(self, var_expr: VariableExpr) -> Any:
        """Resolve variable with property chain"""
        # Get base value
        value = self.context.get(var_expr.name)
        if value is None:
            return None

        # If no properties, return wrapped value
        if not var_expr.properties:
            return value

        # Wrap value for type-aware properties
        wrapped = wrap_value(value)

        # Apply property chain
        for prop in var_expr.properties:
            if isinstance(prop, MethodCall):
                # Call method with arguments
                method = getattr(wrapped, prop.name, None)
                if callable(method):
                    # Resolve any variable references in arguments
                    resolved_args = []
                    for arg in prop.args:
                        if isinstance(arg, str) and arg in self.context:
                            resolved_args.append(self.context[arg])
                        else:
                            resolved_args.append(arg)

                    result = method(*resolved_args)
                    # Re-wrap the result
                    wrapped = wrap_value(result) if not isinstance(result, ValueWrapper) else result
                else:
                    return None
            else:
                # Access property or attribute
                # First try the wrapper
                attr = getattr(wrapped, prop, None)
                if attr is not None:
                    if callable(attr):
                        result = attr()
                        wrapped = wrap_value(result) if not isinstance(result, ValueWrapper) else result
                    else:
                        wrapped = wrap_value(attr) if not isinstance(attr, ValueWrapper) else attr
                else:
                    # Try accessing the underlying value (for dict, object attributes)
                    underlying = wrapped._value
                    if isinstance(underlying, dict):
                        value = underlying.get(prop)
                        if value is not None:
                            wrapped = wrap_value(value)
                        else:
                            return None
                    elif hasattr(underlying, prop):
                        value = getattr(underlying, prop)
                        if callable(value):
                            value = value()
                        wrapped = wrap_value(value)
                    else:
                        return None

        # Return the underlying value
        return wrapped._value if isinstance(wrapped, ValueWrapper) else wrapped

    def render_if(self, node: IfNode) -> str:
        """Conditional rendering"""
        # Evaluate condition
        condition_value = self.evaluate_expression(node.condition)

        if condition_value:
            return self.render(node.body)

        # Check elif branches
        for elif_condition, elif_body in node.elif_branches:
            elif_value = self.evaluate_expression(elif_condition)
            if elif_value:
                return self.render(elif_body)

        # Else branch
        if node.else_body:
            return self.render(node.else_body)

        return ""

    def render_for(self, node: ForNode) -> str:
        """Loop rendering"""
        iterable = self.evaluate_expression(node.iterable)

        if not iterable:
            return ""

        output = []

        for index, item in enumerate(iterable):
            # Create new context with loop variable
            old_value = self.context.get(node.item_var)
            self.context[node.item_var] = item

            # Also provide loop variable (like Django's forloop)
            old_loop = self.context.get("loop")
            self.context["loop"] = {
                "index": index,
                "index0": index,
                "index1": index + 1,
                "first": index == 0,
                "last": index == len(iterable) - 1,
                "length": len(iterable),
            }

            output.append(self.render(node.body))

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

    def render_block(self, node: BlockNode) -> str:
        """Block for template inheritance"""
        # Store block for potential override
        if node.name not in self.blocks:
            self.blocks[node.name] = node.body

        return self.render(self.blocks[node.name])

    def render_function_directive(self, node: FunctionDirectiveNode) -> str:
        """Render function directive"""
        handler = self.function_directives.get(node.name)

        if handler:
            return handler(node.args)

        return f"<!-- Unknown directive: @{node.name} -->"

    # Built-in function directive handlers
    def _directive_url(self, args: List[Any]) -> str:
        """@url('route_name', param1, param2)"""
        if not args:
            return "#"

        route_name = args[0]
        # In a real implementation, you'd use your router here
        # For now, just return a placeholder
        return f"/url/{route_name}"

    def _directive_static(self, args: List[Any]) -> str:
        """@static('path/to/file.css')"""
        if not args:
            return ""

        path = args[0]
        # In a real implementation, you'd use your static files handler
        return f"/static/{path}"

    def _directive_csrf(self, args: List[Any]) -> str:
        """@csrf() - CSRF token field"""
        token = self.context.get("csrf_token", "dummy-csrf-token")
        return f'<input type="hidden" name="csrf_token" value="{token}">'

    def _directive_asset(self, args: List[Any]) -> str:
        """@asset('path/to/file.js')"""
        if not args:
            return ""

        path = args[0]
        return f"/assets/{path}"

    def register_function_directive(self, name: str, handler: Callable):
        """Register a custom function directive"""
        self.function_directives[name] = handler


# ============================================================================
# TEMPLATE ENGINE
# ============================================================================


class TemplateEngine:
    """Main template engine interface"""

    def __init__(self, template_dirs: Optional[List[str]] = None):
        self.template_dirs = template_dirs or []
        self.custom_wrappers = {}
        self.function_directives = {}

    def render_string(self, template: str, context: Dict[str, Any]) -> str:
        """Render template string with context"""

        from pprint import pprint

        # Lexer: text -> tokens
        lexer = Lexer(template)
        tokens = lexer.tokenize()

        pprint(tokens)
        # # Parser: tokens -> AST
        # parser = Parser(tokens)
        # ast = parser.parse()

        # # Renderer: AST -> output
        # renderer = Renderer(context)

        # # Register custom function directives
        # for name, handler in self.function_directives.items():
        #     renderer.register_function_directive(name, handler)

        # output = renderer.render(ast)

        return "output"

    def render_file(self, filename: str, context: Dict[str, Any]) -> str:
        """Render template file"""
        # Try to find the template in template directories
        filepath = None

        if self.template_dirs:
            for template_dir in self.template_dirs:
                import os

                potential_path = os.path.join(template_dir, filename)
                if os.path.exists(potential_path):
                    filepath = potential_path
                    break
        else:
            filepath = filename

        if not filepath:
            raise FileNotFoundError(f"Template not found: {filename}")

        with open(filepath, "r", encoding="utf-8") as f:
            template = f.read()

        return self.render_string(template, context)

    def register_function_directive(self, name: str, handler: Callable):
        """Register a custom function directive"""
        self.function_directives[name] = handler

    def register_wrapper(self, type_class: type, wrapper_class: type):
        """Register a custom value wrapper for a specific type"""
        self.custom_wrappers[type_class] = wrapper_class


# ============================================================================
# USAGE EXAMPLE
# ============================================================================

if __name__ == "__main__":
    from datetime import datetime, timedelta

    # Example template with Pythonic syntax
    template = """
<!DOCTYPE html>
<html>
<head>
    <title>{{ title.upper }}</title>
    <link rel="stylesheet" href="@static('css/style.css')">
</head>
<body>
    <h1>{{ title.title_case }}</h1>
    <p>{{ description.excerpt(50, "...") }}</p>

    @if user.is_admin:
        <div class="admin-panel">
            <h2>Admin Panel</h2>
            <p>Welcome, administrator {{ user.name }}!</p>
        </div>
    @elif user.is_authenticated:
        <div class="user-panel">
            <p>Welcome back, {{ user.name }}!</p>
        </div>
    @else:
        <div class="guest-panel">
            <p>Please log in to continue.</p>
        </div>
    @endif

    @if posts and posts.count > 0:
        <section class="posts">
            <h2>Recent Posts ({{ posts.count }} total)</h2>

            @for post in posts:
                <article class="post">
                    <h3>{{ post.title.title_case }}</h3>
                    <div class="content">
                        {!! post.html_content !!}
                    </div>
                    <p class="excerpt">{{ post.content.excerpt(100) }}</p>
                    <footer>
                        <small>Posted {{ post.date.humanize }}</small>
                        <span>by {{ post.author.upper }}</span>
                        @if loop.first:
                            <span class="badge">Latest</span>
                        @endif
                    </footer>
                </article>
            @endfor
        </section>
    @else:
        <p>No posts available.</p>
    @endif

    <div class="tags">
        @if tags:
            <p>Tags: {{ tags.join(", ") }}</p>
        @endif
    </div>

    @raw:
        This content is not processed: {{ variable }} @if something
        <script>var x = {{ dangerous_code }};</script>
    @endraw

    <footer>
        <p>&copy; 2025 MyApp</p>
        <a href="@url('home')">Home</a>
        <a href="@url('about')">About</a>
    </footer>
</body>
</html>
"""

    # Example context
    context = {
        "title": "my awesome blog",
        "description": "This is a really long description that will be truncated to show how the excerpt function works in PyBlade templates with type-aware properties",
        "user": {"name": "John Doe", "is_admin": True, "is_authenticated": True},
        "posts": [
            {
                "title": "first post about python",
                "content": "This is the content of the first post. It has quite a bit of text that we want to show as an excerpt to demonstrate the functionality.",
                "html_content": "<p>This is <strong>HTML</strong> content that will <em>not</em> be escaped!</p>",
                "date": datetime.now() - timedelta(hours=2),
                "author": "jane smith",
            },
            {
                "title": "second post about templates",
                "content": "Another post with some interesting content about PyBlade templating engine and its features.",
                "html_content": "<p>More <strong>unescaped</strong> HTML here.</p>",
                "date": datetime.now() - timedelta(days=3),
                "author": "bob johnson",
            },
            {
                "title": "third post",
                "content": "A third post to demonstrate the loop functionality.",
                "html_content": "<p>Third post HTML content.</p>",
                "date": datetime.now() - timedelta(weeks=2),
                "author": "alice williams",
            },
        ],
        "tags": ["python", "templates", "web development", "pyblade"],
        "csrf_token": "abc123xyz789",
    }

    # Create engine and render
    engine = TemplateEngine()
    output = engine.render_string(template, context)
    print(output)

    print("\n" + "=" * 80)
    print("Demonstration of expression evaluation:")
    print("=" * 80)

    # Test expressions
    test_template = """
@if user.is_admin and posts.count > 2:
    <p>Admin with many posts!</p>
@endif

@if not user.is_guest:
    <p>User is authenticated</p>
@endif

@for post in posts:
    @if loop.index1 <= 2:
        <p>Top post #{{ loop.index1 }}: {{ post.title }}</p>
    @endif
@endfor
"""

    test_context = {"user": {"is_admin": True, "is_guest": False}, "posts": context["posts"]}

    test_output = engine.render_string(test_template, test_context)
    print(test_output)
