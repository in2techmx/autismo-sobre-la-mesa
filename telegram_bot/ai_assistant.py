"""
Motor de Inteligencia y Clasificación Conversacional — "El Autismo Sobre La Mesa"
Integra:
1. Analizador determinista de lenguaje natural en español (para extraer alimento,
   escalera sensorial, textura y estado emocional incluso sin conexión o como pre-filtro).
2. Integración con Google Gemini API (google-genai / REST) enriquecida con el contexto
   del TFM de la Mtra. Maria Cindy Morales Alarcón y el historial reciente del niño.
"""

import json
import os
import re
import urllib.error
import urllib.request
from dataclasses import dataclass
from typing import List, Optional

from database import BitacoraEntry
from knowledge_base import SYSTEM_PROMPT


@dataclass(frozen=True)
class ParsedMessageResult:
    intent: str  # "LOG_ENTRY", "QUESTION", "BOTH"
    food_item: str
    sensory_step: str
    texture_notes: str
    mood_state: str


# Palabras clave deterministas para clasificar la escalera sensorial
STEP_PATTERNS = [
    ("Comió", [r"\bcomi[oó]\b", r"\bse\s+comi[oó]\b", r"\btrag[oó]\b", r"\bcen[oó]\b", r"\bdesayun[oó]\b", r"\balmorz[oó]\b"]),
    ("Probó", [r"\bprob[oó]\b", r"\bmordi[oó]\b", r"\blami[oó]\b", r"\bchup[oó]\b", r"\bmicromordisco\b", r"\bescupi[oó]\b"]),
    ("Acercó a la boca", [r"\bbes[oó]\b", r"\blabios\b", r"\bacerc[oó]\s+a\s+la\s+boca\b"]),
    ("Tocó", [r"\btoc[oó]\b", r"\bagarr[oó]\b", r"\bjug[oó]\s+con\b", r"\baplast[oó]\b", r"\bmanos\b", r"\bdedos?\b"]),
    ("Olió", [r"\boli[oó]\b", r"\bolfate[oó]\b", r"\bacerco\s+a\s+la\s+nariz\b"]),
    ("Toleró presencia", [r"\btoler[oó]\b", r"\ben\s+el\s+plato\b", r"\ben\s+la\s+mesa\b", r"\bmir[oó]\b"]),
    ("Rechazó", [r"\brechaz[oó]\b", r"\bno\s+quiso\b", r"\barcada\b", r"\bllor[oó]\b", r"\bavent[oó]\b", r"\btir[oó]\b"]),
]

MOOD_PATTERNS = [
    ("En calma", [r"\btranquil[oa]\b", r"\bcalm[ao]\b", r"\bfeliz\b", r"\bcontent[oa]\b", r"\bbien\b", r"\brelajad[oa]\b"]),
    ("Curioso", [r"\bcurios[oa]\b", r"\binteresad[oa]\b", r"\bjuguet[oó]n\b", r"\banimad[oa]\b"]),
    ("Ansioso", [r"\bansios[oa]\b", r"\bnervios[oa]\b", r"\binquiet[oa]\b", r"\bmiedo\b", r"\basustad[oa]\b"]),
    ("Sobrecargado", [r"\bsobrecargad[oa]\b", r"\bcrisis\b", r"\bllorando\b", r"\birritable\b", r"\bestresad[oa]\b", r"\barcadas?\b"]),
]

TEXTURE_KEYWORDS = [
    "crujiente", "blando", "suave", "puré", "pure", "vapor", "al vapor",
    "frito", "horneado", "crudo", "cocido", "rallado", "picado", "trozos",
    "papilla", "líquido", "liquido", "fibroso", "gelatinoso", "tibio", "frío", "caliente"
]

