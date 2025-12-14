import re


class Token:
    """Represents a token found by the lexer."""

    def __init__(self, type, value, line=None, column=None):
        self.type = type
        self.value = value
        self.line = line
        self.column = column

    def __repr__(self):
        # Limit value length for cleaner debug output
        display_value = self.value if len(self.value) < 50 else self.value[:47] + "..."
        return f"Token(type='{self.type}', value='{display_value}', line={self.line}, col={self.column})"


class Lexer:
    """
    Tokenizes a PyBlade template string into a stream of Tokens.
    It identifies variable blocks ({{}}), comment blocks ({##}), and directives (@...).
    """

    def __init__(self, template_string):
        self.template_string = template_string
        self.pos = 0  # Current position in the template string
        self.line = 1  # Current line number
        self.column = 1  # Current column number on the current line
        self.tokens = []

    def _update_pos(self, value_len):
        """Updates line and column numbers based on the length of the consumed value."""
        segment = self.template_string[self.pos : self.pos + value_len]
        new_lines = segment.count("\n")
        self.line += new_lines
        if new_lines > 0:
            # If newlines are present, column resets to 1 + length after the last newline
            last_newline_idx = segment.rfind("\n")
            self.column = value_len - last_newline_idx
        else:
            self.column += value_len
        self.pos += value_len

    def _add_token(self, type, value):
        """Creates a token and adds it to the list, then updates the lexer's position."""
        self.tokens.append(Token(type, value, self.line, self.column))
        self._update_pos(len(value))

    def _peek(self, length=1):
        """Looks ahead in the template string without advancing the position."""
        if self.pos + length > len(self.template_string):
            return self.template_string[self.pos :]  # Return remaining part if shorter than length
        return self.template_string[self.pos : self.pos + length]

    def _match_regex_at_current_pos(self, pattern):
        """Tries to match a regex pattern at the current position."""
        match = re.match(pattern, self.template_string[self.pos :])
        if match:
            return match.group(0)
        return None

    def tokenize(self):
        """Main tokenization loop."""
        while self.pos < len(self.template_string):
            # Prioritized matching for special blocks (order matters)

            # Unescaped variable display: {!! expression !!}
            if self._peek(3) == "{!!":
                self._add_token("UNESCAPED_VAR_START", "{!!")
            elif self._peek(3) == "!!}":
                self._add_token("UNESCAPED_VAR_END", "!!}")

            # Variable display: {{ expression }}
            elif self._peek(2) == "{{":
                self._add_token("VAR_START", "{{")
            elif self._peek(2) == "}}":
                self._add_token("VAR_END", "}}")

            # Comments: {# comment #}
            elif self._peek(2) == "{#":
                self._add_token("COMMENT_START", "{#")
            elif self._peek(2) == "#}":
                self._add_token("COMMENT_END", "#}")

            # PyBlade Directives: @directive or @directive(args)
            elif self._peek(1) == "@":
                # This regex captures the directive name and its argument string (including parentheses).
                # It handles balanced parentheses for arguments, which is crucial for full Python expressions.
                match_directive = self._match_regex_at_current_pos(
                    r"@([a-zA-Z_][a-zA-Z0-9_]*)\b"  # Matches @keyword (e.g., @if, @else, @for)
                    r"(?:"  # Non-capturing group for optional arguments
                    r"\s*"  # Optional whitespace between keyword and '('
                    r"\("  # Opening parenthesis
                    r"(?:[^()]*|\((?:[^()]*|\([^()]*\))*\))*"  # Content inside balanced parentheses
                    r"\)"  # Closing parenthesis
                    r")?"  # Arguments are optional
                )

                if match_directive:
                    self._add_token("DIRECTIVE", match_directive)
                else:
                    # An isolated '@' or '@' followed by non-keyword char. Treat as text.
                    self._add_token("TEXT", self._peek(1))
            else:
                # Match plain text segments. This must be the last "match anything" rule.
                # It matches any character that is NOT the start of a special block
                # We need to be careful not to consume closing delimiters
                text_segment = self._match_regex_at_current_pos(r"[^@\{}\!#]+")
                if text_segment:
                    self._add_token("TEXT", text_segment)
                else:
                    # Check for single special characters that don't form complete tokens
                    next_char = self._peek(1)
                    # Only treat as text if it's not part of a multi-char delimiter
                    if next_char and next_char not in ["@", "{", "}", "!"]:
                        self._add_token("TEXT", next_char)
                    elif next_char == "{" and self._peek(2) not in ["{{", "{#", "{!"]:
                        self._add_token("TEXT", next_char)
                    elif next_char == "}" and self._peek(2) not in ["}}", "!}"]:
                        self._add_token("TEXT", next_char)
                    elif next_char == "!" and self._peek(2) not in ["!!", "!}"]:
                        self._add_token("TEXT", next_char)
                    else:
                        # This shouldn't happen, but ensures progress
                        self._add_token("TEXT", next_char)

        return self.tokens
