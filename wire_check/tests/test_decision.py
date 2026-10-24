import unittest
import sys
import os

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '../..')))

from wire_check.agents.decision import RulesDecisionEngine, generate_callback_script
from wire_check.models import IntakeRequest, EntityResult, SanctionsResult, FraudResult

class TestDecisionEngine(unittest.TestCase):
    def setUp(self):
        self.engine = RulesDecisionEngine()

    def test_clean_proceed(self):
        intake = IntakeRequest(
            company_name="Clean Corp",
            country="DE",
            iban="DE89370400440532013000",
            bank_country="DE",
            invoice_email_domain="cleancorp.com",
            amount=1000.0
        )
        entity = EntityResult(
            canonical_name="Clean Corporation GmbH",
            status="verified",
            website="cleancorp.com",
            source="GLEIF"
        )
        sanctions = SanctionsResult(status="clear", max_score=0.0)
        fraud = FraudResult(
            iban_valid=True,
            bank_country_match=True,
            domain_age_days=500,
            is_young_domain=False,
            is_lookalike=False,
            spf_valid=True,
            dmarc_valid=True
        )

        res = self.engine.decide(intake, entity, sanctions, fraud)
        self.assertEqual(res.decision, "PROCEED")
        self.assertEqual(res.engine_used, "rules_fallback")

    def test_unverified_entity_callback(self):
        intake = IntakeRequest(
            company_name="Unknown Corp",
            country="US",
            iban="US1234567890",
            bank_country="US",
            invoice_email_domain="unknown.com",
            amount=5000.0
        )
        entity = EntityResult(
            canonical_name="Unknown Corp",
            status="unverified",
            source="unverified"
        )
        sanctions = SanctionsResult(status="clear", max_score=0.0)
        fraud = FraudResult(
            iban_valid=True,
            bank_country_match=True,
            domain_age_days=500,
            is_young_domain=False,
            is_lookalike=False,
            spf_valid=True,
            dmarc_valid=True
        )

        res = self.engine.decide(intake, entity, sanctions, fraud)
        self.assertEqual(res.decision, "CALL-BACK")
        self.assertIsNotNone(res.callback_script)

    def test_invalid_iban_hold(self):
        intake = IntakeRequest(
            company_name="Bad IBAN Corp",
            country="DE",
            iban="DE00370400440532013000",
            bank_country="DE",
            invoice_email_domain="badiban.com",
            amount=5000.0
        )
        entity = EntityResult(
            canonical_name="Bad IBAN Corp GmbH",
            status="verified",
            website="badiban.com",
            source="GLEIF"
        )
        sanctions = SanctionsResult(status="clear", max_score=0.0)
        fraud = FraudResult(
            iban_valid=False,
            bank_country_match=True,
            domain_age_days=500,
            is_young_domain=False,
            is_lookalike=False,
            spf_valid=True,
            dmarc_valid=True
        )

        res = self.engine.decide(intake, entity, sanctions, fraud)
        self.assertEqual(res.decision, "HOLD")
        self.assertIn("Invalid IBAN -> HOLD", res.safety_overrides_triggered)

    def test_strong_sanctions_hold(self):
        intake = IntakeRequest(
            company_name="Acme Terrorist Corp",
            country="XX",
            iban="DE89370400440532013000",
            bank_country="DE",
            invoice_email_domain="acme.com",
            amount=5000.0
        )
        entity = EntityResult(
            canonical_name="ACME TERRORIST CORP",
            status="verified",
            website="acme.com",
            source="GLEIF"
        )
        sanctions = SanctionsResult(status="strong_match", max_score=100.0)
        fraud = FraudResult(
            iban_valid=True,
            bank_country_match=True,
            domain_age_days=500,
            is_young_domain=False,
            is_lookalike=False,
            spf_valid=True,
            dmarc_valid=True
        )

        res = self.engine.decide(intake, entity, sanctions, fraud)
        self.assertEqual(res.decision, "HOLD")
        self.assertIn("Strong sanctions match -> HOLD", res.safety_overrides_triggered)

if __name__ == '__main__':
    unittest.main()
