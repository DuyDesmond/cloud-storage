class DomainError(Exception):
    """Base class for all domain exceptions."""
    def __init__(self, message: str):
        self.message = message
        super().__init__(self.message)

class ItemNotFoundError(DomainError):
    """Raised when a requested resource (file, folder) is not found."""
    pass

class QuotaExceededError(DomainError):
    """Raised when a user exceeds their storage quota."""
    pass

class DuplicateRecordError(DomainError):
    """Raised when attempting to create a record that already exists."""
    pass

class AccessDeniedError(DomainError):
    """Raised when a user attempts to access a resource without proper permissions."""
    pass

class InvalidOperationError(DomainError):
    """Raised when an invalid operation is attempted (e.g. moving a folder into itself)."""
    pass

class InfrastructureError(DomainError):
    """Raised when an internal server or external service error occurs."""
    pass
