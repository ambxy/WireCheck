import unittest
from wire_check.agents.fraud import validate_iban, check_bank_country_match, check_lookalike, run_fraud_checks
from wire_check.models import IntakeRequest, EntityResult

class TestFraudAgent(unittest.TestCase):
    def test_validate_iban_valid(self):
        self.assertTrue(validate_iban("DE89370400440532013000"))

    def test_validate_iban_invalid(self):
        self.assertFalse(validate_iban("DE00370400440532013000"))
        self.assertFalse(validate_iban("INVALIDIBAN"))

    def test_bank_country_match(self):
        self.assertTrue(check_bank_country_match("DE89370400440532013000", "DE"))
        self.assertFalse(check_bank_country_match("FR7630002005500000123456789", "DE"))

    def test_check_lookalike(self):
        is_la, target = check_lookalike("suppliir.com", "https://supplier.com")
        self.assertTrue(is_la)
        self.assertEqual(target, "supplier.com")

        is_la, target = check_lookalike("supplier.co", "https://supplier.com")
        self.assertTrue(is_la)
        self.assertEqual(target, "supplier.com")

        is_la, target = check_lookalike("supplier.com", "supplier.com")
        self.assertFalse(is_la)

    def test_run_fraud_checks(self):
        intake = IntakeRequest(
            company_name="Acme Corp",
            country="DE",
            iban="DE89370400440532013000",
            bank_country="DE",
            invoice_email_domain="acme-secure.com",
            amount=15000.0,
            recent_bank_change=True
        )
        entity = EntityResult(
            canonical_name="Acme Corporation GmbH",
            status="verified",
            website="acme.com"
        )
        res = run_fraud_checks(intake, entity)
        self.assertTrue(res.iban_valid)
        self.assertTrue(res.bank_country_match)
        self.assertTrue(len(res.fraud_signals) > 0)

if __name__ == '__main__':
    unittest.main()
