import gradio as gr
import os
import shutil
from typing import List

from app.db import list_voices as db_list_voices, list_calls, upsert_voice, get_voice, delete_voice as db_delete_voice
from app.settings import settings, VOICES_DIR
from app.tts_engine import synthesize_to_wav
from app.utils import sanitize_name
from twilio.rest import Client


def build_ui():
    with gr.Blocks(title=settings.app_name) as demo:
        gr.Markdown(f"# {settings.app_name}")

        with gr.Tab("Manage Voices"):
            with gr.Row():
                with gr.Column():
                    name_in = gr.Textbox(label="Voice Name", placeholder="e.g., Manoj")
                    sample_in = gr.Audio(label="Reference Sample (30–60s .wav)", type="filepath")
                    train_btn = gr.Button("Train Voice")
                    train_status = gr.Markdown(visible=False)
                with gr.Column():
                    refresh_btn = gr.Button("Refresh Voices")
                    voices_df = gr.Dataframe(headers=["name", "ref_wav_path", "created_at"], interactive=False)
                    sel_voice = gr.Dropdown(label="Select Voice", choices=[], interactive=True)
                    prev_btn = gr.Button("Preview")
                    del_btn = gr.Button("Delete")
                    prev_audio = gr.Audio(label="Preview", type="filepath")

            def do_train(name, sample_path):
                if not name or not sample_path:
                    return gr.update(visible=True, value="Please provide name and sample."), None
                clean = sanitize_name(name)
                vdir = os.path.join(VOICES_DIR, clean)
                os.makedirs(vdir, exist_ok=True)
                ref_path = os.path.join(vdir, "reference.wav")
                shutil.copy(sample_path, ref_path)
                upsert_voice(clean, ref_path)
                return gr.update(visible=True, value="Voice saved."), True

            def do_refresh():
                items = db_list_voices()
                names = [v["name"] for v in items]
                return items, gr.update(choices=list(names))

            def do_preview(name):
                v = get_voice(name)
                if not v:
                    return None
                out_path, _ = synthesize_to_wav("This is a preview of the cloned voice.", v["ref_wav_path"], language="en")
                return out_path

            def do_delete(name):
                v = get_voice(name)
                if v:
                    db_delete_voice(name)
                    vdir = os.path.join(VOICES_DIR, name)
                    try:
                        shutil.rmtree(vdir)
                    except Exception:
                        pass
                items, names_update = do_refresh()
                return names_update, items

            train_btn.click(do_train, inputs=[name_in, sample_in], outputs=[train_status, refresh_btn])
            refresh_btn.click(do_refresh, None, [voices_df, sel_voice])
            prev_btn.click(do_preview, inputs=[sel_voice], outputs=[prev_audio])
            del_btn.click(do_delete, inputs=[sel_voice], outputs=[sel_voice, voices_df])
            demo.load(do_refresh, None, [voices_df, sel_voice])

        with gr.Tab("Text to Voice"):
            voice_dd = gr.Dropdown(label="Select Voice", choices=[], interactive=True)
            text_in = gr.Textbox(label="Text", lines=4)
            gen_btn = gr.Button("Generate Speech")
            audio_out = gr.Audio(label="Output", type="filepath")

            def load_voice_names():
                items = db_list_voices()
                names = [v["name"] for v in items]
                return gr.update(choices=names)

            def do_tts(text, voice_name):
                v = get_voice(voice_name)
                if not v:
                    return None
                out_path, _ = synthesize_to_wav(text, v["ref_wav_path"], language="en")
                return out_path

            demo.load(load_voice_names, None, voice_dd)
            gen_btn.click(do_tts, inputs=[text_in, voice_dd], outputs=[audio_out])

        with gr.Tab("AI Call"):
            call_voice_dd = gr.Dropdown(label="Select Voice", choices=[], interactive=True)
            phone_in = gr.Textbox(label="Phone number (E.164)", placeholder="+91...")
            start_msg = gr.Textbox(label="Starting message (optional)")
            call_btn = gr.Button("Start Call")
            call_status = gr.Markdown(visible=False)

            def load_voice_names2():
                items = db_list_voices()
                names = [v["name"] for v in items]
                return gr.update(choices=names)

            def do_call(voice_name, to_number, initial_message):
                client = Client(settings.twilio_account_sid, settings.twilio_auth_token)
                call_id = __import__("uuid").uuid4().hex
                # Insert call row
                from app.db import create_call
                create_call(call_id, to_number, voice_name, initial_message)
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
                return gr.update(visible=True, value=f"Dialing... Call ID: {call_id}")

            demo.load(load_voice_names2, None, call_voice_dd)
            call_btn.click(do_call, inputs=[call_voice_dd, phone_in, start_msg], outputs=[call_status])

        with gr.Tab("History"):
            history_df = gr.Dataframe(headers=["id", "to_number", "voice_name", "status", "summary", "created_at"], interactive=False)
            refresh_hist_btn = gr.Button("Refresh History")
            dl_hint = gr.Markdown(value="Select a call ID above. Download transcript: /api/calls/<CALL_ID>/transcript.txt")

            def load_history():
                items = list_calls()
                return items

            demo.load(load_history, None, history_df)
            refresh_hist_btn.click(load_history, None, history_df)

    return demo