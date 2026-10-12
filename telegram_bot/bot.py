"""
Bot de Telegram — «El Autismo Sobre La Mesa»
Autora de la investigación y guía: Mtra. Maria Cindy Morales Alarcón

Funcionalidades:
- /start : Bienvenida, presentación de la guía e instrucciones.
- /peque <Nombre> : Personaliza el nombre del niño/a para su bitácora.
- /registrar <texto> : Registra directamente una entrada en la bitácora.
- /bitacora : Muestra los últimos registros y estadísticas de avances sensoriales.
- /exportar : Envía un archivo CSV (compatible con Excel) con todo el historial para el terapeuta o nutricionista.
- /escalera : Explica los pasos de la Escalera Sensorial del TFM.
- Mensajes libres de texto: Detecta automáticamente si estás anotando algo en la bitácora
  (ej. "Hoy tocó la fresa con el dedo y estuvo tranquilo") o si estás haciendo una consulta sobre TEA y alimentación,
  o ambas cosas a la vez.
"""

import io
import logging
import os
from datetime import datetime

from telegram import InlineKeyboardButton, InlineKeyboardMarkup, Update
from telegram.constants import ParseMode
from telegram.ext import (
    Application,
    CallbackQueryHandler,
    CommandHandler,
    ContextTypes,
    MessageHandler,
    filters,
)

from ai_assistant import TeaAdvisorService, parse_user_message
from database import BitacoraRepository

logging.basicConfig(
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
    level=logging.INFO,
)
logger = logging.getLogger("AutismoSobreLaMesaBot")

DB_PATH = os.environ.get("BITACORA_DB_PATH", "bitacora_tea.db")
repo = BitacoraRepository(DB_PATH)
advisor = TeaAdvisorService()


def get_main_keyboard() -> InlineKeyboardMarkup:
    keyboard = [
        [
            InlineKeyboardButton("🧠 Analizar y Dar Apoyos", callback_data="ver_analisis"),
        ],
        [
            InlineKeyboardButton("📒 Ver mi Bitácora", callback_data="ver_bitacora"),
            InlineKeyboardButton("📊 Exportar Excel/CSV", callback_data="exportar_csv"),
        ],
        [
            InlineKeyboardButton("🪜 Escalera Sensorial", callback_data="ver_escalera"),
            InlineKeyboardButton("📋 Cuestionario BAMBI", callback_data="ver_bambi"),
        ],
        [
            InlineKeyboardButton("🤝 Redes y Apoyo", callback_data="ver_redes"),
            InlineKeyboardButton("🌐 Guía Web Interactiva", url="https://in2techmx.github.io/autismo-sobre-la-mesa/#bambi-section"),
        ],
    ]
    return InlineKeyboardMarkup(keyboard)


