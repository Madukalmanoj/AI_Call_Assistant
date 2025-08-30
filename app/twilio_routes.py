import uuid
from typing import Optional

from fastapi import APIRouter, Form, Request
from fastapi.responses import Response
from twilio.rest import Client
from twilio.twiml.voice_response import VoiceResponse, Gather

from app.settings import settings
from app.db import create_call, update_call_status, append_transcript, complete_call_with_summary, get_transcript
from app.db import get_voice
from app.tts_engine import synthesize_to_wav
from app.utils import to_public_url
from app.llm_engine import llm

router = APIRouter()


def _twiml_response(xml: str) -> Response:
    return Response(content=xml, media_type="application/xml")


@router.post("/start")
async def start_call(to_number: str = Form(...), voice_name: str = Form(...), initial_message: Optional[str] = Form(None)):
    call_id = uuid.uuid4().hex
    create_call(call_id, to_number, voice_name, initial_message)

    client = Client(settings.twilio_account_sid, settings.twilio_auth_token)

    answer_url = f"{settings.base_url}/twilio/answer?call_id={call_id}"
    status_url = f"{settings.base_url}/twilio/status?call_id={call_id}"

    call = client.calls.create(
        to=to_number,
        from_=settings.twilio_phone_number,
        url=answer_url,
        status_callback=status_url,
        status_callback_event=["completed"],
        method="POST",
    )

    return {"status": "dialing", "call_id": call_id, "sid": call.sid}


@router.api_route("/answer", methods=["GET", "POST"])
async def answer(request: Request):
    call_id = request.query_params.get("call_id")
    if not call_id:
        return _twiml_response(VoiceResponse().to_xml())

    # Look up call and voice
    from app.db import db_cursor
    with db_cursor() as cur:
        cur.execute("SELECT voice_name, initial_message FROM calls WHERE id = ?", (call_id,))
        row = cur.fetchone()
        if row:
            voice_name, initial_message = row[0], row[1]
        else:
            voice_name, initial_message = None, None

    vr = VoiceResponse()

    # If initial message, speak in cloned voice
    voice = get_voice(voice_name) if voice_name else None
    if initial_message and voice:
        out_path, rel_url = synthesize_to_wav(initial_message, voice["ref_wav_path"], language="en")
        append_transcript(call_id, "assistant", initial_message, audio_path=out_path)
        vr.play(to_public_url(rel_url))

    # Gather user speech
    loop_action = f"{settings.base_url}/twilio/loop?call_id={call_id}"
    gather = Gather(input="speech", action=loop_action, method="POST", speechTimeout="auto")
    gather.say("Please speak after the beep.")
    vr.append(gather)

    return _twiml_response(vr.to_xml())


@router.api_route("/loop", methods=["GET", "POST"])
async def loop(request: Request):
    call_id = request.query_params.get("call_id")
    if not call_id:
        return _twiml_response(VoiceResponse().to_xml())

    form = await request.form()
    user_speech = form.get("SpeechResult") or ""
    if user_speech:
        append_transcript(call_id, "user", user_speech)

    # Compose LLM response
    transcript_items = get_transcript(call_id)
    history_text = "\n".join([f"{t['role']}: {t['text']}" for t in transcript_items])
    messages = [
        {"role": "system", "content": "You are a friendly helpful assistant for short phone calls. Keep replies under 15 words."},
        {"role": "user", "content": history_text + ("\nUser:" + user_speech if user_speech else "")},
    ]
    assistant_text = llm.chat(messages)

    # Generate TTS audio with selected voice
    from app.db import db_cursor
    with db_cursor() as cur:
        cur.execute("SELECT voice_name FROM calls WHERE id = ?", (call_id,))
        row = cur.fetchone()
        voice_name = row[0] if row else None

    voice = get_voice(voice_name) if voice_name else None

    vr = VoiceResponse()
    if voice:
        out_path, rel_url = synthesize_to_wav(assistant_text, voice["ref_wav_path"], language="en")
        append_transcript(call_id, "assistant", assistant_text, audio_path=out_path)
        media_url = to_public_url(rel_url)
        vr.play(media_url)
    else:
        vr.say(assistant_text)
        append_transcript(call_id, "assistant", assistant_text)

    loop_action = f"{settings.base_url}/twilio/loop?call_id={call_id}"
    gather = Gather(input="speech", action=loop_action, method="POST", speechTimeout="auto")
    vr.append(gather)
    return _twiml_response(vr.to_xml())


@router.api_route("/status", methods=["POST", "GET"])
async def status(request: Request):
    call_id = request.query_params.get("call_id")
    form = await request.form()
    call_status = form.get("CallStatus") or request.query_params.get("CallStatus")

    if call_id and call_status == "completed":
        # Build summary
        items = get_transcript(call_id)
        transcript_text = "\n".join([f"{t['role']}: {t['text']}" for t in items])
        summary = llm.summarize(transcript_text)
        complete_call_with_summary(call_id, summary)

    return Response(status_code=200)