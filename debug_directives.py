from pyblade.engine.lexer import Lexer
from pyblade.engine.parser import Parser
from pyblade.engine.processor import TemplateProcessor

def debug_inline_comment():
    print("--- Debug Inline Comment ---")
    template = "Hello {# This is a comment #} World"
    lexer = Lexer(template)
    tokens = lexer.tokenize()
    print("Tokens:")
    for t in tokens:
        print(t)
    
    parser = Parser(tokens)
    try:
        ast = parser.parse()
        print("AST:", ast)
    except Exception as e:
        print("Parser Error:", e)

    processor = TemplateProcessor()
    output = processor.render(template, {})
    print("Output:", repr(output))

def debug_regroup():
    print("\n--- Debug Regroup ---")
    cities = [
        {'name': 'Mumbai', 'population': '19,000,000', 'country': 'India'},
        {'name': 'Calcutta', 'population': '15,000,000', 'country': 'India'},
    ]
    template = """
    @regroup(cities by country as country_list)
    @for(country in country_list)
        {{ country.grouper }}
    @endfor
    """
    processor = TemplateProcessor()
    output = processor.render(template, {"cities": cities})
    print("Output:", output)

def debug_with():
    print("\n--- Debug With ---")
    template = "@with(a=1, b=2)\n{{ a }}\n@endwith"
    processor = TemplateProcessor()
    output = processor.render(template, {})
    print("Output:", output)

if __name__ == "__main__":
    debug_inline_comment()
    debug_regroup()
    debug_with()
