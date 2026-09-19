import unittest
from datetime import datetime, timezone

from app.schemas.analysis import (
    CandidateProfile,
    SemanticAssessment,
    VacancyCriteria,
    VacancyCriteriaDraft,
)
from app.services.affinity import AffinityEngine, calculate_affinity, normalize_weights, sanitize_profile
from app.services.llm_client import (
    CANDIDATE_INSTRUCTIONS,
    VACANCY_INSTRUCTIONS,
    LLMProviderError,
    OpenAIAnalysisClient,
)


class FakeProvider:
    model = "fake-model-v1"

    def extract_vacancy_criteria(self, title, description, requirements):
        return VacancyCriteriaDraft(criteria=[
            {"name": "Python", "kind": "SKILL", "description": "Programación Python", "importance": 3},
            {"name": "Diseño de APIs", "kind": "ACTIVITY", "description": "Crear APIs", "importance": 1},
        ])

    def extract_candidate_profile(self, raw_text):
        return CandidateProfile(claims=[
            {"name": "Python", "kind": "SKILL", "evidence_quote": "Desarrollé servicios con Python", "section": "Experiencia"},
            {"name": "Dato inventado", "kind": "SKILL", "evidence_quote": "Esta cita no existe", "section": "Otro"},
        ])

    def match(self, criteria, profile):
        return SemanticAssessment(matches=[
            {"criterion_index": 0, "claim_index": 0, "strength": 1.0, "rationale": "Coincidencia directa."},
            {"criterion_index": 1, "claim_index": 0, "strength": 0.5, "rationale": "La actividad está parcialmente evidenciada."},
        ])


class AffinityEngineTests(unittest.TestCase):
    def setUp(self):
        self.engine = AffinityEngine(FakeProvider())
        self.raw_text = "Experiencia\nDesarrollé servicios con Python durante 10 años."

    def test_normalizes_weights_to_one_hundred(self):
        criteria = self.engine.extract_criteria("Backend", "APIs", "Python")
        self.assertEqual([item.weight for item in criteria.criteria], [75.0, 25.0])
        self.assertEqual(sum(item.weight for item in criteria.criteria), 100)

    def test_discards_untraceable_llm_evidence(self):
        profile = self.engine.extract_profile(self.raw_text)
        self.assertEqual(len(profile.claims), 1)
        self.assertEqual(profile.claims[0].name, "Python")

    def test_calculates_deterministic_weighted_score_and_evidence(self):
        criteria = self.engine.extract_criteria("Backend", "APIs", "Python")
        profile = self.engine.extract_profile(self.raw_text)
        instant = datetime(2026, 1, 1, tzinfo=timezone.utc)

        first = self.engine.analyze(criteria, profile, calculated_at=instant)
        second = self.engine.analyze(criteria, profile, calculated_at=instant)

        self.assertEqual(first, second)
        score, evidence = first
        self.assertEqual(score, 88)
        self.assertEqual(evidence["factors"][0]["evidence_quote"], "Desarrollé servicios con Python")
        self.assertNotIn("10 años", str(evidence))
        self.assertIn("excluye educación y duración", evidence["methodology"])

    def test_empty_verified_profile_scores_zero_without_match_call(self):
        criteria = self.engine.extract_criteria("Backend", "APIs", "Python")
        score, evidence = self.engine.analyze(criteria, CandidateProfile(claims=[]))
        self.assertEqual(score, 0)
        self.assertEqual(len(evidence["uncovered"]), 2)

    def test_rejects_invalid_llm_indexes(self):
        criteria = normalize_weights(VacancyCriteria(criteria=[
            {"name": "Python", "kind": "SKILL", "description": "", "weight": 100}
        ]))
        profile = CandidateProfile(claims=[
            {"name": "Python", "kind": "SKILL", "evidence_quote": "Python", "section": "Habilidades"}
        ])
        bad = SemanticAssessment(matches=[
            {"criterion_index": 0, "claim_index": 4, "strength": 1.0, "rationale": "Inválido"}
        ])
        with self.assertRaises(LLMProviderError):
            calculate_affinity(criteria, profile, bad, model="fake")

    def test_prompt_explicitly_excludes_education_and_years(self):
        combined = (VACANCY_INSTRUCTIONS + CANDIDATE_INSTRUCTIONS).casefold()
        self.assertIn("títulos", combined)
        self.assertIn("años de experiencia", combined)


class OpenAIAdapterTests(unittest.TestCase):
    def test_uses_strict_non_stored_structured_response(self):
        captured = {}

        class FakeResponses:
            def create(self, **kwargs):
                captured.update(kwargs)
                return type("Response", (), {"output_text": '{"claims": []}'})()

        client = object.__new__(OpenAIAnalysisClient)
        client.model = "fake-model"
        client.client = type("Client", (), {"responses": FakeResponses()})()

        result = client.extract_candidate_profile("CV")

        self.assertEqual(result.claims, [])
        self.assertFalse(captured["store"])
        self.assertEqual(captured["temperature"], 0)
        self.assertTrue(captured["text"]["format"]["strict"])
        self.assertFalse(captured["text"]["format"]["schema"]["additionalProperties"])


if __name__ == "__main__":
    unittest.main()
