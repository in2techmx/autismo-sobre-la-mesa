"""
Módulo de Evaluación Interactiva BAMBI + Base Bibliográfica Magistral (BBMagistral BBM-001 a BBM-030)
Basado en el TFM de la Mtra. Maria Cindy Morales Alarcón (MUNA — Universidad de Alicante, 2026),
el archivo BAMBI.txt y el compendio científico BBMagistral.pdf (30 estudios internacionales).

Permite que el bot de Telegram (@TEA_SobreLaMesa_Bot) aplique paso a paso el cuestionario
directamente en el chat mediante botones interactivos (Escala Likert 1 a 5), invierta
automáticamente los ítems positivos (3, 9, 10 y 15), calcule las 3 dimensiones del BAMBI y los
4 ejes clínicos de la BBMagistral, guarde el resultado en SQLite y emita el informe de apoyos.
"""

from dataclasses import dataclass
from typing import Dict, List, Optional


LIKERT_OPTIONS = [
    (1, "1️⃣ Nunca / Raramente (1 pto)"),
    (2, "2️⃣ Pocas veces / Seldom (2 ptos)"),
    (3, "3️⃣ A veces (3 ptos)"),
    (4, "4️⃣ A menudo (4 ptos)"),
    (5, "5️⃣ Siempre / Casi siempre (5 ptos)"),
]


@dataclass(frozen=True)
class QuestionnaireItem:
    number: int
    code: str
    factor_key: str
    factor_label: str
    question_text: str
    reverse: bool = False
    bbm_reference: str = "BAMBI (Lukens & Linscheid, 2008; Soba et al., 2026 [BBM-001])"


