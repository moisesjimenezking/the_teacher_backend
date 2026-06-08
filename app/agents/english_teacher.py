"""English teacher LLM agent.
Context: User is a Spanish speaker who is BEGINNER level in English.
- If user writes in SPANISH → teach/explain in Spanish, give English examples
- If user writes in ENGLISH → correct grammar/spelling mistakes
- If user sends AUDIO → evaluate pronunciation
"""

import json
import re

from app.core.config import settings

SYSTEM_PROMPT = """Eres "Conversator", un profesor de inglés amigable y paciente.

CONTEXTO IMPORTANTE:
- Tu estudiante es hispanohablante
- Su nivel de inglés es PRINCIPIANTE (o muy bajo)
- Si pregunta en español, responde en español (profesor educativo, no traductor)
- Si te escribe en inglés con errores, corrígelos con amabilidad
- Si te envía audio, evalúa la pronunciación

REGLAS SEGÚTIPO DE ENTRADA:

1. USUARIO ESCRIBE EN ESPAÑOL (preguntando o hablando):
   - Respóndele EN ESPAÑOL como un profesor educativo
   - Enséñale frases útiles en inglés relacionadas con lo que preguntó
   - Explica cosas simples, no asumas que sabe inglés
   - Formato:
     {"type": "lesson", "spanish": "respuesta educativa en español", "english": "frase útil en inglés", "pronunciation": "fonética hispana", "example": "ejemplo extra si aplica"}

2. USUARIO ESCRIBE EN INGLÉS (posibles errores):
   - SI hay errores: corrige con amabilidad
     {"type": "correction", "spanish": "explicación del error en español", "original": "parte incorrecta", "corrected": "corrección", "pronunciation": "fonética", "english": "frase corregida completa", "explanation": "regla gramatical simple en español"}
   - SI está perfecto: felicita y enseña algo nuevo
     {"type": "lesson", "spanish": "felicidad + enseñanza nueva", "english": "frase nueva", "pronunciation": "fonética"}

3. USUARIO ENVÍA AUDIO (texto viene como "[Audio transcrito: ...]"):
   - Evalúa pronunciación
   - Formato:
     {"type": "pronunciation", "spanish": "feedback en español", "original": "transcripción", "expected": "lo que debería decir", "pronunciation": "fonética", "english": "frase correcta", "feedback": "tips de pronunciación en español"}

REGLAS CRÍTICAS:
- NUNCA omitas "english" y "pronunciation" — son OBLIGATORIOS
- NUNCA respondas fuera de JSON
- La pronunciación debe ser fonética para hispanohablantes: "je-lou", "mai neim is..."
- Sé BREVE en las explicaciones (2-3 oraciones máximo)
- Sé CALIDO, PACIENTE y MOTIVADOR — no seas condescendiente
- Recuerda: el usuario NO habla bien inglés, explica todo simple
- Solo corrige lo que el usuario REALMENTE escribió en su último mensaje
- Si el mensaje es muy corto (1-2 palabras), no corrijas — solo alienta"""


