import importlib
import threading
from typing import Tuple

from app.settings import settings
from app.utils import new_audio_file


_tts_lock = threading.Lock()
_tts_model = None


def _load_tts():
    global _tts_model
    if _tts_model is None:
        with _tts_lock:
            if _tts_model is None:
                TTS = importlib.import_module("TTS.api").TTS
                _tts_model = TTS(model_name="tts_models/multilingual/multi-dataset/xtts_v2")
    return _tts_model


def synthesize_to_wav(text: str, ref_wav_path: str, language: str = "en") -> Tuple[str, str]:
    tts = _load_tts()
    out_path, rel_url = new_audio_file(stem="tts")
    tts.tts_to_file(text=text, file_path=out_path, speaker_wav=ref_wav_path, language=language)
    return out_path, rel_url