COMMON_FOODS = [
    "brócoli", "brocoli", "zanahoria", "pollo", "manzana", "plátano", "platano",
    "fresa", "arroz", "pasta", "espagueti", "fideos", "pan", "galleta", "galletas",
    "yogur", "yogurt", "leche", "queso", "huevo", "pescado", "atún", "atun",
    "carne", "papa", "patata", "papas", "nuggets", "sopa", "caldo", "lentejas",
    "frijoles", "aguacate", "tomate", "pepino", "uvas", "naranja", "mandarina",
    "pera", "sandía", "sandia", "melón", "melon", " calabaza", "calabacín",
    "avena", "cereal", "tortilla", "jamón", "jamon", "salchicha"
]


def parse_user_message(text: str) -> ParsedMessageResult:
    """
    Analiza determinísticamente un mensaje del usuario para detectar si contiene
    un registro de bitácora, una pregunta o ambos, y extrae sus metadatos.
    """
    clean = text.strip()
    lower = clean.lower()

    is_question = "?" in clean or "¿" in clean or bool(
        re.search(
            r"\b(por\s+qu[eé]|c[oó]mo|cu[aá]ndo|qu[eé]\s+hago|qu[eé]\s+puedo|ayuda|consejo|duda|recomiendas)\b",
            lower,
        )
    )

    detected_step = ""
    for step_label, patterns in STEP_PATTERNS:
        if any(re.search(p, lower) for p in patterns):
            detected_step = step_label
            break

    has_log_indicator = bool(detected_step) or bool(
        re.search(r"\b(hoy|ayer|desayuno|comida|cena|merienda|bit[aá]cora|registro)\b", lower)
    )

    # Extraer alimento
    detected_food = ""
    for food in COMMON_FOODS:
        if re.search(rf"\b{re.escape(food.strip())}\b", lower):
            detected_food = food.strip().capitalize()
            break

    if not detected_food and has_log_indicator:
        # Intentar capturar sustantivo después de verbos clave
        m = re.search(
            r"(?:comi[oó]|prob[oó]|toc[oó]|oli[oó]|toler[oó]|rechaz[oó]|pusimos|dimos)\s+(?:un\s+poco\s+de\s+|una?\s+|el\s+|la\s+)?([a-záéíóúñ]+)",
            lower,
        )
        if m:
            candidate = m.group(1)
            if candidate not in {"un", "una", "el", "la", "lo", "muy", "bien", "mal", "hoy", "ayer", "todo", "nada"}:
                detected_food = candidate.capitalize()

    if not detected_food:
        detected_food = "Registro general"

    if not detected_step:
        detected_step = "Observación general"

    # Extraer textura
    textures = [t for t in TEXTURE_KEYWORDS if re.search(rf"\b{re.escape(t)}\b", lower)]
    texture_str = ", ".join(dict.fromkeys(textures)).capitalize() if textures else "Estándar"

    # Extraer estado emocional
    detected_mood = "No especificado"
    for mood_label, patterns in MOOD_PATTERNS:
        if any(re.search(p, lower) for p in patterns):
            detected_mood = mood_label
            break

    if has_log_indicator and is_question:
        intent = "BOTH"
    elif has_log_indicator:
        intent = "LOG_ENTRY"
    else:
        intent = "QUESTION"

    return ParsedMessageResult(
        intent=intent,
        food_item=detected_food,
        sensory_step=detected_step,
        texture_notes=texture_str,
        mood_state=detected_mood,
    )


