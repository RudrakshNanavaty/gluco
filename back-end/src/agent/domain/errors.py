"""Errors raised below the API and tool layers, which turn them into responses."""


class PersonNotFoundError(LookupError):
    """No participant matches the reference. `suggestions` holds the closest keys."""

    def __init__(self, ref: str, suggestions: list[str] | None = None) -> None:
        super().__init__(ref)
        self.ref = ref
        self.suggestions = suggestions or []


class AmbiguousPersonError(LookupError):
    """The reference matches more than one participant. `candidates` lists them."""

    def __init__(self, ref: str, candidates: list[str]) -> None:
        super().__init__(ref)
        self.ref = ref
        self.candidates = candidates


class ForbiddenError(PermissionError):
    """The signed-in user may not see this data."""


class QueryError(ValueError):
    """A request the data cannot answer as asked (unknown metric, bad range...)."""

    def __init__(self, message: str, **details: object) -> None:
        super().__init__(message)
        self.details = details
