## MultiVoiceCallAssistant

Production-ready AI + Voice application for voice cloning, text-to-speech, and live phone calls via Twilio.

### Features
- Upload a 30–60s sample to create a named voice
- Generate speech in any saved voice
- Place real phone calls where the assistant talks in your cloned voice
- Conversation logs and post-call summaries

### Tech Stack
- UI: Gradio (deployable on Hugging Face Spaces)
- Server: FastAPI (mounted inside the same process)
- Voice cloning TTS: Coqui TTS (XTTS v2, reference-audio conditioned)
- LLM: TinyLlama (Hugging Face Transformers)
- DB: SQLite
- Calls: Twilio (webhooks + REST API)

### Quickstart (Local)
1. Create environment and install core dependencies
```bash
python3 -m venv .venv && source .venv/bin/activate
pip install -r requirements.txt
```
2. OPTIONAL: Install TTS and LLM for full functionality
```bash
pip install TTS==0.21.2 transformers accelerate
# CPU-only torch wheel (optional, required by TTS/transformers)
pip install --index-url https://download.pytorch.org/whl/cpu torch torchvision torchaudio
```
3. Copy env
```bash
cp .env.example .env
```
Fill in `TWILIO_*` and `BASE_URL` (must be public HTTPS for Twilio).

4. Run the app
```bash
uvicorn app.main:app --host 0.0.0.0 --port 7860
```
Open http://localhost:7860

### Deploy to Hugging Face Spaces (Gradio)
- Create a new Space (Gradio, Python)
- Push this repo
- Ensure secrets are set in the Space settings: `TWILIO_ACCOUNT_SID`, `TWILIO_AUTH_TOKEN`, `TWILIO_PHONE_NUMBER`, `BASE_URL`
- Add `TTS`, `transformers`, and `torch` to the Space packages if you need TTS/LLM (see optional section above)
- The app will serve UI at `/` and Twilio webhooks at `/twilio/*`

### Deploy to Render
- Create a new Web Service from this repo
- Build command: `pip install -r requirements.txt && pip install TTS==0.21.2 transformers accelerate && pip install --index-url https://download.pytorch.org/whl/cpu torch`
- Start command: `uvicorn app.main:app --host 0.0.0.0 --port $PORT`
- Add environment variables from `.env.example`

### Notes
- XTTS v2 uses reference-audio conditioning. "Train" simply stores the uploaded audio and prepares metadata. No heavy fine-tuning is required.
- Twilio requires public HTTPS URLs. Set `BASE_URL` so Twilio can fetch TwiML and audio files.

### License
MIT