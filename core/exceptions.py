# Author: Sarala Biswal
"""Platform exception hierarchy."""

from __future__ import annotations


class PlatformException(Exception):
    """Base exception for platform failures."""


class DomainNotFoundError(PlatformException):
    """Raised when a requested regulated domain is not registered."""

    def __init__(self, domain_id: str) -> None:
        """Build an error message for a missing domain adapter."""
        super().__init__(f"Domain adapter not registered for domain '{domain_id}'.")


class ContextAssemblyError(PlatformException):
    """Raised when evidence context cannot be assembled for a submission."""

    def __init__(self, submission_id: str, reason: str) -> None:
        """Build an error message with submission id and assembly failure reason."""
        super().__init__(f"Context assembly failed for submission '{submission_id}': {reason}.")


class GovernanceViolationError(PlatformException):
    """Raised when governance evaluation finds a blocking violation."""

    def __init__(self, violation: str) -> None:
        """Build an error message for a blocking governance violation."""
        super().__init__(f"Governance violation detected: {violation}.")


class EscalationRequiredError(PlatformException):
    """Raised when automation must stop for human review."""

    def __init__(self, reason: str) -> None:
        """Build an error message for a required human escalation."""
        super().__init__(f"Human escalation required: {reason}.")


class AuditWriteError(PlatformException):
    """Raised when a completed decision cannot be written to audit storage."""

    def __init__(self, submission_id: str, reason: str) -> None:
        """Build an error message with submission id and audit write failure reason."""
        super().__init__(f"Audit write failed for submission '{submission_id}': {reason}.")