async def start_command(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    user = update.effective_user
    if not user or not update.message:
        return

    profile = repo.upsert_profile(user_id=user.id, username=user.username or user.first_name)
    child_name = profile.get("child_name", "tu peque")

    welcome_text = (
        f"🍽️ **¡Hola, {user.first_name}! Bienvenido/a a «El Autismo Sobre La Mesa»**\n\n"
        "Soy tu asistente de acompañamiento e integración sensorial, basado en el Trabajo de Fin de Máster "
        "de la **Mtra. Maria Cindy Morales Alarcón** (*MUNA — Universidad de Alicante*).\n\n"
        "✨ **¿Cómo puedo ayudarte hoy?**\n"
        "1️⃣ **Llevar tu Bitácora por mensaje libre:** Solo escríbeme como a un amigo, por ejemplo:\n"
        "   • *\"Hoy en la comida toleró el brócoli en el plato y lo tocó con el tenedor, estuvo tranquilo\"*\n"
        "   • *\"Hoy rechazó el puré de papa porque tenía grumos\"*\n\n"
        "2️⃣ **Analizar tus registros con IA y darte Indicaciones/Apoyos:**\n"
        "   • Usa `/analisis` (o el botón **🧠 Analizar y Dar Apoyos**) para que cruce tu historial de comidas y tu puntaje BAMBI y te dé estrategias personalizadas de *Alimento Puente*, *Regulación Sensorial* y *Ajustes en Mesa*.\n\n"
        "3️⃣ **Resolver tus dudas sobre TEA y alimentación:** Pregúntame lo que necesites:\n"
        "   • *\"¿Cómo aplico el alimento puente si solo come nuggets?\"*\n"
        "   • *\"¿Por qué le dan arcadas los olores fuertes?\"*\n\n"
        "📌 **Comandos rápidos:**\n"
        f"• `/peque Nombre` — Cambia el nombre de tu peque (actual: **{child_name}**)\n"
        "• `/analisis` — **Diagnóstico de patrones e indicaciones personalizadas de apoyo**\n"
        "• `/registrar_bambi 42` — Guarda tu puntaje del cuestionario BAMBI en tu expediente\n"
        "• `/bitacora` — Resumen de avances registrados\n"
        "• `/exportar` — Descarga tu bitácora en Excel/CSV para llevarla a consulta\n"
        "• `/bambi` — Guía e interpretación del Cuestionario BAMBI\n"
        "• `/escalera` — Consulta los pasos de la Escalera Sensorial\n"
        "• `/redes` — Directorio de organizaciones en España, México, Europa y EE. UU."
    )
    await update.message.reply_text(
        welcome_text,
        parse_mode=ParseMode.MARKDOWN,
        reply_markup=get_main_keyboard(),
    )


async def set_child_name_command(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    user = update.effective_user
    if not user or not update.message:
        return

    if not context.args:
        await update.message.reply_text(
            "Por favor escribe el nombre después del comando. Ejemplo:\n`/peque Mía`",
            parse_mode=ParseMode.MARKDOWN,
        )
        return

    new_name = " ".join(context.args).strip()
    repo.upsert_profile(user_id=user.id, username=user.username or "", child_name=new_name)
    await update.message.reply_text(
        f"💚 ¡Perfecto! A partir de ahora llevaré la bitácora personalizada para **{new_name}**.",
        parse_mode=ParseMode.MARKDOWN,
    )


async def bitacora_command(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    user = update.effective_user
    message = update.effective_message
    if not user or not message:
        return

    profile = repo.get_profile(user.id)
    child_name = profile["child_name"]
    entries = repo.get_recent_entries(user.id, limit=8)
    stats = repo.get_summary_stats(user.id)

    if not entries:
        await message.reply_text(
            f"📒 La bitácora de **{child_name}** aún no tiene registros.\n\n"
            "Escríbeme un mensaje contándome qué comió, tocó, olió o probó hoy, por ejemplo:\n"
            "*\"Hoy olió una fresa y estuvo muy curioso\"*",
            parse_mode=ParseMode.MARKDOWN,
        )
        return

    lines = [
        f"📒 **Bitácora Alimentaria de {child_name}**",
        f"📊 *Total de registros:* {stats['total_entries']} | *Alimentos explorados:* {stats['unique_foods_count']}\n",
        "🕒 **Últimos avances registrados:**",
    ]
    for e in entries:
        date_short = e.created_at[:16]
        lines.append(
            f"• `{date_short}` — **{e.food_item}** → *{e.sensory_step}* "
            f"(Textura: {e.texture_notes} | Estado: {e.mood_state})"
        )

    lines.append("\n💡 Usa `/analisis` para recibir indicaciones de apoyo o `/exportar` para descargar en Excel.")
    await message.reply_text(
        "\n".join(lines),
        parse_mode=ParseMode.MARKDOWN,
        reply_markup=get_main_keyboard(),
    )


async def analisis_command(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    user = update.effective_user
    message = update.effective_message
    if not user or not message:
        return

    profile = repo.get_profile(user.id)
    child_name = profile["child_name"]
    entries = repo.get_recent_entries(user.id, limit=50)
    bambi_record = repo.get_latest_bambi_score(user.id)

    analysis_text = advisor.generate_clinical_analysis(
        entries=entries,
        child_name=child_name,
        latest_bambi=bambi_record,
    )
    await message.reply_text(
        analysis_text,
        parse_mode=ParseMode.MARKDOWN,
        reply_markup=get_main_keyboard(),
    )


async def registrar_bambi_command(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    user = update.effective_user
    message = update.effective_message
    if not user or not message:
        return

    if not context.args:
        await message.reply_text(
            "📋 **Cómo registrar tu puntaje BAMBI en el bot:**\n\n"
            "Escribe `/registrar_bambi` seguido de tu puntuación total (entre 18 y 90). "
            "Opcionalmente puedes añadir los 3 subtotales (Rechazo, Selectividad, Disruptivas).\n\n"
            "• Ejemplo rápido: `/registrar_bambi 42`\n"
            "• Ejemplo detallado: `/registrar_bambi 42 15 16 11`\n\n"
            "👉 Si aún no conoces tu puntaje, calcúlalo gratis aquí:\n"
            "[Calculadora BAMBI Interactiva](https://in2techmx.github.io/autismo-sobre-la-mesa/#bambi-section)",
            parse_mode=ParseMode.MARKDOWN,
        )
        return

    try:
        total = int(context.args[0])
        if not (18 <= total <= 90):
            raise ValueError("Fuera de rango")
        refusal = int(context.args[1]) if len(context.args) > 1 else 0
        selectivity = int(context.args[2]) if len(context.args) > 2 else 0
        disruptive = int(context.args[3]) if len(context.args) > 3 else 0
    except ValueError:
        await message.reply_text(
            "⚠️ Por favor introduce un número válido entre **18 y 90**.\nEjemplo: `/registrar_bambi 42`",
            parse_mode=ParseMode.MARKDOWN,
        )
        return

    record = repo.add_bambi_score(
        user_id=user.id,
        total_score=total,
        refusal_score=refusal,
        selectivity_score=selectivity,
        disruptive_score=disruptive,
    )
    profile = repo.get_profile(user.id)
    child_name = profile["child_name"]
    status_str = (
        "🟠 **≥ 34 ptos (Selectividad clínicamente significativa)**"
        if record["clinical_flag"]
        else "🟢 **< 34 ptos (Dentro del rango esperado)**"
    )
    await message.reply_text(
        f"✅ **Puntaje BAMBI guardado para {child_name}:** `{total} / 90 ptos`\n"
        f"• Interpretación: {status_str}\n\n"
        "🧠 Ahora puedes pulsar **«Analizar y Dar Apoyos»** o escribir `/analisis` para que cruce este resultado con tu bitácora diaria.",
        parse_mode=ParseMode.MARKDOWN,
        reply_markup=get_main_keyboard(),
    )


async def exportar_command(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    user = update.effective_user
    message = update.effective_message
    if not user or not message:
        return

    entries = repo.get_recent_entries(user.id, limit=1)
    if not entries:
        await message.reply_text(
            "Aún no tienes registros en tu bitácora para exportar. ¡Escríbeme tu primer registro primero!"
        )
        return

    csv_bytes = repo.export_user_csv(user.id)
    profile = repo.get_profile(user.id)
    safe_child = profile["child_name"].replace(" ", "_")
    filename = f"Bitacora_{safe_child}_{datetime.now().strftime('%Y%m%d')}.csv"

    await message.reply_document(
        document=io.BytesIO(csv_bytes),
        filename=filename,
        caption=(
            f"📊 Aquí tienes la **Bitácora de Alimentación de {profile['child_name']}**.\n"
            "Puedes abrirla directamente en Excel y compartirla con su Terapeuta Ocupacional, "
            "Logopeda o Nutricionista Pediátrico."
        ),
        parse_mode=ParseMode.MARKDOWN,
    )


async def escalera_command(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    message = update.effective_message
    if not message:
        return

    text = (
        "🪜 **La Escalera de las Pequeñas Victorias**\n"
        "*Fundamentada en el TFM de la Mtra. Cindy Morales Alarcón*\n\n"
        "El objetivo inicial **no es que el niño trague**, sino desactivar el miedo sensorial paso a paso:\n\n"
        "1️⃣ **Tolerar la presencia:** Que el alimento esté en la mesa o en un plato auxiliar sin presión.\n"
        "2️⃣ **Interactuar sin comer:** Tocarlo con el tenedor, ayudar a servirlo o jugar con él.\n"
        "3️⃣ **Oler:** Acercarse al aroma sin exigencia.\n"
        "4️⃣ **Tocar con la piel:** Con la yema del dedo, la mano o acercarlo a la mejilla.\n"
        "5️⃣ **Acercar a la boca:** Dar un \"besito\" al alimento o tocarlo con los labios.\n"
        "6️⃣ **Probar y decidir:** Dar un micromordisco con permiso para escupirlo en una servilleta si la sensación es intensa.\n\n"
        "💚 *Cada escalón que registres en tu bitácora es un logro real.*"
    )
    await message.reply_text(text, parse_mode=ParseMode.MARKDOWN)


async def redes_command(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    message = update.effective_message
    if not message:
        return

    text = (
        "🤝 **Redes y Organizaciones de Referencia Internacional**\n"
        "*Informe de Investigación — Mtra. Maria Cindy Morales Alarcón (UA/MUNA)*\n\n"
        "🇪🇸 **España:**\n"
        "• **APACV (Alicante):** Asociación de Padres y Amigos de Personas con Autismo de la Comunidad Valenciana.\n"
        "• **Autismo España** y Federaciones Autonómicas.\n"
        "• **Universidad de Alicante (MUNA):** Soporte científico y transferencia.\n"
        "• **Fundación ConecTEA / Ángel Rivière / Aucavi / AEPED-SPINUT.**\n\n"
        "🇲🇽 **México:**\n"
        "• **Colectivo Autismo Ciudad de México:** Apapache A.C., Autentic/Autismo México, Cemedepsi, Crea tu Mundo Autismo, Comunidad Unique.\n"
        "• **Fundación TATO** y colectivos estatales (Guadalajara, Monterrey, Mérida, Puebla).\n\n"
        "🇪🇺 **Unión Europea:**\n"
        "• **Autism-Europe**, Federació Catalana d'Autisme, EPR (European Platform for Rehabilitation).\n\n"
        "🌎 **Estados Unidos e Internacional:**\n"
        "• **STAR Institute for Sensory Processing** (Colorado)\n"
        "• **SOS Approach to Feeding** (Dra. Kay Toomey — *Steps to Eating*)\n"
        "• **Feeding Matters** (PFD), **Autism Speaks**, **EDAC** (Univ. de Edimburgo — ARFID)."
    )
    await message.reply_text(text, parse_mode=ParseMode.MARKDOWN, reply_markup=get_main_keyboard())


async def bambi_command(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    message = update.effective_message
    if not message:
        return

    text = (
        "📋 **Inventario BAMBI (Brief Autism Mealtime Behavior Inventory)**\n"
        "*Cuestionario para evaluar conducta durante las comidas (cuidadores o adultos autistas)*\n\n"
        "📏 **Sistema de Puntuación (Escala Likert 1 a 5 en 18 ítems):**\n"
        "• **1 pto:** Nunca / Raramente\n"
        "• **2 ptos:** Pocas veces (Seldom)\n"
        "• **3 ptos:** A veces\n"
        "• **4 ptos:** A menudo\n"
        "• **5 ptos:** Siempre / Casi todas las comidas\n"
        "⚠️ *Ítems inversos (3, 9, 10 y 15):* Redactados en positivo (ej. «Está dispuesto a probar nuevos alimentos»); su puntaje se invierte antes de sumar ($1\\rightarrow5, 2\\rightarrow4, 3\\rightarrow3, 4\\rightarrow2, 5\\rightarrow1$).\n\n"
        "📊 **Puntuación Total e Interpretación:**\n"
        "• **Rango posible:** De **18 puntos** (mínimo problema) a **90 puntos** (máximo problema).\n"
        "• **Umbral clínico:** Una puntuación total **≥ 34 puntos** suele indicar problemas de alimentación clínicamente significativos en niños con TEA.\n\n"
        "🎯 **Análisis por 3 Dimensiones (Factores):**\n"
        "1️⃣ 🧃 **Rechazo Alimentario (Food Refusal):** Bloquea la boca, escupe, llora o rechaza categóricamente lo servido.\n"
        "2️⃣ 🥦 **Selectividad Alimentaria:** Rigidez con texturas, marcas, colores o resistencia a probar alimentos nuevos.\n"
        "3️⃣ 🪑 **Conductas Disruptivas en la Mesa:** Se levanta constantemente, avienta platos o no mantiene atención en comer.\n\n"
        "💡 *Para vincular tu resultado con el análisis de IA del bot, usa:* `/registrar_bambi <puntaje>` (ej. `/registrar_bambi 42`).\n"
        "👉 [Realizar Cuestionario BAMBI Interactivo](https://in2techmx.github.io/autismo-sobre-la-mesa/#bambi-section)"
    )
    await message.reply_text(text, parse_mode=ParseMode.MARKDOWN, reply_markup=get_main_keyboard())


async def handle_callback_query(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    query = update.callback_query
    if not query:
        return
    await query.answer()

    if query.data == "ver_analisis":
        await analisis_command(update, context)
    elif query.data == "ver_bitacora":
        await bitacora_command(update, context)
    elif query.data == "exportar_csv":
        await exportar_command(update, context)
    elif query.data == "ver_escalera":
        await escalera_command(update, context)
    elif query.data == "ver_bambi":
        await bambi_command(update, context)
    elif query.data == "ver_redes":
        await redes_command(update, context)


async def handle_free_text(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    user = update.effective_user
    if not user or not update.message or not update.message.text:
        return

    text = update.message.text.strip()
    lower = text.lower()
    profile = repo.upsert_profile(user_id=user.id, username=user.username or user.first_name)
    child_name = profile["child_name"]

    # Si el usuario pide directamente analizar su bitácora o qué apoyos/indicaciones seguir según sus registros
    if any(
        kw in lower
        for kw in (
            "analiza mi bitacora",
            "analiza mi bitácora",
            "analizar bitacora",
            "analizar bitácora",
            "dame indicaciones",
            "dame apoyos",
            "que apoyos me recomiendas",
            "qué apoyos me recomiendas",
            "analisis de bitacora",
            "análisis de bitácora",
        )
    ):
        await analisis_command(update, context)
        return

    parsed = parse_user_message(text)

    # Si el mensaje contiene un registro de alimentación, lo guardamos en SQLite
    if parsed.intent in ("LOG_ENTRY", "BOTH"):
        repo.add_entry(
            user_id=user.id,
            food_item=parsed.food_item,
            sensory_step=parsed.sensory_step,
            raw_notes=text,
            texture_notes=parsed.texture_notes,
            mood_state=parsed.mood_state,
            child_name=child_name,
        )

    recent_entries = repo.get_recent_entries(user.id, limit=15)
    reply = advisor.generate_response(
        user_message=text,
        parsed=parsed,
        recent_entries=recent_entries,
        child_name=child_name,
    )

    await update.message.reply_text(
        reply,
        parse_mode=ParseMode.MARKDOWN,
        reply_markup=get_main_keyboard(),
    )


def _load_dotenv_if_present() -> None:
    env_file = os.path.join(os.path.dirname(os.path.abspath(__file__)), ".env")
    if os.path.exists(env_file):
        with open(env_file, "r", encoding="utf-8") as f:
            for line in f:
                line = line.strip()
                if line and not line.startswith("#") and "=" in line:
                    k, v = line.split("=", 1)
                    if k.strip() not in os.environ:
                        os.environ[k.strip()] = v.strip().strip('"').strip("'")


def main() -> None:
    _load_dotenv_if_present()
    token = os.environ.get("TELEGRAM_BOT_TOKEN", "").strip()
    if not token:
        raise RuntimeError(
            "Falta la variable de entorno TELEGRAM_BOT_TOKEN. "
            "Configúrala en .env o antes de iniciar el bot."
        )

    app = Application.builder().token(token).build()

    app.add_handler(CommandHandler("start", start_command))
    app.add_handler(CommandHandler("peque", set_child_name_command))
    app.add_handler(CommandHandler("analisis", analisis_command))
    app.add_handler(CommandHandler("registrar_bambi", registrar_bambi_command))
    app.add_handler(CommandHandler("bitacora", bitacora_command))
    app.add_handler(CommandHandler("exportar", exportar_command))
    app.add_handler(CommandHandler("escalera", escalera_command))
    app.add_handler(CommandHandler("bambi", bambi_command))
    app.add_handler(CommandHandler("redes", redes_command))
    app.add_handler(CallbackQueryHandler(handle_callback_query))
    app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, handle_free_text))

    logger.info("Bot «El Autismo Sobre La Mesa» (@TEA_SobreLaMesa_Bot) iniciado y escuchando mensajes...")
    app.run_polling(allowed_updates=Update.ALL_TYPES)


if __name__ == "__main__":
    main()