# 18 Ítems oficiales del Inventario BAMBI (Brief Autism Mealtime Behavior Inventory)
# + 4 Ítems clínicos integradores de la Base Bibliográfica Magistral (BBMagistral.pdf: BBM-001 a BBM-030)
BBM_QUESTIONNAIRE_ITEMS: List[QuestionnaireItem] = [
    # --- PARTE I: INVENTARIO BAMBI (Ítems 1 al 18, Rango 18-90 ptos, Corte clínico >= 34) ---
    QuestionnaireItem(
        number=1,
        code="BAMBI-01",
        factor_key="refusal",
        factor_label="🧃 Rechazo Alimentario (Food Refusal)",
        question_text="¿Llora o grita durante las comidas cuando se le presenta la comida?",
        reverse=False,
        bbm_reference="BAMBI — BBM-001 (Soba et al., 2026) / BBM-009 (Parkar & Kapoor, 2026)",
    ),
    QuestionnaireItem(
        number=2,
        code="BAMBI-02",
        factor_key="refusal",
        factor_label="🧃 Rechazo Alimentario (Food Refusal)",
        question_text="¿Gira la cara o aparta el cuerpo del plato cuando se le acerca la cuchara o el alimento?",
        reverse=False,
        bbm_reference="BAMBI — BBM-001 / BBM-008 (Tereshko & Martino, 2025)",
    ),
    QuestionnaireItem(
        number=3,
        code="BAMBI-03",
        factor_key="selectivity",
        factor_label="🥦 Selectividad Alimentaria (Ítem Inverso 🔄)",
        question_text="¿Permanece sentado/a en la mesa hasta terminar la comida?",
        reverse=True,
        bbm_reference="BAMBI Ítem Inverso #3 — BAMBI.txt / BBM-001",
    ),
    QuestionnaireItem(
        number=4,
        code="BAMBI-04",
        factor_key="refusal",
        factor_label="🧃 Rechazo Alimentario (Food Refusal)",
        question_text="¿Escupe o expulsa la comida una vez que ha entrado en la boca?",
        reverse=False,
        bbm_reference="BAMBI — BBM-001 / BBM-015 (Karaca et al., 2025)",
    ),
    QuestionnaireItem(
        number=5,
        code="BAMBI-05",
        factor_key="disruptive",
        factor_label="🪑 Conductas Disruptivas en la Mesa",
        question_text="¿Muestra conductas agresivas durante las comidas (golpear, empujar el plato, pellizcar, lanzar objetos)?",
        reverse=False,
        bbm_reference="BAMBI — BBM-011 (Salameh et al., 2026)",
    ),
    QuestionnaireItem(
        number=6,
        code="BAMBI-06",
        factor_key="disruptive",
        factor_label="🪑 Conductas Disruptivas en la Mesa",
        question_text="¿Muestra conductas autolesivas durante las comidas (morderse, golpearse la cabeza o pellizcarse)?",
        reverse=False,
        bbm_reference="BAMBI — BBM-001 / BBM-027 (Tong et al., 2026)",
    ),
    QuestionnaireItem(
        number=7,
        code="BAMBI-07",
        factor_key="refusal",
        factor_label="🧃 Rechazo Alimentario (Food Refusal)",
        question_text="¿Cierra la boca con fuerza o aprieta los labios cuando se le ofrece comida?",
        reverse=False,
        bbm_reference="BAMBI — BBM-001 / BBM-008",
    ),
    QuestionnaireItem(
        number=8,
        code="BAMBI-08",
        factor_key="refusal",
        factor_label="🧃 Rechazo Alimentario (Food Refusal)",
        question_text="¿Tiene arcadas, náuseas o parece a punto de vomitar ante ciertos alimentos, olores o texturas?",
        reverse=False,
        bbm_reference="BAMBI — BBM-003 (Laaraje et al., 2026) / BBM-019 (Zulkifli et al., 2022)",
    ),
    QuestionnaireItem(
        number=9,
        code="BAMBI-09",
        factor_key="selectivity",
        factor_label="🥦 Selectividad Alimentaria (Ítem Inverso 🔄)",
        question_text="¿Está dispuesto/a a probar alimentos nuevos cuando se le ofrecen suavemente?",
        reverse=True,
        bbm_reference="BAMBI Ítem Inverso #9 — BAMBI.txt / BBM-004 (Kawaguchi et al., 2026)",
    ),
    QuestionnaireItem(
        number=10,
        code="BAMBI-10",
        factor_key="selectivity",
        factor_label="🥦 Selectividad Alimentaria (Ítem Inverso 🔄)",
        question_text="¿Acepta comer alimentos de diferentes grupos nutricionales (frutas, verduras, proteínas, cereales)?",
        reverse=True,
        bbm_reference="BAMBI Ítem Inverso #10 — BAMBI.txt / BBM-006 (Chusak et al., 2026)",
    ),
    QuestionnaireItem(
        number=11,
        code="BAMBI-11",
        factor_key="selectivity",
        factor_label="🥦 Selectividad Alimentaria",
        question_text="¿Le disgustan ciertos alimentos y se niega categóricamente a comerlos (sobre todo frutas o verduras)?",
        reverse=False,
        bbm_reference="BAMBI — BBM-005 (Morales-Zepeda et al., 2025) / BBM-017 (Santos et al., 2025)",
    ),
    QuestionnaireItem(
        number=12,
        code="BAMBI-12",
        factor_key="disruptive",
        factor_label="🪑 Conductas Disruptivas en la Mesa",
        question_text="¿Se niega a comer determinados alimentos pero exige comer solo sus alimentos seguros o snacks?",
        reverse=False,
        bbm_reference="BAMBI — BBM-006 (Chusak et al., 2026) / BBM-026 (Schultz et al., 2026)",
    ),
    QuestionnaireItem(
        number=13,
        code="BAMBI-13",
        factor_key="disruptive",
        factor_label="🪑 Conductas Disruptivas en la Mesa",
        question_text="¿Se levanta de la mesa repetidamente o deambula durante el tiempo de la comida?",
        reverse=False,
        bbm_reference="BAMBI — BBM-015 (Karaca et al., 2025 — Procesamiento vestibular)",
    ),
    QuestionnaireItem(
        number=14,
        code="BAMBI-14",
        factor_key="selectivity",
        factor_label="🥦 Selectividad Alimentaria",
        question_text="¿Prefiere que le sirvan exactamente los mismos alimentos en cada comida (repetición de menú)?",
        reverse=False,
        bbm_reference="BAMBI — BBM-026 (Schultz et al., 2026: 57,1% repite menú) / BBM-030 (Wallisch et al., 2026)",
    ),
    QuestionnaireItem(
        number=15,
        code="BAMBI-15",
        factor_key="selectivity",
        factor_label="🥦 Selectividad Alimentaria (Ítem Inverso 🔄)",
        question_text="¿Acepta variedad de texturas (crujientes, suaves, fibrosas, húmedas o con trozos)?",
        reverse=True,
        bbm_reference="BAMBI Ítem Inverso #15 — BAMBI.txt / BBM-005 (78% rechazo por textura)",
    ),
    QuestionnaireItem(
        number=16,
        code="BAMBI-16",
        factor_key="selectivity",
        factor_label="🥦 Selectividad Alimentaria",
        question_text="¿Exige que los alimentos se preparen o sirvan siempre de una forma, marca, color o empaque específico?",
        reverse=False,
        bbm_reference="BAMBI — BBM-025 (Pomoni et al., 2025 FAQ) / BBM-028 (Siracusano et al., 2025: sameness)",
    ),
    QuestionnaireItem(
        number=17,
        code="BAMBI-17",
        factor_key="disruptive",
        factor_label="🪑 Conductas Disruptivas en la Mesa",
        question_text="¿Es inflexible con las rutinas de la mesa (mismo plato, mismo vaso, mismo lugar o sin que los alimentos se toquen)?",
        reverse=False,
        bbm_reference="BAMBI — BBM-005 (Morales-Zepeda et al., 2025: ritualismo) / BBM-030",
    ),
    QuestionnaireItem(
        number=18,
        code="BAMBI-18",
        factor_key="disruptive",
        factor_label="🪑 Conductas Disruptivas en la Mesa",
        question_text="¿Evita mirar, tocar o acercarse a alimentos que no forman parte de su repertorio habitual?",
        reverse=False,
        bbm_reference="BAMBI — BBM-025 (Pomoni et al., 2025: conducta evitativa)",
    ),
    # --- PARTE II: DIMENSIONES CLÍNICAS COMPLEMENTARIAS BBMAGISTRAL (BBM-001 a BBM-030) ---
    QuestionnaireItem(
        number=19,
        code="BBM-SENS",
        factor_key="bbm_sensory",
        factor_label="🔬 BBMagistral — Modalidades Sensoriales (BBM-003 / BBM-026)",
        question_text="¿Rechaza alimentos por su aspecto visual (62,4%), olor intenso (57%) o texturas mixtas/con grumos (44,2%), prefiriendo secos/crujientes?",
        reverse=False,
        bbm_reference="Laaraje et al. (2026) [BBM-003] y Schultz et al. (2026) [BBM-026]",
    ),
    QuestionnaireItem(
        number=20,
        code="BBM-GI",
        factor_key="bbm_gi",
        factor_label="🩺 BBMagistral — Eje Gastrointestinal y Estreñimiento (BBM-013 / BBM-014)",
        question_text="¿Presenta estreñimiento frecuente, dolor abdominal, distensión o reflujo (presente en el 41%–48,7% de niños con TEA y selectividad)?",
        reverse=False,
        bbm_reference="Wang et al. (2022) [BBM-013], Gürgör et al. (2026) [BBM-014] y Kopańska et al. (2025) [BBM-023]",
    ),
    QuestionnaireItem(
        number=21,
        code="BBM-PRAXIS",
        factor_key="bbm_praxis",
        factor_label="👄 BBMagistral — Praxis Motora Oral y Postural (BBM-015 / BBM-029)",
        question_text="¿Muestra fatiga o dificultad para masticar alimentos fibrosos, mover el alimento con la lengua (praxis oral) o mantener el equilibrio sentado?",
        reverse=False,
        bbm_reference="López-Martínez et al. (2025 — Estudio SemAlTea España) [BBM-029] y Karaca et al. (2025) [BBM-015]",
    ),
    QuestionnaireItem(
        number=22,
        code="BBM-FAMILY",
        factor_key="bbm_family",
        factor_label="💛 BBMagistral — Estrés Parental, Sueño y Comedor Escolar (BBM-007 / BBM-011 / BBM-027)",
        question_text="¿La hora de la comida genera alto estrés o desgaste en la familia, o coexiste con dificultades en el comedor escolar o en el sueño?",
        reverse=False,
        bbm_reference="Lee et al. (2026 — AMBQ) [BBM-007], Salameh et al. (2026) [BBM-011] y Tong et al. (2026) [BBM-027]",
    ),
]


