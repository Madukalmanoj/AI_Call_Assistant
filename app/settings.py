import os
from dataclasses import dataclass
from dotenv import load_dotenv

load_dotenv()


def get_env(name: str, default: str | None = None) -> str | None:
    value = os.getenv(name)
    if value is not None and value.strip() != "":
        return value
    return default


@dataclass
class Settings:
    app_name: str = get_env("APP_NAME", "MultiVoiceCallAssistant") or "MultiVoiceCallAssistant"
    data_dir: str = get_env("DATA_DIR", "./data") or "./data"

    # Twilio
    twilio_account_sid: str | None = get_env("TWILIO_ACCOUNT_SID")
    twilio_auth_token: str | None = get_env("TWILIO_AUTH_TOKEN")
    twilio_phone_number: str | None = get_env("TWILIO_PHONE_NUMBER")

    # Public base URL for Twilio to fetch TwiML and media
    base_url: str | None = get_env("BASE_URL")


settings = Settings()

# Prepare directories
STATIC_DIR = os.path.join(settings.data_dir, "static")
VOICES_DIR = os.path.join(settings.data_dir, "voices")
AUDIO_OUT_DIR = os.path.join(STATIC_DIR, "audio")
TRANSCRIPTS_DIR = os.path.join(settings.data_dir, "transcripts")
DB_PATH = os.path.join(settings.data_dir, "app.db")

for d in [settings.data_dir, STATIC_DIR, VOICES_DIR, AUDIO_OUT_DIR, TRANSCRIPTS_DIR]:
    os.makedirs(d, exist_ok=True)