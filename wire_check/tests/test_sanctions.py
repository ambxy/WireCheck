import unittest
import sys
import os

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '../..')))

from wire_check.agents.sanctions import screen_entity, normalize_text, compute_similarity
from wire_check.models import EntityResult

class TestSanctionsAgent(unittest.TestCase):
    def test_normalize_text(self):
        self.assertEqual(normalize_text("  Acme  Corp  "), "ACME CORP")
        self.assertEqual(normalize_text("München Gmbh"), "MUNCHEN GMBH")

    def test_compute_similarity(self):
        score = compute_similarity("ACME TERRORIST CORP", "ACME TERRORIST CORP")
        self.assertEqual(score, 100.0)

    def test_screen_entity_clear(self):
        entity = EntityResult(
            canonical_name="Safe Clean Supplier Ltd",
            status="verified",
            website="safesupplier.com"
        )
        res = screen_entity(entity)
        self.assertEqual(res.status, "clear")
        self.assertEqual(len(res.candidates), 0)

    def test_screen_entity_strong_match(self):
        entity = EntityResult(
            canonical_name="ACME TERRORIST CORP",
            status="verified",
            website="acme.com"
        )
        res = screen_entity(entity)
        self.assertEqual(res.status, "strong_match")
        self.assertTrue(res.max_score >= 85.0)
        self.assertEqual(res.candidates[0].list_source, "OFAC")

    def test_screen_entity_near_match(self):
        # Close spelling to "ACME TERRORIST CORP"
        entity = EntityResult(
            canonical_name="ACME TERRORIST CO",
            status="verified",
            website="acme.com"
        )
        res = screen_entity(entity)
        self.assertIn(res.status, ["near_match", "strong_match"])
        self.assertTrue(res.max_score >= 60.0)

if __name__ == '__main__':
    unittest.main()
