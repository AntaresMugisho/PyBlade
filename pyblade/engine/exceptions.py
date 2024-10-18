# Custom Exception classes for the template engine (e.g: TemplateNotFoundException, SyntaxErrorException)

class UndefinedVariableError(Exception):
    def __init__(self, variable_name):
        super().__init__(f"Undefined variable '{variable_name}'")
        self.variable_name = variable_name
