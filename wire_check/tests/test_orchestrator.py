import unittest
import sys
import os

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '../..')))

from wire_check.agents.orchestrator import run_wire_check_workflow
from wire_check.models import IntakeRequest

class TestOrchestratorWorkflow(unittest.TestCase):
    def test_clean_workflow_e2e(self):
        intake = IntakeRequest(
            company_name="Safe Clean Supplier Ltd",
            country="DE",
            iban="DE89370400440532013000",
            bank_country="DE",
            invoice_email_domain="safesupplier.com",
            amount=10000.0,
            recent_bank_change=False
        )
        response = run_wire_check_workflow(intake)
        self.assertIsNotNone(response)
        self.assertIn(response.decision.decision, ["PROCEED", "CALL-BACK", "HOLD"])
        print(f"Test clean workflow result decision: {response.decision.decision}")

    def test_fraud_workflow_e2e(self):
        intake = IntakeRequest(
            company_name="Acme Terrorist Corp",
            country="XX",
            iban="DE89370400440532013000",
            bank_country="DE",
            invoice_email_domain="suspicious-new-domain.com",
            amount=75000.0,
            recent_bank_change=True
        )
        response = run_wire_check_workflow(intake)
        self.assertEqual(response.decision.decision, "HOLD")
        print(f"Test fraud/sanctions workflow result decision: {response.decision.decision}")

if __name__ == '__main__':
    unittest.main()
