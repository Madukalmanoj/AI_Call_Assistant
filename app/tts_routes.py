from fastapi import APIRouter, HTTPException

from app.db import get_voice
from app.tts_engine import synthesize_to_wav

router = APIRouter()


@router.post("")
async def tts(text: str, voice_name: str):
    voice = get_voice(voice_name)
    if not voice:
        raise HTTPException(status_code=404, detail="Voice not found")
    _, rel_url = synthesize_to_wav(text, voice["ref_wav_path"], language="en")
    return {"audio_url": rel_url}