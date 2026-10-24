import time
from typing import List, Dict, Any, Optional
from wire_check.models import IntakeRequest, EntityResult, SanctionsResult, FraudResult, DecisionResult
from wire_check.config import DECISION_ENGINE, THRESHOLDS
from wire_check.utils.typesafe_client import TypeSafeClient
from wire_check.utils.logger import get_logger

logger = get_logger("decision_agent")

def generate_callback_script(intake: IntakeRequest, entity: EntityResult, fraud: FraudResult) -> str:
    """Generates a deterministic call-back verification script."""
    return f"""--- WIRE-CHECK CALL-BACK VERIFICATION SCRIPT ---
To: Finance / AP Team ({intake.company_name})
Action Required: VERIFY OUT-OF-BAND BEFORE WIRE RELEASE

1. Contact Person: Call the primary verified phone number on file for {entity.canonical_name} (NOT the phone number listed on the invoice PDF or recent email change request).
2. Registered Address on File: {entity.registered_address or 'Unverified / Manual check required'}
3. IBAN Verification: Confirm outgoing wire IBAN is exactly: {intake.iban} (Bank Country: {intake.bank_country})
4. Amount & Purpose: Verify wire amount of ${intake.amount:,.2f} USD / equivalent for invoice issued by {intake.invoice_email_domain}.
5. Recent Changes: {"⚠️ WARNING: Supplier recently reported bank detail changes. Double-confirm via pre-established trusted phone channel." if intake.recent_bank_change else "No recent bank changes flagged."}
6. Fraud Signals Flagged: {', '.join(fraud.fraud_signals) if fraud.fraud_signals else 'None'}

Approved by: Wire Check Advisory Engine (Jev / Rules Fallback)
-------------------------------------------------------------"""

class RulesDecisionEngine:
    """Deterministic rules-based decision engine."""
    def decide(self, intake: IntakeRequest, entity: EntityResult, sanctions: SanctionsResult, fraud: FraudResult) -> DecisionResult:
        start_time = time.time()
        evidence: List[str] = []
        overrides: List[str] = []

        decision = "PROCEED"

        # 1. Entity unverified -> at least CALL-BACK
        if entity.status == "unverified":
            decision = "CALL-BACK"
            overrides.append("Entity unverified -> PROCEED forbidden")
            evidence.append("Entity could not be verified in official registries (GLEIF / Companies House).")

        # 2. Sanctions checks
        if sanctions.status == "strong_match":
            decision = "HOLD"
            overrides.append("Strong sanctions match -> HOLD")
            evidence.append(f"Strong sanctions candidate detected (Score: {sanctions.max_score:.1f}%).")
        elif sanctions.status == "near_match":
            if decision != "HOLD":
                decision = "CALL-BACK"
            overrides.append("Sanctions near-match -> CALL-BACK")
            evidence.append(f"Sanctions near-match detected (Score: {sanctions.max_score:.1f}%).")

        # 3. Fraud checks
        if not fraud.iban_valid:
            decision = "HOLD"
            overrides.append("Invalid IBAN -> HOLD")
            evidence.append("IBAN failed ISO 13616 mod-97 checksum validation.")

        if not fraud.bank_country_match:
            if decision != "HOLD":
                decision = "CALL-BACK"
            evidence.append("Bank country does not match IBAN country prefix.")

        if fraud.is_lookalike and fraud.is_young_domain:
            decision = "HOLD"
            overrides.append("Lookalike domain + young domain -> HOLD")
            evidence.append(f"Invoice domain {intake.invoice_email_domain} is a lookalike to registered website and newly registered ({fraud.domain_age_days} days).")
        elif fraud.is_lookalike or fraud.is_young_domain or intake.recent_bank_change:
            if decision != "HOLD":
                decision = "CALL-BACK"
            evidence.append(f"Fraud risk indicators present: {', '.join(fraud.fraud_signals)}")

        if not fraud.spf_valid or not fraud.dmarc_valid:
            if decision != "HOLD":
                decision = "CALL-BACK"
            evidence.append("Sender email domain has missing or invalid SPF/DMARC posture.")

        if not evidence:
            evidence.append("All checks passed cleanly. Entity verified, sanctions clear, IBAN valid, domain secure.")

        latency_ms = (time.time() - start_time) * 1000.0
        script = generate_callback_script(intake, entity, fraud) if decision in ["CALL-BACK", "HOLD"] else None

        return DecisionResult(
            decision=decision,
            engine_used="rules_fallback",
            evidence=evidence,
            safety_overrides_triggered=overrides,
            jev_probabilities={},
            callback_script=script,
            latency_ms=latency_ms,
            token_usage={"prompt_tokens": 0, "completion_tokens": 0, "total_tokens": 0}
        )

