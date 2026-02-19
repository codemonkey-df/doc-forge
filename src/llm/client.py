"""LiteLLM client wrapper for LLM interactions."""

import os

import litellm


class LLMError(Exception):
    """Custom exception for LLM-related errors.

    Attributes:
        stage: The stage where the error occurred.
        message: The error message.
    """

    def __init__(self, stage: str, message: str) -> None:
        self.stage = stage
        self.message = message
        super().__init__(f"[{stage}] {message}")


def call_llm(system: str, user: str, model: str = "gpt-4o") -> str:
    """Call the LLM with the given system and user prompts.

    Args:
        system: The system prompt.
        user: The user prompt.
        model: The model to use. Defaults to "gpt-4o".
            Can be overridden by DOCFORGE_MODEL environment variable.

    Returns:
        The text content from the LLM response.

    Raises:
        LLMError: If the LLM call fails.
    """
    # Override model from environment variable if set
    actual_model = os.environ.get("DOCFORGE_MODEL", model)

    try:
        response = litellm.completion(
            model=actual_model,
            messages=[
                {"role": "system", "content": system},
                {"role": "user", "content": user},
            ],
        )
        return response.choices[0].message.content  # type: ignore[return-value]
    except litellm.exceptions.APIError as e:
        raise LLMError(
            stage="llm_call",
            message=f"API error: {e}",
        ) from e
    except Exception as e:
        raise LLMError(
            stage="llm_call",
            message=f"Unexpected error: {e}",
        ) from e
