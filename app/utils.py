import os
import re
import uuid
from typing import Tuple

from app.settings import AUDIO_OUT_DIR, settings


SAFE_NAME_REGEX = re.compile(r"[^a-zA-Z0-9_-]+")


def sanitize_name(name: str) -> str:
    return SAFE_NAME_REGEX.sub("_", name.strip()).strip("_")


def new_audio_file(stem: str = "out", ext: str = ".wav") -> Tuple[str, str]:
    unique = f"{stem}_{uuid.uuid4().hex}{ext}"
    full_path = os.path.join(AUDIO_OUT_DIR, unique)
    rel_url = f"/static/audio/{unique}"
    return full_path, rel_url


def to_public_url(rel_url: str) -> str:
    base = settings.base_url or ""
    if base.endswith("/"):
        base = base[:-1]
    return f"{base}{rel_url}"