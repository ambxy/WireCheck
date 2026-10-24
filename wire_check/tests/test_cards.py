import unittest
import sys
import os

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '../..')))

from wire_check.cards.templates import create_intake_form_card, create_sanctions_carousel_card, create_fraud_detail_card, create_decision_review_card
from wire_check.models import IntakeRequest, EntityResult, SanctionsResult, FraudResult, DecisionResult, WorkflowResponse

class TestInteractiveCards(unittest.TestCase):
    def test_card_generation(self):
        form_card = create_intake_form_card()
        self.assertEqual(form_card["type"], "form")

        response = WorkflowResponse(
            intake=IntakeRequest(
                company_name="Test Corp",
                country="DE",
                iban="DE89370400440532013000",
                bank_country="DE",
                invoice_email_domain="test.com",
                amount=5000.0
            ),
            entity=EntityResult(canonical_name="Test Corp GmbH", status="verified", source="GLEIF"),
            sanctions=SanctionsResult(status="clear"),
            fraud=FraudResult(iban_valid=True, bank_country_match=True, spf_valid=True, dmarc_valid=True),
            decision=DecisionResult(decision="PROCEED", engine_used="rules_fallback", evidence=["Clean"])
        )

        carousel = create_sanctions_carousel_card(response)
        self.assertEqual(carousel["type"], "card")

        detail = create_fraud_detail_card(response)
        self.assertEqual(detail["type"], "detail")

        review = create_decision_review_card(response)
        self.assertEqual(review["type"], "review")

if __name__ == '__main__':
    unittest.main()
