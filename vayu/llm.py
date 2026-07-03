"""Provider-agnostic LLM wrapper.

Priority: Gemini → OpenAI → local deterministic composer. The demo therefore *always*
answers, with or without cloud credentials, and the active backend is reported to the
UI so provenance is honest. Swap in Vertex/Gemini by just setting GEMINI_API_KEY.
"""
from __future__ import annotations

from . import config


def available() -> str:
    return config.ai_backend()


def complete(prompt: str, system: str = "", *, temperature: float = 0.3) -> tuple[str, str]:
    """Return (text, backend_used). Falls back gracefully on any error."""
    backend = config.ai_backend()
    try:
        if backend == "gemini":
            return _gemini(prompt, system, temperature), "gemini"
        if backend == "openai":
            return _openai(prompt, system, temperature), "openai"
    except Exception as exc:  # noqa: BLE001 — never let the assistant hard-fail
        return _local_note(f"(cloud AI unavailable: {exc}) "), "local"
    return "", "local"


def _gemini(prompt: str, system: str, temperature: float) -> str:
    from google import genai
    from google.genai import types

    client = genai.Client(api_key=config.GEMINI_API_KEY)
    resp = client.models.generate_content(
        model=config.GEMINI_MODEL,
        contents=prompt,
        config=types.GenerateContentConfig(
            system_instruction=system or None,
            temperature=temperature,
        ),
    )
    return (resp.text or "").strip()


def _openai(prompt: str, system: str, temperature: float) -> str:
    from openai import OpenAI

    client = OpenAI(api_key=config.OPENAI_API_KEY)
    resp = client.chat.completions.create(
        model=config.OPENAI_MODEL,
        temperature=temperature,
        messages=[
            {"role": "system", "content": system or "You are a helpful assistant."},
            {"role": "user", "content": prompt},
        ],
    )
    return (resp.choices[0].message.content or "").strip()


def _local_note(note: str) -> str:
    return note
