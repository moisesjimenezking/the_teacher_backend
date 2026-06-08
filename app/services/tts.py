"""Text-to-Speech service using edge-tts (Microsoft)."""

import asyncio
import base64
import tempfile
from pathlib import Path


class TTSService:
    """Converts English text to speech audio (mp3 base64)."""

    def __init__(self, voice: str = "en-US-GuyNeural"):
        self.voice = voice
        # Slow rate: -40% speed (edge-tts uses percentage like -40%)
        self.slow_rate = "-40%"

    async def text_to_audio_base64(self, text: str, slow: bool = False) -> str:
        """Convert text to speech and return base64 encoded mp3.
        
        Args:
            text: English text to speak
            slow: If True, speak at ~60% speed for learning
        """
        import edge_tts

        with tempfile.NamedTemporaryFile(suffix=".mp3", delete=False) as tmp:
            tmp_path = tmp.name

        rate = self.slow_rate if slow else "+0%"
        communicate = edge_tts.Communicate(text, self.voice, rate=rate)
        await communicate.save(tmp_path)

        with open(tmp_path, "rb") as f:
            audio_bytes = f.read()

        Path(tmp_path).unlink(missing_ok=True)

        return base64.b64encode(audio_bytes).decode("utf-8")


singleton: TTSService | None = None


def get_tts_service() -> TTSService:
    global singleton
    if singleton is None:
        singleton = TTSService()
    return singleton
