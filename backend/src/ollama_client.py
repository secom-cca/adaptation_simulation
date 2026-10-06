"""Shared Ollama client with host env support and concurrency limiting."""

from __future__ import annotations

import os
import threading
from contextlib import contextmanager
from typing import Any, Dict, Iterator, List, Optional

try:
    import ollama
except ModuleNotFoundError:
    ollama = None

DEFAULT_OLLAMA_HOST = "http://127.0.0.1:11434"
DEFAULT_OLLAMA_MODEL = "gemma4:e2b"
DEFAULT_LLM_MAX_CONCURRENCY = 3
DEFAULT_LLM_QUEUE_TIMEOUT_SECONDS = 60.0

_sem_lock = threading.Lock()
_sem: Optional[threading.Semaphore] = None
_sem_limit: Optional[int] = None


def get_ollama_host() -> str:
    return (os.environ.get("OLLAMA_HOST") or DEFAULT_OLLAMA_HOST).strip()


def get_ollama_model(default: str = DEFAULT_OLLAMA_MODEL) -> str:
    return (os.environ.get("OLLAMA_MODEL") or default).strip()


def get_llm_max_concurrency() -> int:
    raw = os.environ.get("LLM_MAX_CONCURRENCY", str(DEFAULT_LLM_MAX_CONCURRENCY))
    try:
        return max(1, int(raw))
    except ValueError:
        return DEFAULT_LLM_MAX_CONCURRENCY


def get_llm_queue_timeout() -> float:
    raw = os.environ.get("LLM_QUEUE_TIMEOUT_SECONDS", str(DEFAULT_LLM_QUEUE_TIMEOUT_SECONDS))
    try:
        return max(1.0, float(raw))
    except ValueError:
        return DEFAULT_LLM_QUEUE_TIMEOUT_SECONDS


def _get_semaphore() -> threading.Semaphore:
    global _sem, _sem_limit
    limit = get_llm_max_concurrency()
    with _sem_lock:
        if _sem is None or _sem_limit != limit:
            _sem = threading.Semaphore(limit)
            _sem_limit = limit
        return _sem


@contextmanager
def llm_slot() -> Iterator[None]:
    """Acquire a concurrency slot for an LLM call (blocks up to LLM_QUEUE_TIMEOUT_SECONDS)."""
    sem = _get_semaphore()
    timeout = get_llm_queue_timeout()
    if not sem.acquire(timeout=timeout):
        raise TimeoutError(
            f"LLM concurrency limit reached (LLM_MAX_CONCURRENCY={get_llm_max_concurrency()}). "
            "Try again shortly."
        )
    try:
        yield
    finally:
        sem.release()


def get_client(*, timeout: float = 30.0):
    if ollama is None:
        raise RuntimeError(
            "Python package 'ollama' is not installed. Run: pip install ollama"
        )
    return ollama.Client(host=get_ollama_host(), timeout=timeout)


def chat_ollama(
    *,
    model: str,
    messages: List[Dict[str, str]],
    options: Dict[str, Any],
    timeout: float = 30.0,
    response_format: str | None = None,
) -> Any:
    """Call Ollama chat under the shared concurrency semaphore."""
    with llm_slot():
        client = get_client(timeout=timeout)
        kwargs: Dict[str, Any] = {
            "model": model,
            "messages": messages,
            "options": options,
        }
        if response_format:
            kwargs["format"] = response_format
        return client.chat(**kwargs)
