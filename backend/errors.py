"""One error type for all services. main.py turns it into an HTTP response."""


class ApiError(Exception):
    def __init__(self, errors, status=422):
        super().__init__("; ".join(errors) if isinstance(errors, list) else str(errors))
        self.errors = errors if isinstance(errors, list) else [str(errors)]
        self.status = status