def compute_bambi_bbm_results(answers: Dict[int, int]) -> dict:
    """
    Calcula de forma determinista el puntaje del Inventario BAMBI (ítems 1-18, invirtiendo 3, 9, 10 y 15)
    y el perfil clínico multidimensional de la Base Bibliográfica Magistral (ítems 19-22).
    """
    total_bambi = 0
    refusal_score = 0
    selectivity_score = 0
    disruptive_score = 0

    bbm_sensory = 0
    bbm_gi = 0
    bbm_praxis = 0
    bbm_family = 0

    for item in BBM_QUESTIONNAIRE_ITEMS:
        raw_val = answers.get(item.number, 1)
        raw_val = max(1, min(5, int(raw_val)))
        scored_val = (6 - raw_val) if item.reverse else raw_val

        if item.number <= 18:
            total_bambi += scored_val
            if item.factor_key == "refusal":
                refusal_score += scored_val
            elif item.factor_key == "selectivity":
                selectivity_score += scored_val
            elif item.factor_key == "disruptive":
                disruptive_score += scored_val
        else:
            if item.factor_key == "bbm_sensory":
                bbm_sensory = scored_val
            elif item.factor_key == "bbm_gi":
                bbm_gi = scored_val
            elif item.factor_key == "bbm_praxis":
                bbm_praxis = scored_val
            elif item.factor_key == "bbm_family":
                bbm_family = scored_val

    clinical_flag = total_bambi >= 34

    # Clasificación de gravedad clínica según Tereshko & Martino (2025) [BBM-008] y Soba et al. (2026) [BBM-001]
    if total_bambi < 34:
        severity_level = "Selectividad Leve / Picky Eating Esperado (< 34 ptos)"
    elif total_bambi <= 50:
        severity_level = "Selectividad Alimentaria Clínicamente Significativa — Moderada (≥ 34 ptos)"
    else:
        severity_level = "Selectividad Alimentaria Elevada / Rechazo Alimentario Severo (Riesgo ARFID — BBM-023)"

    return {
        "total_score": total_bambi,
        "refusal_score": refusal_score,
        "selectivity_score": selectivity_score,
        "disruptive_score": disruptive_score,
        "clinical_flag": clinical_flag,
        "severity_level": severity_level,
        "bbm_sensory": bbm_sensory,
        "bbm_gi": bbm_gi,
        "bbm_praxis": bbm_praxis,
        "bbm_family": bbm_family,
    }