class JevDecisionEngine:
    """Jev (TypeSafe System One) decision engine with rules fallback and safety overrides."""
    def __init__(self):
        self.client = TypeSafeClient()
        self.rules_engine = RulesDecisionEngine()

    def decide(self, intake: IntakeRequest, entity: EntityResult, sanctions: SanctionsResult, fraud: FraudResult) -> DecisionResult:
        start_time = time.time()

        # Build compact structured state summary for Jev
        state = {
            "entity_status": entity.status,
            "entity_source": entity.source,
            "sanctions_status": sanctions.status,
            "sanctions_max_score": sanctions.max_score,
            "iban_valid": fraud.iban_valid,
            "bank_country_match": fraud.bank_country_match,
            "is_young_domain": fraud.is_young_domain,
            "is_lookalike": fraud.is_lookalike,
            "spf_valid": fraud.spf_valid,
            "dmarc_valid": fraud.dmarc_valid,
            "amount_band": "high" if intake.amount > 50000 else "normal",
            "recent_bank_change": intake.recent_bank_change
        }

        questions = {
            "decision": {
                "type": "Choice",
                "options": ["PROCEED", "CALL-BACK", "HOLD"],
                "instructions": "Choose PROCEED only if fully verified and clean; CALL-BACK if minor risk or unverified; HOLD if major sanctions or fraud risk."
            }
        }

        jev_probs: Dict[str, float] = {}
        tokens = {}
        jev_decision = "CALL-BACK"

        try:
            answers, latency_ms, tokens = self.client.system_one(state, questions)
            decision_ans = answers.get("decision", {})
            jev_probs = decision_ans.get("probabilities", {"PROCEED": 0.1, "CALL-BACK": 0.8, "HOLD": 0.1})

            # Pick top option from Jev probabilities
            jev_decision = max(jev_probs, key=jev_probs.get)
            top_prob = jev_probs.get(jev_decision, 0.0)

            # Confidence escalation
            min_conf = THRESHOLDS.get("jev_confidence_min", 0.70)
            if top_prob < min_conf and jev_decision == "PROCEED":
                jev_decision = "CALL-BACK"
                logger.info(f"Jev confidence {top_prob:.2f} below minimum {min_conf}. Escalated to CALL-BACK.")

        except Exception as e:
            logger.warning(f"Jev decision engine failed or unavailable: {e}. Falling back to RulesDecisionEngine.")
            rules_res = self.rules_engine.decide(intake, entity, sanctions, fraud)
            rules_res.evidence.insert(0, f"Decided by rules fallback due to Jev error: {e}")
            return rules_res

        # Apply Hard Safety Overrides (stricter rule)
        rules_res = self.rules_engine.decide(intake, entity, sanctions, fraud)
        override_decision = rules_res.decision
        overrides = rules_res.safety_overrides_triggered

        # Stricter of Jev decision and override decision
        # Hierarchy: HOLD > CALL-BACK > PROCEED
        hierarchy = {"PROCEED": 0, "CALL-BACK": 1, "HOLD": 2}

        final_decision = jev_decision
        if hierarchy.get(override_decision, 0) > hierarchy.get(jev_decision, 0):
            final_decision = override_decision
            logger.info(f"Safety override applied: Jev proposed {jev_decision}, but override demanded {override_decision}.")

        total_latency = (time.time() - start_time) * 1000.0
        script = generate_callback_script(intake, entity, fraud) if final_decision in ["CALL-BACK", "HOLD"] else None

        evidence = rules_res.evidence
        evidence.insert(0, f"Jev Model assessed probabilities: {jev_probs}")

        return DecisionResult(
            decision=final_decision,
            engine_used="jev",
            evidence=evidence,
            safety_overrides_triggered=overrides,
            jev_probabilities=jev_probs,
            callback_script=script,
            latency_ms=total_latency,
            token_usage=tokens
        )

def make_decision(intake: IntakeRequest, entity: EntityResult, sanctions: SanctionsResult, fraud: FraudResult) -> DecisionResult:
    """Factory function selecting Jev or Rules decision engine based on configuration."""
    engine_type = DECISION_ENGINE
    logger.info(f"Executing DecisionEngine using: {engine_type}")

    if engine_type == "rules":
        return RulesDecisionEngine().decide(intake, entity, sanctions, fraud)
    else:
        try:
            return JevDecisionEngine().decide(intake, entity, sanctions, fraud)
        except Exception as e:
            logger.warning(f"Jev engine failed: {e}. Falling back to RulesDecisionEngine.")
            return RulesDecisionEngine().decide(intake, entity, sanctions, fraud)
