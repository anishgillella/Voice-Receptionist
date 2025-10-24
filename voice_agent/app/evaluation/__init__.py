"""Call evaluation module with LLM judge and Logfire tracing."""

from .logfire_tracing import setup_logfire, trace_model
from .llm_judge import judge_call
from .metrics_calculator import calculate_call_duration, analyze_transcript_length, extract_key_phrases

__all__ = ["setup_logfire", "trace_model", "judge_call", "calculate_call_duration", "analyze_transcript_length", "extract_key_phrases"]
