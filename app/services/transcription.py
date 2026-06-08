"""Audio transcription service using faster-whisper."""

import io
import base64
import tempfile
from pathlib import Path
from pydub import AudioSegment

from faster_whisper import WhisperModel

from app.core.config import settings


class TranscriptionService:
    """Transcribes audio (base64 or bytes) to text using Whisper."""

    def __init__(self):
        self._model = None

    def _load_model(self):
        if self._model is None:
            # Auto-detect CUDA
            try:
                import torch
                if torch.cuda.is_available():
                    device = "cuda"
                    compute_type = "float16"
                else:
                    device = "cpu"
                    compute_type = "int8"
            except ImportError:
                device = "cpu"
                compute_type = "int8"

            self._model = WhisperModel(
                settings.WHISPER_MODEL,
                device=device,
                compute_type=compute_type,
            )
        return self._model

    def transcribe_base64(self, base64_audio: str) -> str:
        """Decode base64 audio (webm/ogg/wav) and transcribe to text."""
        raw = base64.b64decode(base64_audio)
        return self._transcribe_bytes(raw)

    def transcribe_bytes(self, audio_bytes: bytes) -> str:
        """Transcribe raw audio bytes to text."""
        return self._transcribe_bytes(audio_bytes)

    def _transcribe_bytes(self, raw: bytes) -> str:
        """Convert bytes to wav, then transcribe."""
        audio = self._convert_to_wav(raw)
        text = self._run_whisper(audio)
        return text.strip()

    def _convert_to_wav(self, raw: bytes) -> str:
        """Convert raw audio bytes (webm/ogg) to wav temp file."""
        suffix = ".webm"
        if raw[:4] == b'RIFF':
            suffix = ".wav"
        elif raw[:4] == b'OggS':
            suffix = ".ogg"

        with tempfile.NamedTemporaryFile(suffix=suffix, delete=False) as tmp_in:
            tmp_in.write(raw)
            input_path = tmp_in.name

        audio = AudioSegment.from_file(input_path)

        wav_path = input_path.rsplit(".", 1)[0] + ".wav"
        audio.export(wav_path, format="wav")

        Path(input_path).unlink(missing_ok=True)

        return wav_path

    def _run_whisper(self, wav_path: str) -> str:
        """Run Whisper on a wav file."""
        model = self._load_model()
        segments, _ = model.transcribe(wav_path, language="en")

        text_parts = []
        for seg in segments:
            text_parts.append(seg.text)

        Path(wav_path).unlink(missing_ok=True)

        return " ".join(text_parts)


singleton: TranscriptionService | None = None


def get_transcription_service() -> TranscriptionService:
    global singleton
    if singleton is None:
        singleton = TranscriptionService()
    return singleton
