"""Plain-language API errors. Responses never include a stack trace."""


class APIError(Exception):
    def __init__(self, message: str, status: int = 400, allowed: list | None = None):
        super().__init__(message)
        self.message = message
        self.status = status
        self.allowed = list(allowed) if allowed else None


def world_name(value: str | None, default: str = "guided") -> str:
    world = (value if value is not None else default).strip().lower()
    if world not in ("guided", "explore"):
        raise APIError("world must be guided or explore.")
    return world
