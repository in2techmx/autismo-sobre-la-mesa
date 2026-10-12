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
                    "🏫 **El comedor escolar y la adaptación sensorial (Conti et al., 2026):**\n"
                    "El ruido acústico, los olores mezclados y la prisa del comedor escolar suelen desregular al niño antes del primer bocado.\n"
                    "• **Recomendación:** Acuerda con la escuela anticipar el menú con pictogramas, permitir un lugar más tranquilo, "
                    "respetar su utensilio habitual y asegurar siempre al menos un **alimento seguro** en su bandeja."
                )
            elif any(k in lower for k in ["arfid", "trastorno", "evitación", "evitacion", "sos", "toomey"]):
                lines.append(
                    "🔬 **Evidencia Internacional (ARFID & Método SOS):**\n"
                    "• **Comorbilidad TEA–ARFID:** Investigada por la red *EDAC (Universidad de Edimburgo, Sader et al., 2025)*, "
                    "reconoce cuando la selectividad trasciende a un Trastorno de Evitación/Restricción de la Ingesta de Alimentos.\n"
                    "• **Jerarquía Steps to Eating (SOS Approach to Feeding):** Armoniza con la guía «El Autismo Sobre La Mesa» "
                    "dividiendo el acercamiento en pasos sin presión (tolerar → mirar → oler → tocar → probar)."
                )
            elif any(k in lower for k in ["bambi", "cuestionario", "inventario", "evaluaci", "puntaje", "puntuaci"]):
                lines.append(
                    "📋 **Inventario BAMBI (Brief Autism Mealtime Behavior Inventory):**\n"
                    "Consta de **18 preguntas** en escala Likert del 1 (*Nunca*) al 5 (*Siempre*), con 4 ítems inversos (3, 9, 10 y 15). Evalúa 3 dimensiones:\n"
                    "• 🧃 **Rechazo Alimentario:** Bloquear la boca, escupir, girar la cara o llorar.\n"
                    "• 🥦 **Selectividad Alimentaria:** Rigidez con texturas, marcas o resistencia a alimentos nuevos.\n"
                    "• 🪑 **Conductas Disruptivas en la Mesa:** Levantarse, aventar platos o inflexibilidad en rutinas.\n"
                    "📊 **Interpretación:** Rango de 18 a 90 puntos. Un puntaje **≥ 34 puntos** indica dificultades alimentarias clínicamente significativas. Puedes contestarlo de forma interactiva en el Capítulo 6 de nuestra web."
                )
            elif any(k in lower for k in ["asociaci", "organiza", "ayuda", "méxico", "mexico", "españa", "alicante", "europa", "ong", "fundaci"]):
                lines.append(
                    "🤝 **Redes y Organizaciones de Referencia:**\n"
                    "• **España:** APACV (Alicante), Confederación Autismo España, Universidad de Alicante (MUNA), Fundación ConecTEA, Fundación Ángel Rivière, AEPED/SPINUT.\n"
                    "• **México:** Colectivo Autismo Ciudad de México (Apapache A.C., Autentic, Cemedepsi, Crea tu Mundo, Comunidad Unique) y Fundación TATO.\n"
                    "• **Europa e Internacional:** Autism-Europe, STAR Institute for Sensory Processing, SOS Approach to Feeding y Feeding Matters."
                )
            else:
                lines.append(
                    "📘 **Guía «El Autismo Sobre La Mesa» (Mtra. Cindy Morales Alarcón — UA/MUNA):**\n"
                    "Para acompañar la selectividad alimentaria en casa recuerda los 4 pilares del estudio:\n"
                    "1️⃣ **Cero coacción:** Evita luchas de poder; el estrés bloquea el apetito.\n"
                    "2️⃣ **Regulación previa:** 10 minutos de juego tranquilo o presión profunda antes de ir a la mesa.\n"
                    "3️⃣ **Escalera sensorial:** Tolerar en la mesa → tocar → oler → besar el alimento → probar con permiso de escupir.\n"
                    "4️⃣ **Alimento puente (Food Chaining):** Conecta alimentos seguros con nuevos que compartan color, forma o textura."
                )

        return "\n\n".join(lines)

    def generate_clinical_analysis(
        self,
        entries: List[BitacoraEntry],
        child_name: str = "tu peque",
        latest_bambi: Optional[dict] = None,
    ) -> str:
        """
        Analiza todos los registros acumulados en la bitácora (y el puntaje BAMBI si existe)
        para detectar patrones sensoriales, emocionales y entregar un Plan de Apoyos e Indicaciones.
        """
        if not entries:
            return (
                f"🧠 **Análisis Clínico-Sensorial de {child_name}**\n\n"
                "Aún no hay registros suficientes en la bitácora para detectar patrones.\n"
                "👉 Escríbeme primero un par de mensajes contándome qué alimentos ha tolerado, tocado, probado o rechazado hoy."
            )

        deterministic_report = self._generate_deterministic_analysis(entries, child_name, latest_bambi)

        if self.api_key:
            try:
                history_lines = "\n".join(
                    [
                        f"- [{e.created_at}] Alimento: {e.food_item} | Escalón: {e.sensory_step} | Textura: {e.texture_notes} | Estado: {e.mood_state} | Nota: {e.raw_notes}"
                        for e in entries[:30]
                    ]
                )
                bambi_ctx = (
                    f"Último puntaje BAMBI registrado: Total={latest_bambi['total_score']}/90 "
                    f"(Rechazo={latest_bambi.get('refusal_score', 0)}, Selectividad={latest_bambi.get('selectivity_score', 0)}, Disruptivo={latest_bambi.get('disruptive_score', 0)})"
                    if latest_bambi
                    else "Sin cuestionario BAMBI registrado aún."
                )
                prompt = (
                    f"Actúa como el sistema de análisis clínico del TFM de la Mtra. Maria Cindy Morales Alarcón.\n"
                    f"Analiza el historial de bitácora de {child_name} ({len(entries)} registros) y su contexto BAMBI ({bambi_ctx}).\n\n"
                    f"HISTORIAL DE BITÁCORA:\n{history_lines}\n\n"
                    f"RESUMEN ESTADÍSTICO BASE:\n{deterministic_report}\n\n"
                    "Genera un informe estructurado, cálido y accionable con:\n"
                    "1. 🔍 Patrones Sensoriales y de Textura detectados (qué acepta mejor vs qué detona rechazo).\n"
                    "2. 📊 Cruce con las 3 dimensiones del BAMBI (Rechazo, Selectividad, Conducta en mesa).\n"
                    "3. 🌉 Propuesta concreta de Alimentos Puente (Food Chaining) a partir de los alimentos que sí ha tolerado/comido.\n"
                    "4. 🛠️ 3 Indicaciones o Apoyos prácticos para aplicar esta semana en casa y comedor escolar."
                )
                url = f"https://generativelanguage.googleapis.com/v1beta/models/{self.model_name}:generateContent?key={self.api_key}"
                payload = {
                    "system_instruction": {"parts": [{"text": SYSTEM_PROMPT}]},
                    "contents": [{"role": "user", "parts": [{"text": prompt}]}],
                    "generationConfig": {"temperature": 0.35, "maxOutputTokens": 900},
                }
                req = urllib.request.Request(
                    url,
                    data=json.dumps(payload).encode("utf-8"),
                    headers={"Content-Type": "application/json"},
                    method="POST",
                )
                with urllib.request.urlopen(req, timeout=18) as resp:
                    data = json.loads(resp.read().decode("utf-8"))
                    candidates = data.get("candidates", [])
                    if candidates:
                        parts = candidates[0].get("content", {}).get("parts", [])
                        if parts and "text" in parts[0]:
                            return parts[0]["text"].strip()
            except Exception:
                pass

        return deterministic_report

    def _generate_deterministic_analysis(
        self,
        entries: List[BitacoraEntry],
        child_name: str,
        latest_bambi: Optional[dict] = None,
    ) -> str:
        total = len(entries)
        accepted_foods = []
        explored_foods = []
        rejected_foods = []
        accepted_textures: dict[str, int] = {}
        rejected_textures: dict[str, int] = {}
        stress_episodes = 0
        calm_episodes = 0

        for e in entries:
            tex = e.texture_notes if e.texture_notes and e.texture_notes != "Estándar" else ""
            if e.sensory_step in ("Comió", "Probó"):
                if e.food_item not in accepted_foods:
                    accepted_foods.append(e.food_item)
                if tex:
                    accepted_textures[tex] = accepted_textures.get(tex, 0) + 1
            elif e.sensory_step in ("Toleró presencia", "Olió", "Tocó", "Acercó a la boca"):
                if e.food_item not in explored_foods:
                    explored_foods.append(e.food_item)
                if tex:
                    accepted_textures[tex] = accepted_textures.get(tex, 0) + 1
            elif e.sensory_step == "Rechazó":
                if e.food_item not in rejected_foods:
                    rejected_foods.append(e.food_item)
                if tex:
                    rejected_textures[tex] = rejected_textures.get(tex, 0) + 1

            if e.mood_state in ("Ansioso", "Sobrecargado"):
                stress_episodes += 1
            elif e.mood_state in ("En calma", "Curioso"):
                calm_episodes += 1

        rejection_rate = (len([e for e in entries if e.sensory_step == "Rechazó"]) / total) * 100

        lines = [
            f"🧠 **Informe de Análisis Clínico-Sensorial y Plan de Apoyos para {child_name}**",
            f"*Basado en {total} registros de su bitácora y la evidencia del TFM (Mtra. Cindy Morales Alarcón)*\n",
        ]

        if latest_bambi:
            b_score = latest_bambi["total_score"]
            status_str = "Clínicamente significativo (≥ 34 ptos)" if b_score >= 34 else "Leve/Moderado (< 34 ptos)"
            lines.append(
                f"📋 **Línea Base BAMBI Registrada:** **{b_score} / 90 ptos** — *{status_str}*"
            )

        # 1. Patrones detectados
        lines.append("🔍 **1. Patrones Sensoriales Detectados:**")
        if accepted_foods:
            lines.append(f"• **Alimentos con mayor aceptación/éxito:** {', '.join(accepted_foods[:6])}")
        if explored_foods:
            lines.append(f"• **En fase de aproximación sensorial (tolerar/tocar/oler):** {', '.join(explored_foods[:6])}")
        if rejected_foods:
            lines.append(f"• **Alimentos que activan rechazo o defensa sensorial:** {', '.join(rejected_foods[:6])}")

        if accepted_textures:
            best_tex = sorted(accepted_textures.items(), key=lambda x: x[1], reverse=True)[0][0]
            lines.append(f"• **Textura mejor tolerada:** *{best_tex}* (vía de seguridad perceptiva).")
        if rejected_textures:
            worst_tex = sorted(rejected_textures.items(), key=lambda x: x[1], reverse=True)[0][0]
            lines.append(f"• **Textura de mayor desafío:** *{worst_tex}* (posible hiperreactividad táctil intraoral).")

        lines.append(
            f"• **Balance emocional en la mesa:** {calm_episodes} experiencias en calma/curiosidad vs {stress_episodes} episodios de ansiedad/sobrecarga."
        )

        # 2. Indicaciones y Apoyos personalizados
        lines.append("\n🛠️ **2. Indicaciones y Apoyos Personalizados (Plan de Acción):**")

        if accepted_foods or explored_foods:
            base_food = (accepted_foods + explored_foods)[0]
            lines.append(
                f"1️⃣ **Estrategia de Alimento Puente (Food Chaining):** Toma como ancla *{base_food}* y ofrece la próxima semana una variante que conserve la misma forma, color o temperatura, cambiando solo un 10% la preparación."
            )
        else:
            lines.append(
                "1️⃣ **Construcción de Seguridad Visual:** Utiliza un «plato de aprendizaje» separado del plato principal donde el alimento nuevo solo esté presente en la mesa sin ninguna exigencia de tocarlo ni comerlo."
            )

        if rejection_rate >= 40 or stress_episodes > calm_episodes:
            lines.append(
                "2️⃣ **Reducción de Alerta Sensorial (Prioridad Alta):** Se observa una tasa elevada de rechazo o estrés en la mesa. Implementa **10-15 minutos de regulación propioceptiva** antes de comer (presión profunda, saltar suaves, abrazos firmes) y limita la duración en la mesa a máximo 20-25 minutos con cero coacción."
            )
        else:
            lines.append(
                "2️⃣ **Avance en la Escalera Sensorial (Steps to Eating):** Dado que hay buena regulación en calma, invita a jugar con los alimentos en exploración (tocar con tenedor, oler o dar un «besito» al alimento) celebrando cada micro-paso."
            )

        if rejected_foods:
            lines.append(
                f"3️⃣ **Ajuste para {', '.join(rejected_foods[:2])}:** No los retires definitivamente ni obligues a probarlos; preséntalos en trozos muy pequeños, separados visualmente de su alimento seguro y sin salsas ni mezclas."
            )
        else:
            lines.append(
                "3️⃣ **Coordinación Familia–Escuela:** Comparte tu archivo `/exportar` con el comedor escolar o su terapeuta ocupacional para mantener exactamente los mismos apoyos visuales y utensilios."
            )

        lines.append(
            "\n💡 *Tip: También puedes guardar tu puntaje del cuestionario BAMBI escribiendo `/registrar_bambi <puntaje>` (ej. `/registrar_bambi 42`).*"
        )
        return "\n".join(lines)
