class ReagentError(Exception):
    """
    Base error for the reagent package.
    """

    pass


class InterpreterError(ReagentError):
    """
    An error raised when the interpreter cannot evaluate a Python expression, due to syntax error or unsupported
    operations.
    """

    pass
