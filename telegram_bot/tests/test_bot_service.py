"""
Suite de Pruebas Automatizadas (Gate 1 — IN2TECHMX)
Verifica de manera determinista:
1. Persistencia SQLite (creación de perfil, inserción de registros en bitácora, estadísticas y exportación CSV UTF-8 con BOM).
2. Clasificación en lenguaje natural (detección de alimento, escalón sensorial, textura, estado emocional e intención).
3. Respuestas fundamentadas en el TFM de la Mtra. Maria Cindy Morales Alarcón.
"""

import os
import sys
import tempfile
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from ai_assistant import TeaAdvisorService, parse_user_message
from database import BitacoraRepository
from knowledge_base import TFM_KNOWLEDGE_BASE


class TestTelegramBotService(unittest.TestCase):
    def setUp(self) -> None:
        self.temp_dir = tempfile.TemporaryDirectory()
        self.db_path = Path(self.temp_dir.name) / "test_bitacora.db"
        self.repo = BitacoraRepository(self.db_path)

    def tearDown(self) -> None:
        self.temp_dir.cleanup()

    def test_profile_and_bitacora_persistence(self) -> None:
        user_id = 100200300
        profile = self.repo.upsert_profile(user_id=user_id, username="mama_mia", child_name="Mía")
        self.assertEqual(profile["child_name"], "Mía")

        entry = self.repo.add_entry(
            user_id=user_id,
            food_item="Brócoli",
            sensory_step="Tocó",
            raw_notes="Hoy tocó el brócoli al vapor con el dedo y estuvo tranquila",
            texture_notes="Al vapor",
            mood_state="En calma",
        )
        self.assertEqual(entry.food_item, "Brócoli")
        self.assertEqual(entry.sensory_step, "Tocó")
        self.assertEqual(entry.child_name, "Mía")

        recent = self.repo.get_recent_entries(user_id)
        self.assertEqual(len(recent), 1)
        self.assertEqual(recent[0].mood_state, "En calma")

        stats = self.repo.get_summary_stats(user_id)
        self.assertEqual(stats["total_entries"], 1)
        self.assertEqual(stats["unique_foods_count"], 1)
        self.assertEqual(stats["steps_breakdown"]["Tocó"], 1)

    def test_csv_export_format(self) -> None:
        user_id = 999888
        self.repo.upsert_profile(user_id=user_id, child_name="Lucas")
        self.repo.add_entry(
            user_id=user_id,
            food_item="Fresa",
            sensory_step="Olió",
            raw_notes="Olió una fresa fresca en el desayuno",
            texture_notes="Crudo",
            mood_state="Curioso",
        )
        csv_bytes = self.repo.export_user_csv(user_id)
        self.assertTrue(csv_bytes.startswith(b"\xef\xbb\xbf"))  # UTF-8 BOM para Excel
        csv_text = csv_bytes.decode("utf-8-sig")
        self.assertIn("Lucas", csv_text)
        self.assertIn("Fresa", csv_text)
        self.assertIn("Olió", csv_text)

    def test_nlp_message_parser_log_entry(self) -> None:
        msg = "Hoy en la comida probó zanahoria al vapor y estuvo muy tranquilo"
        parsed = parse_user_message(msg)
        self.assertEqual(parsed.intent, "LOG_ENTRY")
        self.assertEqual(parsed.food_item, "Zanahoria")
        self.assertEqual(parsed.sensory_step, "Probó")
        self.assertIn("vapor", parsed.texture_notes.lower())
        self.assertEqual(parsed.mood_state, "En calma")

    def test_nlp_message_parser_question_and_both(self) -> None:
        q_msg = "¿Por qué rechaza las sopas con trozos y texturas mixtas?"
        parsed_q = parse_user_message(q_msg)
        self.assertEqual(parsed_q.intent, "QUESTION")

        both_msg = "Hoy rechazó el plátano blando y lloró, ¿qué puedo hacer?"
        parsed_both = parse_user_message(both_msg)
        self.assertEqual(parsed_both.intent, "BOTH")
        self.assertEqual(parsed_both.sensory_step, "Rechazó")

    def test_advisor_response_grounded_in_tfm(self) -> None:
        advisor = TeaAdvisorService(gemini_api_key="")  # Fuerza motor determinista local TFM
        msg = "Hoy tocó la manzana cruda y estuvo curioso. ¿Cómo uso el alimento puente con las texturas?"
        parsed = parse_user_message(msg)
        response = advisor.generate_response(msg, parsed, [], child_name="Mía")
        self.assertIn("Mía", response)
        self.assertIn("Manzana", response)
        self.assertIn("Tocó", response)
        self.assertIn("texturas", response.lower())
        self.assertIn("Mtra. Maria Cindy Morales Alarcón", TFM_KNOWLEDGE_BASE)

    def test_clinical_analysis_and_bambi_score(self) -> None:
        user_id = 777111
        self.repo.upsert_profile(user_id=user_id, child_name="Mateo")
        self.repo.add_entry(
            user_id=user_id,
            food_item="Galleta",
            sensory_step="Comió",
            raw_notes="Hoy comió galleta crujiente muy tranquilo",
            texture_notes="Crujiente / seco",
            mood_state="En calma",
        )
        self.repo.add_entry(
            user_id=user_id,
            food_item="Puré de calabaza",
            sensory_step="Rechazó",
            raw_notes="Rechazó el puré de calabaza con grumos y tuvo sobrecarga",
            texture_notes="Con grumos",
            mood_state="Incómodo / sobrecarga",
        )
        bambi = self.repo.add_bambi_score(
            user_id=user_id,
            total_score=46,
            refusal_score=18,
            selectivity_score=18,
            disruptive_score=10,
        )
        self.assertTrue(bambi["clinical_flag"])
        latest_bambi = self.repo.get_latest_bambi_score(user_id)
        self.assertIsNotNone(latest_bambi)
        self.assertEqual(latest_bambi["total_score"], 46)

        advisor = TeaAdvisorService(gemini_api_key="")
        entries = self.repo.get_recent_entries(user_id, limit=20)
        analysis = advisor.generate_clinical_analysis(
            entries=entries,
            child_name="Mateo",
            latest_bambi=latest_bambi,
        )
        self.assertIn("Mateo", analysis)
        self.assertIn("46 / 90", analysis)
        self.assertIn("Alimento Puente", analysis)
        self.assertIn("Galleta", analysis)
        self.assertIn("Puré de calabaza", analysis)

    def test_bbm_interactive_questionnaire_scoring(self) -> None:
        from questionnaire_bbm import (
            BBM_QUESTIONNAIRE_ITEMS,
            compute_bambi_bbm_results,
            format_bbm_assessment_report,
            format_question_prompt,
        )

        self.assertEqual(len(BBM_QUESTIONNAIRE_ITEMS), 22)

        # Caso de mínimo problema: ítems directos en 1 (Nunca), ítems inversos (3, 9, 10, 15) en 5 (Siempre)
        min_answers = {i: 1 for i in range(1, 23)}
        for rev_item in (3, 9, 10, 15):
            min_answers[rev_item] = 5
        res_min = compute_bambi_bbm_results(min_answers)
        self.assertEqual(res_min["total_score"], 18)
        self.assertFalse(res_min["clinical_flag"])

        # Caso de alto problema: ítems directos en 4, ítems inversos en 1 (se invierten a 5), BBM en 4
        high_answers = {i: 4 for i in range(1, 23)}
        for rev_item in (3, 9, 10, 15):
            high_answers[rev_item] = 1
        res_high = compute_bambi_bbm_results(high_answers)
        # 14 ítems directos * 4 = 56; 4 ítems inversos * 5 = 20 -> Total = 76
        self.assertEqual(res_high["total_score"], 76)
        self.assertTrue(res_high["clinical_flag"])
        self.assertEqual(res_high["bbm_gi"], 4)

        prompt_q3 = format_question_prompt(2, "Mía")
        self.assertIn("Pregunta 3 de 22", prompt_q3)
        self.assertIn("Ítem Inverso", prompt_q3)

        report = format_bbm_assessment_report(res_high, "Mía")
        self.assertIn("76 / 90 puntos", report)
        self.assertIn("BBM-014", report)
        self.assertIn("SemAlTea", report)


if __name__ == "__main__":
    unittest.main()