def format_question_prompt(index: int, child_name: str) -> str:
    """Genera el texto formateado en Markdown para la pregunta actual (0-indexed)."""
    item = BBM_QUESTIONNAIRE_ITEMS[index]
    total_q = len(BBM_QUESTIONNAIRE_ITEMS)
    filled = int(((index + 1) / total_q) * 10)
    bar = "🟩" * filled + "⬜" * (10 - filled)

    section_header = (
        "📋 **PARTE 1: Inventario Clínico BAMBI (Ítems 1–18)**"
        if item.number <= 18
        else "🔬 **PARTE 2: Perfil Multidimensional BBMagistral (Ítems 19–22)**"
    )
    reverse_note = (
        "\n💡 *Nota: Pregunta redactada en positivo (Ítem inverso #{}). Responde con normalidad: el bot invertirá el puntaje automáticamente.*".format(
            item.number
        )
        if item.reverse
        else ""
    )

    return (
        f"{section_header}\n"
        f"👶 Evaluando a: **{child_name}**\n"
        f"{bar} **Pregunta {item.number} de {total_q}**\n\n"
        f"**Dimensión:** {item.factor_label}\n"
        f"📖 *Evidencia:* `{item.bbm_reference}`\n\n"
        f"❓ **{item.question_text}**{reverse_note}\n\n"
        "Selecciona con qué frecuencia ocurre durante las comidas:"
    )


