"""LLM module for document generation."""

from src.llm.client import LLMError, call_llm
from src.llm.prompts import (
    prompt_generate_toc,
    prompt_self_heal,
    prompt_structure_chapter,
    prompt_summarize_intro,
)

__all__ = [
    "LLMError",
    "call_llm",
    "prompt_generate_toc",
    "prompt_self_heal",
    "prompt_structure_chapter",
    "prompt_summarize_intro",
]
