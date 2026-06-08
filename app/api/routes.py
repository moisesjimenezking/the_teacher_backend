"""FastAPI routes — WebSocket for chat, HTTP for health/transcription."""

import json
from fastapi import APIRouter, WebSocket, WebSocketDisconnect

from app.services.transcription import get_transcription_service
from app.services.tts import get_tts_service
from app.agents.english_teacher import get_english_teacher

URL_PREFIX = "/api/v1/teacher"

# ── Sub-routers (like Flask blueprints) ──

health_router = APIRouter(prefix="/health", tags=["health"])
transcribe_router = APIRouter(prefix="/transcribe", tags=["transcribe"])
chat_router = APIRouter(tags=["chat"])

_histories: dict[str, list[dict]] = {}


@health_router.get("/")
async def health():
    return {"status": "ok", "app": "Conversator"}


@transcribe_router.post("/")
async def transcribe_audio(payload: dict):
    base64_audio = payload.get("audio", "")
    text = get_transcription_service().transcribe_base64(base64_audio)
    return {"text": text}


@chat_router.websocket("/ws")
async def websocket_chat(websocket: WebSocket):
    await websocket.accept()

    conn_id = str(id(websocket))
    _histories[conn_id] = []

    transcription = get_transcription_service()
    tts = get_tts_service()
    teacher = get_english_teacher()

    try:
        while True:
            raw = await websocket.receive_text()

            try:
                data = json.loads(raw)
            except json.JSONDecodeError:
                data = {"content": raw, "type": "text"}

            msg_type = data.get("type", "text")
            content = data.get("content", "")

            user_content = content
            is_audio = msg_type == "audio"

            # ── Transcribe audio ──
            if is_audio:
                try:
                    user_content = transcription.transcribe_base64(content) or "[No se pudo transcribir]"
                except Exception:
                    user_content = "[Error transcribiendo]"
                agent_message = f"[Audio transcrito: {user_content}]"
            else:
                agent_message = user_content

            # Save user msg to history
            _histories[conn_id].append({"sender": "user", "content": user_content})

            # Get teacher response
            resp = await teacher.get_response(agent_message, _histories[conn_id])

            english_text = resp.get("english", "")
            pronunciation_text = resp.get("pronunciation", "")

            # Generate pronunciation audio
            pronunciation_audio_b64 = None
            if english_text:
                try:
                    pronunciation_audio_b64 = await tts.text_to_audio_base64(english_text)
                except Exception:
                    pass

            # Build display parts
            parts = []
            if resp.get("spanish"):
                parts.append(("spanish", resp["spanish"]))
            if resp.get("example") and resp["example"] != english_text:
                parts.append(("example", f"📝 {resp['example']}"))
            if resp.get("explanation"):
                parts.append(("explanation", f"📖 {resp['explanation']}"))
            if resp.get("tip"):
                parts.append(("tip", f"💡 {resp['tip']}"))

            content_text = "\n\n".join(p[1] for p in parts) if parts else resp.get("content", str(resp))

            # Build the full assistant message for history (includes english phrase taught)
            full_assistant_msg = content_text
            if english_text:
                full_assistant_msg += f"\n[Frase enseñada: {english_text}]"

            # Save assistant msg with full context
            _histories[conn_id].append({
                "sender": "assistant",
                "content": full_assistant_msg,
            })

            await websocket.send_json({
                "type": resp.get("type", "lesson"),
                "sender": "assistant",
                "content": content_text,
                "english": english_text,
                "pronunciation": pronunciation_text,
                "pronunciationAudio": pronunciation_audio_b64,
                "example": resp.get("example", ""),
                "spanish": resp.get("spanish", ""),
                "tip": resp.get("tip", ""),
                "correction": resp.get("correction", ""),
                "explanation": resp.get("explanation", ""),
                "original": resp.get("original", ""),
                "expected": resp.get("expected", ""),
                "feedback": resp.get("feedback", ""),
            })

    except WebSocketDisconnect:
        _histories.pop(conn_id, None)
    except Exception:
        _histories.pop(conn_id, None)


# ── Main router with versioned prefix ──

router = APIRouter(prefix=URL_PREFIX)
router.include_router(health_router)
router.include_router(transcribe_router)
router.include_router(chat_router)
