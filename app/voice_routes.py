import os
from typing import List

from fastapi import APIRouter, UploadFile, File, Form, HTTPException
from fastapi.responses import FileResponse

from app.settings import VOICES_DIR
from app.utils import sanitize_name
from app.db import upsert_voice, list_voices, get_voice, delete_voice as db_delete_voice
from app.tts_engine import synthesize_to_wav

router = APIRouter()


@router.post("/train")
async def train_voice(name: str = Form(...), sample: UploadFile = File(...)):
    clean = sanitize_name(name)
    if not clean:
        raise HTTPException(status_code=400, detail="Invalid voice name")
    voice_dir = os.path.join(VOICES_DIR, clean)
    os.makedirs(voice_dir, exist_ok=True)
    ref_wav_path = os.path.join(voice_dir, "reference.wav")

    data = await sample.read()
    with open(ref_wav_path, "wb") as f:
        f.write(data)

    upsert_voice(clean, ref_wav_path)
    return {"status": "ok", "name": clean}


@router.get("")
async def voices() -> List[dict]:
    return list_voices()


@router.get("/{name}/preview")
async def preview_voice(name: str):
    v = get_voice(name)
    if not v:
        raise HTTPException(status_code=404, detail="Voice not found")
    _, rel = synthesize_to_wav("This is a preview of the cloned voice.", v["ref_wav_path"], language="en")
    return {"audio_url": rel}


@router.delete("/{name}")
async def delete_voice(name: str):
    v = get_voice(name)
    if not v:
        raise HTTPException(status_code=404, detail="Voice not found")
    # Remove from DB
    db_delete_voice(name)
    # Remove files
    voice_dir = os.path.join(VOICES_DIR, name)
    try:
        if os.path.isdir(voice_dir):
            for root, _, files in os.walk(voice_dir, topdown=False):
                for file in files:
                    os.remove(os.path.join(root, file))
            os.rmdir(voice_dir)
    except Exception:
        # Ignore FS errors
        pass
    return {"status": "ok"}