from fastapi import APIRouter, HTTPException
from fastapi.responses import PlainTextResponse

from app.db import list_calls, get_transcript

router = APIRouter()


@router.get("")
async def calls():
    return list_calls()


@router.get("/{call_id}/transcript.txt", response_class=PlainTextResponse)
async def transcript(call_id: str):
    items = get_transcript(call_id)
    if not items:
        raise HTTPException(status_code=404, detail="Not found")
    text = "\n".join([f"{t['role']}: {t['text']}" for t in items])
    return text