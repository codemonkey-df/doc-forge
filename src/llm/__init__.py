"""LLM module for document generation."""

from src.llm.client import LLMError, call_llm
from src.llm.generator import ResolvedContext, generate_content, read_file
from src.llm.prompts import (
    prompt_self_heal,
    prompt_structure_chapter,
    prompt_summarize_intro,
)

__all__ = [
    "LLMError",
    "ResolvedContext",
    "call_llm",
    "generate_content",
    "prompt_self_heal",
    "prompt_structure_chapter",
    "prompt_summarize_intro",
    "read_file",
]
