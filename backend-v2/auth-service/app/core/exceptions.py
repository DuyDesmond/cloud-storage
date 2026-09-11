class DomainError(Exception):
    """Base class for all domain exceptions."""
    def __init__(self, message: str):
        self.message = message
        super().__init__(self.message)

class UserNotFoundError(DomainError):
    """Raised when a user is not found."""
    pass

class InvalidCredentialsError(DomainError):
    """Raised when authentication fails due to invalid credentials."""
    pass

class DuplicateRecordError(DomainError):
    """Raised when attempting to create a user that already exists."""
    pass
