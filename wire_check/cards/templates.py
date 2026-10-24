from typing import Dict, Any, List
from wire_check.models import WorkflowResponse

def create_intake_form_card() -> Dict[str, Any]:
    """Generates ASI1 Interactive Form Card for Supplier Wire Intake."""
    return {
        "type": "form",
        "title": "Wire Check — Supplier Verification Intake",
        "description": "Enter supplier and wire payment details before releasing funds.",
        "fields": [
            {"id": "company_name", "label": "Supplier Legal/Business Name", "type": "text", "required": True},
            {"id": "country", "label": "Country (2-letter ISO)", "type": "text", "required": True, "placeholder": "DE, US, GB"},
            {"id": "registration_number", "label": "Company Registration Number (Optional)", "type": "text", "required": False},
            {"id": "iban", "label": "Supplier IBAN / Bank Account", "type": "text", "required": True},
            {"id": "bank_country", "label": "Bank Country (2-letter ISO)", "type": "text", "required": True},
            {"id": "invoice_email_domain", "label": "Invoice Sender Email Domain", "type": "text", "required": True, "placeholder": "supplier.com"},
            {"id": "amount", "label": "Wire Amount (USD)", "type": "number", "required": True},
            {"id": "recent_bank_change", "label": "Did supplier recently change bank details?", "type": "boolean", "required": False}
        ],
        "submit_label": "Run Wire Check Security Audit"
    }

def create_sanctions_carousel_card(response: WorkflowResponse) -> Dict[str, Any]:
    """Generates ASI1 Carousel Card for Sanctions screening candidates."""
    candidates = response.sanctions.candidates
    if not candidates:
        return {
            "type": "card",
            "title": "Sanctions Screening Results",
            "badge": {"variant": "success", "text": "Clear"},
            "content": "No sanctions candidates detected across OFAC, EU, or UN consolidated lists."
        }

    slides = []
    for c in candidates:
        slides.append({
            "title": f"Match: {c.matched_name}",
            "subtitle": f"List Source: {c.list_source} (Score: {c.score:.1f}%)",
            "badge": {"variant": "warning" if not c.is_strong_match else "error", "text": "Strong Match" if c.is_strong_match else "Near Match"},
            "details": f"Identifiers: {c.identifiers}"
        })

    return {
        "type": "carousel",
        "title": f"Sanctions Screening: {len(candidates)} Candidate(s) Found",
        "slides": slides
    }

def create_fraud_detail_card(response: WorkflowResponse) -> Dict[str, Any]:
    """Generates ASI1 Detail View Card for Payment Fraud & Domain Security signals."""
    fraud = response.fraud
    signals = fraud.fraud_signals

    variant = "success" if not signals else ("warning" if len(signals) <= 2 else "error")

    return {
        "type": "detail",
        "title": "Payment Fraud & Domain Security Audit",
        "badge": {"variant": variant, "text": f"{len(signals)} Signal(s) Detected"},
        "rows": [
            {"label": "IBAN Mod-97 Check", "value": "Valid" if fraud.iban_valid else "INVALID"},
            {"label": "Bank vs Company Country Match", "value": "Match" if fraud.bank_country_match else "MISMATCH"},
            {"label": "Domain Age", "value": f"{fraud.domain_age_days} days ({'Young' if fraud.is_young_domain else 'Established'})"},
            {"label": "Lookalike Domain Check", "value": f"Lookalike to {fraud.lookalike_target}" if fraud.is_lookalike else "Clean"},
            {"label": "SPF / DMARC Posture", "value": f"SPF: {'Valid' if fraud.spf_valid else 'Invalid'} | DMARC: {'Valid' if fraud.dmarc_valid else 'Invalid'}"},
            {"label": "Detected Fraud Signals", "value": ", ".join(signals) if signals else "None"}
        ]
    }

def create_decision_review_card(response: WorkflowResponse) -> Dict[str, Any]:
    """Generates ASI1 Review Card with Jev probabilities, engine used, and call-back script."""
    decision = response.decision
    variant = "success" if decision.decision == "PROCEED" else ("warning" if decision.decision == "CALL-BACK" else "error")

    rows = [
        {"label": "Final Decision Recommendation", "value": decision.decision},
        {"label": "Engine Used", "value": decision.engine_used.upper()},
        {"label": "Jev Probabilities", "value": str(decision.jev_probabilities)},
        {"label": "Safety Overrides Triggered", "value": ", ".join(decision.safety_overrides_triggered) if decision.safety_overrides_triggered else "None"},
        {"label": "Evidence Summary", "value": "; ".join(decision.evidence[:3])}
    ]

    card = {
        "type": "review",
        "title": f"Wire Check Decision: {decision.decision}",
        "badge": {"variant": variant, "text": decision.decision},
        "rows": rows
    }

    if decision.callback_script:
        card["callback_script"] = decision.callback_script

    return card
