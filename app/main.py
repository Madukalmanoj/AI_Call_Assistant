from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles

from app.twilio_routes import router as twilio_router
from app.voice_routes import router as voice_router
from app.tts_routes import router as tts_router
from app.calls_routes import router as calls_router
from app.settings import settings, STATIC_DIR
from app.db import init_db

app = FastAPI(title=settings.app_name)

# ----------------------
# CORS
# ----------------------
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# ----------------------
# Static files
# ----------------------
app.mount("/static", StaticFiles(directory=STATIC_DIR), name="static")

# ----------------------
# Routers
# ----------------------
app.include_router(twilio_router, prefix="/twilio", tags=["twilio"])
app.include_router(voice_router, prefix="/api/voices", tags=["voices"])
app.include_router(tts_router, prefix="/api/tts", tags=["tts"])
app.include_router(calls_router, prefix="/api/calls", tags=["calls"])

# ----------------------
# DB
# ----------------------
init_db()

# ----------------------
# Health endpoint (fast)
# ----------------------
@app.get("/healthz")
def health():
    return {"ok": True}

# ----------------------
# Lazy-load Gradio UI (fast startup)
# ----------------------
blocks = None
def get_gradio_blocks():
    global blocks
    if blocks is None:
        from app.ui import build_ui
        blocks = build_ui()
    return blocks

@app.on_event("startup")
def mount_gradio():
    import gradio as gr
    gr.mount_gradio_app(app, get_gradio_blocks(), path="/ui")  # mount at /ui, not /
