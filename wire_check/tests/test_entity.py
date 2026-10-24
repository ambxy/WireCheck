import unittest
import sys
import os

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '../..')))

from wire_check.agents.entity import resolve_entity
from wire_check.models import IntakeRequest

class TestEntityAgent(unittest.TestCase):
    def test_resolve_entity_unverified_fallback(self):
        intake = IntakeRequest(
            company_name="Unknown Mysterious Supplier LLC",
            country="US",
            iban="US1234567890",
            bank_country="US",
            invoice_email_domain="unknown.com",
            amount=5000.0
        )
        res = resolve_entity(intake)
        self.assertEqual(res.status, "unverified")
        self.assertEqual(res.source, "unverified")
        self.assertEqual(res.canonical_name, "Unknown Mysterious Supplier LLC")

if __name__ == '__main__':
    unittest.main()
