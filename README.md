# Conversator Backend

FastAPI + WebSocket chat con Whisper (audio→text) y profesor de inglés con TTS.

## Requisitos

- Python 3.10
- API key de OpenRouter (gratis en https://openrouter.ai/keys)

## Setup (sin Docker, una sola versión de Python)

```bash
# Desde la raíz del proyecto
pyenv local 3.10.20          # usa Python 3.10
python -m venv venv310       # crea venv con 3.10
source venv310/bin/activate  # activa el venv

cd backend
pip install -r requirements.txt
```

## Config

Edita `backend/.env` y pon tu API key:

```env
OPENROUTER_API_KEY=sk-or-v1-tu-key-aqui
LLM_MODEL=anthropic/claude-sonnet-4
```

## Run

```bash
source venv310/bin/activate
cd backend
python -m app.main
```

Servidor en `http://localhost:8080`

## Test rápido

```bash
source venv310/bin/activate
cd backend
python -c "
import asyncio, json
from app.agents.english_teacher import get_english_teacher
async def t():
    r = await get_english_teacher().get_response('Quiero aprender a presentarme', [], 'text')
    print(json.dumps(r, ensure_ascii=False, indent=2))
asyncio.run(t())
"
```

## API

- `GET /api/health` — health check
- `POST /api/transcribe` — transcribe base64 audio `{"audio": "base64..."}`
- `WS /ws` — WebSocket chat (text + audio)

## WebSocket protocol

Enviar:
```json
{"type": "text", "content": "Hello"}
{"type": "audio", "content": "base64encoded_audio"}
```

Recibir:
```json
{"type": "lesson", "spanish": "...", "english": "...", "pronunciation": "..."}
{"type": "voice_response", "audio": "base64mp3", "english": "...", "translation": "..."}
{"type": "system", "content": "[Transcripción: ...]"}
```

## Aceleración GPU (CUDA)

Por defecto el proyecto está configurado para ejecutarse en VPS sin GPU, utilizando Whisper en modo CPU para la transcripción de audio.

```env
WHISPER_DEVICE=cpu
WHISPER_COMPUTE_TYPE=int8
```

Si se ejecuta en un entorno local o servidor con GPU NVIDIA y CUDA disponible, puede aprovechar la aceleración por hardware modificando estas variables:

```env
WHISPER_DEVICE=cuda
WHISPER_COMPUTE_TYPE=float16
```

No se requieren cambios en el código. La aplicación detectará la configuración definida en las variables de entorno y utilizará automáticamente CPU o GPU para el procesamiento de audio.

## Ejecución con GPU NVIDIA (Opcional)

El repositorio incluye el script `run.sh`, diseñado para entornos locales con GPU NVIDIA. Este script:

* Activa automáticamente el entorno virtual.
* Configura las librerías CUDA instaladas mediante los paquetes de Python.
* Verifica la disponibilidad de CUDA y muestra la GPU detectada.
* Inicia la aplicación utilizando la configuración definida en `.env`.

Ejemplo:

```bash
chmod +x run.sh
./run.sh
```

> Nota: Este script fue creado principalmente para facilitar el desarrollo local con aceleración CUDA. En servidores VPS sin GPU puede ejecutarse la aplicación directamente mediante `python -m app.main`.
