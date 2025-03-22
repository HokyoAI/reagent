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


class ReagentRuntimeError(ReagentError):
    """
    An error raised when the reagent runtime encounters an issue.
    """

    pass


class NotFoundError(ReagentRuntimeError):
    """
    An error raised when a resource is not found.
    """

    pass


class NamespaceNotFoundError(NotFoundError):
    """
    An error raised when a namespace is not found.
    """

    pass


class ConflictError(ReagentRuntimeError):
    """
    An error raised when a resource is in conflict.
    """

    pass