class TeaAdvisorService:
    """
    Servicio de asesoría clínica y acompañamiento con soporte para Gemini API
    y motor de respaldo basado en evidencia del TFM (100% funcional con o sin API Key).
    """

    def __init__(self, gemini_api_key: Optional[str] = None, model_name: str = "gemini-2.5-flash") -> None:
        self.api_key = gemini_api_key or os.environ.get("GEMINI_API_KEY", "")
        self.model_name = model_name

    def generate_response(
        self,
        user_message: str,
        parsed: ParsedMessageResult,
        recent_entries: List[BitacoraEntry],
        child_name: str = "tu peque",
    ) -> str:
        if self.api_key:
            try:
                return self._call_gemini_api(user_message, parsed, recent_entries, child_name)
            except Exception:
                # Si la API falla o no hay red, responde de forma transparente con el motor clínico local del TFM
                pass

        return self._generate_local_tfm_response(user_message, parsed, recent_entries, child_name)

    def _call_gemini_api(
        self,
        user_message: str,
        parsed: ParsedMessageResult,
        recent_entries: List[BitacoraEntry],
        child_name: str,
    ) -> str:
        history_summary = "\n".join(
            [
                f"- [{e.created_at}] Alimento: {e.food_item} | Escalón: {e.sensory_step} | Textura: {e.texture_notes} | Estado: {e.mood_state} | Nota: {e.raw_notes}"
                for e in recent_entries[:8]
            ]
        ) or "Sin registros previos en la bitácora."

        prompt_context = (
            f"Nombre del niño/a: {child_name}\n"
            f"Clasificación automática del mensaje actual: Intención={parsed.intent}, "
            f"Alimento={parsed.food_item}, Escalón={parsed.sensory_step}, "
            f"Textura={parsed.texture_notes}, Estado={parsed.mood_state}\n\n"
            f"Últimos registros en su bitácora:\n{history_summary}\n\n"
            f"Mensaje actual de la familia:\n\"{user_message}\"\n\n"
            "Instrucción: Si se acaba de registrar un avance o evento en la bitácora, celébralo con calidez "
            "según la Escalera Sensorial y ofrece una recomendación breve y práctica basada en el TFM de la "
            "Mtra. Cindy Morales Alarcón. Si hace una pregunta sobre TEA o alimentación, respóndela con claridad, "
            "empatía y rigor científico."
        )

        url = f"https://generativelanguage.googleapis.com/v1beta/models/{self.model_name}:generateContent?key={self.api_key}"
        payload = {
            "system_instruction": {"parts": [{"text": SYSTEM_PROMPT}]},
            "contents": [{"role": "user", "parts": [{"text": prompt_context}]}],
            "generationConfig": {"temperature": 0.4, "maxOutputTokens": 700},
        }

        req = urllib.request.Request(
            url,
            data=json.dumps(payload).encode("utf-8"),
            headers={"Content-Type": "application/json"},
            method="POST",
        )
        with urllib.request.urlopen(req, timeout=15) as resp:
            data = json.loads(resp.read().decode("utf-8"))
            candidates = data.get("candidates", [])
            if candidates:
                parts = candidates[0].get("content", {}).get("parts", [])
                if parts and "text" in parts[0]:
                    return parts[0]["text"].strip()

        return self._generate_local_tfm_response(user_message, parsed, recent_entries, child_name)

    def _generate_local_tfm_response(
        self,
        user_message: str,
        parsed: ParsedMessageResult,
        recent_entries: List[BitacoraEntry],
        child_name: str,
    ) -> str:
        lower = user_message.lower()
        lines = []

        if parsed.intent in ("LOG_ENTRY", "BOTH"):
            lines.append(
                f"📒 **¡Registro guardado en la bitácora de {child_name}!**\n"
                f"• **Alimento:** {parsed.food_item}\n"
                f"• **Escalón sensorial:** {parsed.sensory_step}\n"
                f"• **Textura/Presentación:** {parsed.texture_notes}\n"
                f"• **Estado:** {parsed.mood_state}\n"
            )
            if parsed.sensory_step in ("Toleró presencia", "Olió", "Tocó", "Acercó a la boca"):
                lines.append(
                    f"🌱 **Lectura desde «El Autismo Sobre La Mesa»:** ¡Este paso cuenta muchísimo! "
                    f"Que {child_name} haya logrado **{parsed.sensory_step.lower()}** con *{parsed.food_item}* "
                    "reduce la alerta de su sistema nervioso. Recuerda no presionar para que lo trague hoy; "
                    "mantener la experiencia segura consolida la confianza."
                )
            elif parsed.sensory_step in ("Probó", "Comió"):
                lines.append(
                    f"🎉 **¡Gran victoria sensorial!** {child_name} dio el paso de **{parsed.sensory_step.lower()}** "
                    f"con *{parsed.food_item}*. Puedes usar las características de este alimento (su forma, temperatura o textura) "
                    "como **alimento puente (Food Chaining)** para futuras exploraciones similares."
                )
            elif parsed.sensory_step == "Rechazó":
                lines.append(
                    f"💚 **Acompañamiento sin culpa:** El rechazo ante *{parsed.food_item}* no es un retroceso ni un capricho. "
                    "Según la investigación del TFM, puede deberse a sobrecarga sensorial previa, un cambio sutil en la presentación "
                    "o cansancio. Te sugiero volver un escalón atrás (solo dejarlo en un plato auxiliar lejos del suyo) sin exigencias."
                )

        if parsed.intent in ("QUESTION", "BOTH"):
            if any(k in lower for k in ["textura", "grumo", "trozo", "crujiente", "puré", "pure", "mezcla"]):
                lines.append(
                    "🥣 **Sobre las texturas en el TEA:**\n"
                    "La boca concentra una altísima densidad de receptores táctiles. Muchos niños con perfil hiperreactivo "
                    "rechazan las **texturas mixtas** (sopas con tropezones, yogur con fruta) porque su cerebro no logra predecir "
                    "qué sensación viene en cada cucharada.\n"
                    "• **Recomendación:** Presenta los alimentos **separados** en el plato y utiliza la técnica del *Alimento Puente*: "
                    "si acepta algo crujiente, introduce otro alimento con exactamente el mismo nivel de crujido."
                )
            elif any(k in lower for k in ["peso", "delgad", "nutrici", "vitamin", "hierro", "crecimiento"]):
                lines.append(
                    "⚖️ **El mito del peso corporal (Evidencia del TFM):**\n"
                    "La investigación de la Mtra. Cindy Morales Alarcón destaca que un peso o percentil normal **no garantiza** "
                    "una nutrición completa. Los repertorios muy selectivos pueden cubrir las calorías pero tener carencias de "
                    "micronutrientes (hierro, zinc, vitaminas, fibra).\n"
                    "• **Recomendación:** Exporta tu bitácora con `/exportar` y compártela con su nutricionista pediátrico para valorar "
                    "la calidad de la dieta sin forzar las comidas."
                )
            elif any(k in lower for k in ["estómago", "estomago", "estreñimiento", "reflujo", "dolor", "panza", "barriga", "gastro"]):
                lines.append(
                    "🩺 **Vínculo Gastrointestinal y TEA:**\n"
                    "El TFM subraya una alta coexistencia de molestias gastrointestinales (estreñimiento, reflujo, malestar abdominal) "
                    "en niños con TEA. Muchas veces el niño rechaza comer porque asocia el alimento con malestar físico.\n"
                    "• **Recomendación:** Descarta primero con el pediatra cualquier causa digestiva u oromotora antes de abordar el rechazo como algo únicamente conductual."
                )
            elif any(k in lower for k in ["escuela", "colegio", "comedor", "maestra", "profes"]):
                lines.append(
                    "🏫 **El comedor escolar y la coordinación:**\n"
                    "El ruido acústico, los olores mezclados y la prisa del comedor escolar suelen desregular al niño antes del primer bocado.\n"
                    "• **Recomendación:** Acuerda con la escuela anticipar el menú con pictogramas, permitir un lugar más tranquilo, "
                    "respetar su utensilio habitual y asegurar siempre al menos un **alimento seguro** en su bandeja."
                )
            else:
                lines.append(
                    "📘 **Guía «El Autismo Sobre La Mesa» (Mtra. Cindy Morales Alarcón):**\n"
                    "Para acompañar la selectividad alimentaria en casa recuerda los 4 pilares del estudio:\n"
                    "1️⃣ **Cero coacción:** Evita luchas de poder; el estrés bloquea el apetito.\n"
                    "2️⃣ **Regulación previa:** 10 minutos de juego tranquilo o presión profunda antes de ir a la mesa.\n"
                    "3️⃣ **Escalera sensorial:** Tolerar en la mesa → tocar → oler → besar el alimento → probar con permiso de escupir.\n"
                    "4️⃣ **Alimento puente:** Conecta alimentos seguros con nuevos que compartan color, forma o textura."
                )

        return "\n\n".join(lines)
