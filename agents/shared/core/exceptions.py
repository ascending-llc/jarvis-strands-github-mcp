"""Custom exception hierarchy for the orchestrator."""


class OrchestratorException(Exception):
    """Base exception for all orchestrator errors."""

    pass


class ConfigurationError(OrchestratorException):
    """Raised when configuration is invalid or incomplete."""

    pass


class ValidationError(OrchestratorException):
    """Raised when input or output validation fails."""

    pass


class AgentError(OrchestratorException):
    """Raised when an agent fails to execute or returns invalid output."""

    pass


class ToolError(OrchestratorException):
    """Raised when a tool call fails."""

    pass


class WorkflowError(OrchestratorException):
    """Raised when a workflow step fails."""

    pass


class DomainVerificationError(WorkflowError):
    """Raised when domain verification fails."""

    pass


class IntegrationError(WorkflowError):
    """Raised when integration of agent outputs fails."""

    pass


class ReportGenerationError(WorkflowError):
    """Raised when report generation fails."""

    pass
