"""Shared cooperative cancellation exception for long-running Ollama/LLM work."""


class CooperativeCancelled(RuntimeError):
    """Raised when a cancellable operation should stop at a safe boundary."""
