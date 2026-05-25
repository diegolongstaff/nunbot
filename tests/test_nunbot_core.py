import csv
import unittest
from pathlib import Path

import pandas as pd


class TestNunbotCore(unittest.TestCase):
    def test_normalize_search_query_strips_accents_and_punctuation(self):
        from nunbot_core import normalize_search_query

        self.assertEqual(
            normalize_search_query("  Fractura de cadera, con enclavado!  "),
            "fractura de cadera con enclavado",
        )

    def test_validate_search_query_rejects_low_signal_input(self):
        from nunbot_core import validate_search_query

        ok, message = validate_search_query("abc")
        self.assertFalse(ok)
        self.assertIn("más específica", message)

    def test_validate_search_query_rejects_excessively_long_input(self):
        from nunbot_core import validate_search_query

        ok, message = validate_search_query("fractura " * 100)
        self.assertFalse(ok)
        self.assertIn("demasiado larga", message)

    def test_rank_local_candidates_prefers_exact_keyword_match(self):
        from nunbot_core import rank_local_candidates

        df = pd.DataFrame(
            [
                {
                    "Código": "MS.01.01",
                    "Descripción": "Infiltración diagnóstica o terapéutica",
                    "Región": "MS",
                    "Palabras clave": "diagnóstica, infiltración, terapéutica",
                },
                {
                    "Código": "PC.01.01",
                    "Descripción": "Reducción de fractura de cadera",
                    "Región": "PC",
                    "Palabras clave": "cadera, fractura, reducción",
                },
            ]
        )

        ranked = rank_local_candidates("fractura de cadera", df, region="PC", limit=2)
        self.assertEqual(ranked[0]["Código"], "PC.01.01")

    def test_validate_region_response_rejects_invalid_region(self):
        from nunbot_core import validate_region_response

        region, confidence, reason = validate_region_response({"region": "XX", "confianza": 0.9, "motivo": "test"})
        self.assertEqual(region, "")
        self.assertEqual(confidence, 0)
        self.assertEqual(reason, "")

    def test_validate_suggested_codes_filters_unknown_codes(self):
        from nunbot_core import validate_suggested_codes

        df = pd.DataFrame([
            {"Código": "MS.01.01"},
            {"Código": "PC.01.01"},
        ])
        suggestions = [
            {"codigo": "MS.01.01", "confianza": 1.2, "motivo": "ok"},
            {"codigo": "NO.EXISTE", "confianza": 0.8, "motivo": "bad"},
        ]

        cleaned = validate_suggested_codes(suggestions, df)
        self.assertEqual(len(cleaned), 1)
        self.assertEqual(cleaned[0]["codigo"], "MS.01.01")
        self.assertEqual(cleaned[0]["confianza"], 1.0)

    def test_check_runtime_health_reports_missing_requirements(self):
        from unittest.mock import patch

        from nunbot_core import check_runtime_health

        with patch.dict("os.environ", {}, clear=True):
            issues = check_runtime_health(data_path=Path("/tmp/does-not-exist.csv"))

        self.assertTrue(any("archivo de datos" in issue for issue in issues))
        self.assertTrue(any("OPENAI_API_KEY" in issue for issue in issues))

    def test_check_runtime_health_passes_when_requirements_exist(self):
        from unittest.mock import patch

        from nunbot_core import check_runtime_health

        with patch.dict("os.environ", {"OPENAI_API_KEY": "test-key"}, clear=True):
            issues = check_runtime_health(data_path=Path("nun_procedimientos.csv"))

        self.assertEqual(issues, [])

    def test_csv_path_points_to_repo_data_file(self):
        from nunbot_core import default_data_path

        self.assertEqual(default_data_path().name, "nun_procedimientos.csv")
        self.assertTrue(default_data_path().exists())

    def test_nun_procedimientos_csv_matches_march_2026_reference_values(self):
        expected = {
            "1": ("$101,398.00", "$0.00", "$101,398.00"),
            "2": ("$204,137.00", "$40,810.00", "$244,947.00"),
            "3": ("$348,340.00", "$70,214.00", "$418,554.00"),
            "4": ("$503,244.00", "$100,656.00", "$603,900.00"),
            "5": ("$813,148.00", "$162,608.00", "$1,138,364.00"),
            "6": ("$1,357,240.00", "$271,418.00", "$1,900,076.00"),
            "7": ("$1,659,846.00", "$330,678.00", "$2,321,202.00"),
            "8": ("$2,124,771.00", "$424,953.00", "$2,974,677.00"),
            "9": ("$2,722,360.00", "$544,480.00", "$3,811,320.00"),
            "10": ("$3,817,734.00", "$763,546.00", "$5,344,826.00"),
        }

        with Path("nun_procedimientos.csv").open(newline="", encoding="utf-8") as fh:
            rows = list(csv.DictReader(fh))

        self.assertGreater(len(rows), 0)

        for row in rows:
            self.assertIn(row["Complejidad"], expected)
            self.assertEqual(
                (row["Cirujano"], row["Ayudantes"], row["Total"]),
                expected[row["Complejidad"]],
            )

    def test_search_nun_codes_falls_back_when_region_inference_fails(self):
        from unittest.mock import patch
        from typing import Any, cast

        from nunbot_core import search_nun_codes

        class BrokenRegionClient:
            def with_options(self, **kwargs):
                return self

            @property
            def chat(self):
                class Chat:
                    @property
                    def completions(self):
                        class Completions:
                            def create(self, *args, **kwargs):
                                raise RuntimeError("openai down")

                        return Completions()

                return Chat()

        df = pd.DataFrame(
            [
                {
                    "Código": "PC.10.01",
                    "Descripción": "Reducción cerrada de fractura de cadera",
                    "Región": "PC",
                    "Palabras clave": "cadera, fractura, reducción",
                    "Cirujano": 100,
                    "Ayudantes": 50,
                    "Total": 150,
                },
                {
                    "Código": "MS.10.01",
                    "Descripción": "Reducción de fractura de muñeca",
                    "Región": "MS",
                    "Palabras clave": "muñeca, fractura, reducción",
                    "Cirujano": 90,
                    "Ayudantes": 45,
                    "Total": 135,
                },
            ]
        )

        with patch("nunbot_core.determine_region_locally", return_value=("", 0.0, "")), patch(
            "nunbot_core.infer_region_with_openai", side_effect=RuntimeError("openai down")
        ):
            region, confidence, reason, suggestions, local_candidates, used_fallback = search_nun_codes(
                cast(Any, BrokenRegionClient()),
                "descripción sin pistas anatómicas claras",
                df,
            )

        self.assertEqual(region, "")
        self.assertEqual(confidence, 0.0)
        self.assertIn("búsqueda determinística", reason)
        self.assertTrue(used_fallback)
        self.assertTrue(suggestions)
        self.assertTrue(local_candidates)

    def test_search_nun_codes_prefers_local_region_detection_before_openai(self):
        from unittest.mock import patch

        from nunbot_core import search_nun_codes

        df = pd.DataFrame(
            [
                {
                    "Código": "PC.10.01",
                    "Descripción": "Reducción cerrada de fractura de cadera",
                    "Región": "PC",
                    "Palabras clave": "cadera, fractura, reducción",
                    "Cirujano": 100,
                    "Ayudantes": 50,
                    "Total": 150,
                },
                {
                    "Código": "MS.10.01",
                    "Descripción": "Reducción de fractura de muñeca",
                    "Región": "MS",
                    "Palabras clave": "muñeca, fractura, reducción",
                    "Cirujano": 90,
                    "Ayudantes": 45,
                    "Total": 135,
                },
            ]
        )

        class DummyClient:
            pass

        dummy_client = DummyClient()

        with patch("nunbot_core.determine_region_locally", return_value=("PC", 0.88, "Inferido localmente")) as local_region, patch(
            "nunbot_core.infer_region_with_openai"
        ) as openai_region, patch(
            "nunbot_core.rank_codes_with_openai",
            return_value=[{"codigo": "PC.10.01", "confianza": 0.91, "motivo": "Coincidencia exacta"}],
        ) as openai_rank:
            region, confidence, reason, suggested_codes, local_candidates, used_fallback = search_nun_codes(
                dummy_client,
                "fractura de cadera con reducción",
                df,
            )

        local_region.assert_called_once()
        openai_region.assert_not_called()
        openai_rank.assert_called_once()
        self.assertEqual(region, "PC")
        self.assertEqual(confidence, 0.88)
        self.assertEqual(reason, "Inferido localmente")
        self.assertEqual(suggested_codes[0]["codigo"], "PC.10.01")
        self.assertFalse(used_fallback)
        self.assertGreaterEqual(len(local_candidates), 1)

    def test_build_search_prompt_only_includes_provided_candidates(self):
        from nunbot_core import build_search_prompt

        candidates = pd.DataFrame(
            [
                {
                    "Código": "PC.01.01",
                    "Descripción": "Reducción de fractura de cadera con osteosíntesis y seguimiento prolongado",
                    "Palabras clave": "cadera, fractura, reducción, osteosíntesis, seguimiento",
                },
                {
                    "Código": "PC.01.02",
                    "Descripción": "Osteosíntesis de cadera",
                    "Palabras clave": "cadera, osteosíntesis",
                },
                {
                    "Código": "PC.01.01",
                    "Descripción": "Texto duplicado que no debería llegar al prompt",
                    "Palabras clave": "duplicado",
                },
            ]
        )
        prompt = build_search_prompt("fractura de cadera", candidates)
        user_message = prompt[1]["content"]
        self.assertIn("fractura de cadera", user_message)
        self.assertIn("PC.01.01 | Reducción de fractura de cadera con osteosíntesis", user_message)
        self.assertIn("Palabras clave:", user_message)
        self.assertIn("PC.01.02 | Osteosíntesis de cadera", user_message)
        self.assertNotIn("Texto duplicado que no debería llegar al prompt", user_message)
        self.assertNotIn("MS.01.01", user_message)
