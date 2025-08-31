from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
import gradio as gr

from app.settings import settings, STATIC_DIR
from app.twilio_routes import router as twilio_router
from app.voice_routes import router as voice_router
from app.tts_routes import router as tts_router
from app.calls_routes import router as calls_router
from app.db import init_db

# Initialize FastAPI
app = FastAPI(title=settings.app_name)

# CORS
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Static files
app.mount("/static", StaticFiles(directory=STATIC_DIR), name="static")

# Routers
app.include_router(twilio_router, prefix="/twilio", tags=["twilio"])
app.include_router(voice_router, prefix="/api/voices", tags=["voices"])
app.include_router(tts_router, prefix="/api/tts", tags=["tts"])
app.include_router(calls_router, prefix="/api/calls", tags=["calls"])

# Initialize DB
init_db()

# Lazy Gradio UI
blocks = None  # Do not build UI yet

def get_gradio_blocks():
    global blocks
    if blocks is None:
        from app.ui import build_ui
        blocks = build_ui()  # load UI + models only when first request
    return blocks

# Mount Gradio lazily
@app.on_event("startup")
def mount_gradio():
    app_gr = gr.mount_gradio_app(app, get_gradio_blocks(), path="/")
