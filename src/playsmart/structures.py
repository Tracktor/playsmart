from __future__ import annotations

import typing


class CacheObject(typing.TypedDict):
    """Struct to store prompt responses for a single hostname."""

    app_fingerprint: str
    generic: dict[str, str]
    contexts: dict[str, dict[str, str]]


class FieldDict(typing.TypedDict):
    """Struct to feed the LLM on how it should parse fields in DOM."""

    name: str
    xpath: str
    type: str