class EnglishTeacherAgent:
    def __init__(self):
        self._client = None

    def _get_client(self):
        if self._client is None:
            from openai import OpenAI
            api_key = settings.OPENROUTER_API_KEY or settings.OPENAI_API_KEY
            base_url = "https://openrouter.ai/api/v1" if settings.LLM_PROVIDER == "openrouter" else None
            self._client = OpenAI(api_key=api_key, base_url=base_url)
        return self._client

    def _get_model(self) -> str:
        model = settings.LLM_MODEL
        return model[len("openrouter/"):] if model.startswith("openrouter/") else model

    def _is_spanish(self, text: str) -> bool:
        """Detect if text is primarily Spanish."""
        text_lower = text.lower().strip()
        # Common Spanish words/phrases
        spanish_indicators = [
            'hola', 'buenos', 'buenas', 'quiero', 'cómo', 'qué', 'por favor',
            'gracias', 'no sé', 'puedes', 'ayuda', 'enseñar', 'aprender',
            'ingles', 'inglés', 'significa', 'traduce', 'pronuncia',
            'estoy', 'tengo', 'hay', 'favor', 'dime', 'explicar',
            'mi nombre', 'presentarme', 'llamo', 'donde', 'cuando',
            'porque', 'también', 'pero', 'muy', 'bien', 'mal',
        ]
        for word in spanish_indicators:
            if word in text_lower:
                return True

        # If it contains ñ, accents common in Spanish
        if any(c in text_lower for c in 'ñáéíóúü'):
            return True

        # If user explicitly writes in Spanish pattern
        spanish_words = ['el', 'la', 'los', 'las', 'un', 'una', 'es', 'son',
                         'estoy', 'está', 'quiere', 'necesito', 'me gustaría']
        words = text_lower.split()
        spanish_count = sum(1 for w in words if w in spanish_words)
        if spanish_count >= 2:
            return True

        return False

    def _extract_taught_phrase(self, conversation_history: list[dict]) -> str:
        """Extract the English phrase the teacher last taught."""
        for msg in reversed(conversation_history):
            if msg.get("sender") == "assistant":
                content = msg.get("content", "")
                # Look for explicit [Frase enseñada: ...] tag from backend
                tag_match = re.search(r'\[Frase enseñada:\s*([^\]]+)\]', content)
                if tag_match:
                    return tag_match.group(1).strip()
                # Fallback: quoted phrases
                matches = re.findall(r'"([^"]+)"', content)
                if matches:
                    return matches[-1]
                break
        return ""

    def _build_context(self, user_message: str, conversation_history: list[dict]) -> list[dict]:
        """Build messages with clear conversation context."""
        messages = [{"role": "system", "content": SYSTEM_PROMPT}]

        # Build recent conversation history
        context_lines = []
        for msg in conversation_history[-6:]:
            role = "Usuario" if msg.get("sender") == "user" else "Profesor"
            content = msg.get("content", "")
            if content:
                context_lines.append(f"{role}: {content}")

        if context_lines:
            ctx = "HISTORIAL DE CONVERSACIÓN:\n" + "\n".join(context_lines)
            messages.append({"role": "system", "content": ctx})

        # For audio: include what was taught for comparison
        if user_message.startswith("[Audio transcrito:"):
            taught = self._extract_taught_phrase(conversation_history)
            hint = f"\n\nIMPORTANTE: En tu última respuesta enseñaste la frase: \"{taught}\". Compara el audio del usuario CON ESTA FRASE." if taught else ""
            messages.append({"role": "user", "content": f"AUDIO DEL USUARIO: {user_message}{hint}"})
        else:
            lang = "ESPAÑOL" if self._is_spanish(user_message) else "INGLÉS"
            messages.append({"role": "user", "content": f"MENSAJE ({lang}): {user_message}"})

        return messages

    async def get_response(self, user_message: str, conversation_history: list[dict]) -> dict:
        messages = self._build_context(user_message, conversation_history)

        try:
            client = self._get_client()
            response = client.chat.completions.create(
                model=self._get_model(),
                messages=messages,
                max_tokens=1024,
                temperature=0.7,
            )
            raw = response.choices[0].message.content.strip()

            # Parse JSON
            start = raw.find("{")
            end = raw.rfind("}") + 1
            if start >= 0 and end > start:
                data = json.loads(raw[start:end])
            else:
                data = {"type": "lesson", "spanish": raw}

            # Enforce required fields
            if not data.get("english"):
                data["english"] = "Practice makes perfect."
            if not data.get("pronunciation"):
                data["pronunciation"] = self._generate_phonetic(data["english"])

            # Normalize types
            t = data.get("type", "lesson")
            if t not in ("correction", "pronunciation"):
                data["type"] = "lesson"

            return data

        except Exception as e:
            return {
                "type": "error",
                "spanish": f"Error de conexión. Intenta de nuevo. ({e})",
                "english": "Sorry, connection error. Please try again!",
                "pronunciation": "sori, kəˈnekʃən eror",
            }

    def _generate_phonetic(self, english: str) -> str:
        """Simple English → Spanish phonetic."""
        phonetic_map = {
            'th': 'z', 'sh': 'sh', 'ch': 'ch', 'ph': 'f',
            'ee': 'i', 'oo': 'u', 'ou': 'au', 'ow': 'au',
            'ay': 'ei', 'ai': 'ei', 'wh': 'w', 'wr': 'r', 'kn': 'n',
            'tion': 'shon', 'sion': 'zhon',
        }
        lower = english.lower()
        for eng, ph in sorted(phonetic_map.items(), key=lambda x: -len(x[0])):
            lower = lower.replace(eng, ph)
        return lower


singleton = None


def get_english_teacher() -> EnglishTeacherAgent:
    global singleton
    if singleton is None:
        singleton = EnglishTeacherAgent()
    return singleton
