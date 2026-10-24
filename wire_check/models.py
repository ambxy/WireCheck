from typing import List, Optional, Dict, Any

try:
    from pydantic import BaseModel, Field
    HAS_PYDANTIC = True
except ImportError:
    HAS_PYDANTIC = False

if HAS_PYDANTIC:
    from pydantic import BaseModel, Field

    class IntakeRequest(BaseModel):
        company_name: str
        country: str
        registration_number: Optional[str] = None
        iban: str
        bank_country: str
        invoice_email_domain: str
        amount: float
        recent_bank_change: bool = False

    class EntityResult(BaseModel):
        canonical_name: str
        aliases: List[str] = Field(default_factory=list)
        status: str = "unverified" # "verified", "unverified", "active", "inactive"
        registered_address: Optional[str] = None
        website: Optional[str] = None
        source: str = "unverified"  # "GLEIF", "Companies House", or "unverified"

    class SanctionsCandidate(BaseModel):
        matched_name: str
        score: float
        list_source: str  # "OFAC", "EU", "UN"
        identifiers: Dict[str, Any] = Field(default_factory=dict)
        is_strong_match: bool = False

    class SanctionsResult(BaseModel):
        candidates: List[SanctionsCandidate] = Field(default_factory=list)
        max_score: float = 0.0
        status: str = "clear"  # "clear", "near_match", "strong_match"

    class FraudResult(BaseModel):
        iban_valid: bool
        bank_country_match: bool
        domain_age_days: Optional[int] = None
        is_young_domain: bool = False
        is_lookalike: bool = False
        lookalike_target: Optional[str] = None
        spf_valid: bool = False
        dmarc_valid: bool = False
        fraud_signals: List[str] = Field(default_factory=list)

    class DecisionResult(BaseModel):
        decision: str  # "PROCEED", "CALL-BACK", "HOLD"
        engine_used: str  # "jev" or "rules_fallback"
        evidence: List[str] = Field(default_factory=list)
        safety_overrides_triggered: List[str] = Field(default_factory=list)
        jev_probabilities: Dict[str, float] = Field(default_factory=dict)
        callback_script: Optional[str] = None
        latency_ms: float = 0.0
        token_usage: Dict[str, int] = Field(default_factory=dict)

    class WorkflowResponse(BaseModel):
        intake: IntakeRequest
        entity: EntityResult
        sanctions: SanctionsResult
        fraud: FraudResult
        decision: DecisionResult

else:
    from dataclasses import dataclass, field

    @dataclass
    class IntakeRequest:
        company_name: str
        country: str
        iban: str
        bank_country: str
        invoice_email_domain: str
        amount: float
        registration_number: Optional[str] = None
        recent_bank_change: bool = False

    @dataclass
    class EntityResult:
        canonical_name: str
        status: str = "unverified"
        source: str = "unverified"
        aliases: List[str] = field(default_factory=list)
        registered_address: Optional[str] = None
        website: Optional[str] = None

    @dataclass
    class SanctionsCandidate:
        matched_name: str
        score: float
        list_source: str
        identifiers: Dict[str, Any] = field(default_factory=list)
        is_strong_match: bool = False

    @dataclass
    class SanctionsResult:
        candidates: List[SanctionsCandidate] = field(default_factory=list)
        max_score: float = 0.0
        status: str = "clear"

    @dataclass
    class FraudResult:
        iban_valid: bool
        bank_country_match: bool
        domain_age_days: Optional[int] = None
        is_young_domain: bool = False
        is_lookalike: bool = False
        lookalike_target: Optional[str] = None
        spf_valid: bool = False
        dmarc_valid: bool = False
        fraud_signals: List[str] = field(default_factory=list)

    @dataclass
    class DecisionResult:
        decision: str
        engine_used: str
        evidence: List[str] = field(default_factory=list)
        safety_overrides_triggered: List[str] = field(default_factory=list)
        jev_probabilities: Dict[str, float] = field(default_factory=dict)
        callback_script: Optional[str] = None
        latency_ms: float = 0.0
        token_usage: Dict[str, int] = field(default_factory=dict)

    @dataclass
    class WorkflowResponse:
        intake: IntakeRequest
        entity: EntityResult
        sanctions: SanctionsResult
        fraud: FraudResult
        decision: DecisionResult
