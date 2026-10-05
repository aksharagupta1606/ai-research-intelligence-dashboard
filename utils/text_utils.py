from __future__ import annotations

import re
from collections.abc import Iterable


def split_authors(value: str | Iterable[str] | None) -> list[str]:
    if not value:
        return []
    if not isinstance(value, str):
        return [str(item).strip() for item in value if str(item).strip()]
    return [item.strip() for item in re.split(r"\s*[,;]\s*", value) if item.strip()]


def clean_filename(value: str) -> str:
    name = value.replace("\\", "/").split("/")[-1]
    name = re.sub(r"[^A-Za-z0-9._-]+", "_", name).strip("._")
    return (name or "research-paper.pdf")[:180]


def split_sentences(text: str) -> list[str]:
    return [
        sentence.strip()
        for sentence in re.split(r"(?<=[.!?])\s+", text.strip())
        if len(sentence.strip()) > 24
    ]