def format_bbm_assessment_report(results: dict, child_name: str) -> str:
    """
    Genera el dictamen completo del cuestionario BAMBI + BBMagistral (BBM-001 a BBM-030)
    con recomendaciones clínicas personalizadas según las dimensiones activadas.
    """
    total = results["total_score"]
    refusal = results["refusal_score"]
    selectivity = results["selectivity_score"]
    disruptive = results["disruptive_score"]
    flag_icon = "🟠" if results["clinical_flag"] else "🟢"

    lines = [
        f"📋 **INFORME DE EVALUACIÓN BAMBI + BBMAGISTRAL PARA {child_name.upper()}**",
        "*Fundamentado en el TFM de la Mtra. Maria Cindy Morales Alarcón (UA/MUNA, 2026) y los 30 estudios de BBMagistral*\n",
        f"{flag_icon} **Puntuación Total BAMBI (18 ítems):** **`{total} / 90 puntos`**",
        f"• **Punto de corte clínico (≥ 34 ptos):** {results['severity_level']}",
        "• *(Ítems inversos 3, 9, 10 y 15 corregidos automáticamente)*\n",
        "📊 **Desglose por las 3 Dimensiones del BAMBI:**",
        f"1️⃣ 🧃 **Rechazo Alimentario (Food Refusal):** `{refusal} / 25 ptos` ({int(refusal/25*100)}%)",
        f"2️⃣ 🥦 **Selectividad y Rigidez Alimentaria:** `{selectivity} / 35 ptos` ({int(selectivity/35*100)}%)",
        f"3️⃣ 🪑 **Conductas Disruptivas en la Mesa:** `{disruptive} / 30 ptos` ({int(disruptive/30*100)}%)\n",
        "🔬 **Perfil Multidimensional BBMagistral (BBM-001 a BBM-030):**",
        f"• **Reactividad Sensorial Visual/Olfativa/Texturas (BBM-003/026):** `{results['bbm_sensory']} / 5`",
        f"• **Riesgo Gastrointestinal y Estreñimiento (BBM-013/014):** `{results['bbm_gi']} / 5`",
        f"• **Praxis Motora Oral y Sistema Vestibular (BBM-015/029):** `{results['bbm_praxis']} / 5`",
        f"• **Impacto en Estrés Parental, Sueño y Escuela (BBM-007/011/027):** `{results['bbm_family']} / 5`\n",
        "🛠️ **Indicaciones Clínicas y Apoyos Personalizados según tu Evaluación:**",
    ]

    # Recomendaciones dinámicas basadas en los puntajes específicos del niño
    rec_num = 1
    if selectivity >= 18 or results["bbm_sensory"] >= 3:
        lines.append(
            f"{rec_num}️⃣ **Desensibilización Sensorial y Alimento Puente (BBM-003 Laaraje, BBM-004 Kawaguchi, BBM-016 Breda):** "
            "Predomina la hiperreactividad a texturas/olores/presentación visual y la insistencia en la invarianza (*sameness*). "
            "No mezcles texturas; sirve los alimentos separados visualmente, respeta su alimento seguro (ej. crujiente/seco según BBM-026) "
            "y aplica el método *Sapere* y *Food Chaining* cambiando solo una propiedad sensorial a la vez."
        )
        rec_num += 1

    if refusal >= 12 or results["clinical_flag"]:
        lines.append(
            f"{rec_num}️⃣ **Escalera Sensorial sin Coacción (BBM-008 Tereshko, BBM-010 Mirizzi, BBM-018 Akyurek):** "
            "Evita cualquier presión o manejo contingente forzado (BBM-010 demuestra que el control coercitivo incrementa el rechazo). "
            "Usa un «plato de aprendizaje» auxiliar para trabajar primero tolerancia visual, tacto con tenedor y olfato antes de esperar ingestión."
        )
        rec_num += 1

    if results["bbm_gi"] >= 3:
        lines.append(
            f"{rec_num}️⃣ **Valoración Gastrointestinal Prioritaria (BBM-013 Wang, BBM-014 Gürgör, BBM-023 Kopańska):** "
            "Reportaste indicadores digestivos/estreñimiento. La evidencia demuestra correlación significativa entre el puntaje BAMBI y el estreñimiento funcional ($r=0,353$). "
            "Consulta con pediatría y nutrición para descartar dolor abdominal o reflujo que esté condicionando el rechazo a comer."
        )
        rec_num += 1

    if results["bbm_praxis"] >= 3 or disruptive >= 15:
        lines.append(
            f"{rec_num}️⃣ **Terapia Ocupacional: Praxis Oral y Soporte Postural/Vestibular (BBM-015 Karaca, BBM-024 Nakaoka, BBM-029 López-Martínez):** "
            "El estudio español *SemAlTea (BBM-029)* documenta que el 80,7% de niños con problemas de participación alimentaria presenta alteraciones de praxis oral, "
            "y *BBM-015* confirma el rol del sistema vestibular. Asegura apoyo firme de los pies en la silla y solicita valoración de Terapia Ocupacional / Logopedia Miofuncional."
        )
        rec_num += 1

    if results["bbm_family"] >= 3:
        lines.append(
            f"{rec_num}️⃣ **Cuidado al Cuidador y Coordinación con Comedor Escolar (BBM-002 Conti FOOD-AUT, BBM-007 Lee, BBM-011 Salameh):** "
            "El estrés parental se correlaciona fuertemente con el BAMBI ($r=0,78$). Coordina con la escuela el uso de sus utensilios familiares y anticipación visual (BBM-024 logró pasar de 4 a 24 alimentos aceptados en escuela), "
            "y evita usar suplementos sin prescripción nutricional individualizada (BBM-011 / BBM-012 / BBM-017)."
        )
        rec_num += 1

    if rec_num == 1:
        lines.append(
            "1️⃣ **Mantenimiento Positivo y Exposición Lúdica (BBM-004 / BBM-016):** "
            "El puntaje se encuentra en rango leve (< 34 ptos). Continúa involucrando a tu peque en actividades culinarias sencillas y registrando sus avances en la bitácora."
        )

    lines.append(
        "\n✅ *Este resultado ya quedó guardado en el expediente de tu peque. Cuando escribas `/analisis` se cruzará automáticamente con tus registros diarios de comida.*"
    )
    return "\n".join(lines)
