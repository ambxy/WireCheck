import os
try:
    from dotenv import load_dotenv
    load_dotenv()
except ImportError:
    pass

# Decision Engine Configuration
DECISION_ENGINE = os.getenv("DECISION_ENGINE", "jev").lower()
TYPESAFE_API_KEY = os.getenv("TYPESAFE_API_KEY", "")
JEV_MODEL = os.getenv("JEV_MODEL", "jev-1.13.0")
TYPESAFE_API_URL = "https://api.typesafe.ai/v1/systemone"
ASI1_API_KEY = os.getenv("ASI1_API_KEY", "dummy_key_to_bypass_validation")

# External API Configuration
GLEIF_API_URL = os.getenv("GLEIF_API_URL", "https://api.gleif.org/api/v1")
COMPANIES_HOUSE_API_KEY = os.getenv("COMPANIES_HOUSE_API_KEY", "")

# Agent Configuration
AGENT_SEED = os.getenv("AGENT_SEED", "wire_check_default_seed")

# Decision Thresholds & Rules Configuration
THRESHOLDS = {
    "sanctions_hold_score": 85.0,      # Score >= 85 triggers strong sanctions candidate -> HOLD
    "sanctions_callback_score": 60.0,  # Score between 60 and 85 triggers near-match -> CALL-BACK
    "domain_age_days_min": 180,        # Domains registered less than 180 days ago are considered "young"
    "lookalike_edit_distance": 2,      # Levenshtein distance <= 2 against registered website domain triggers lookalike
    "jev_confidence_min": 0.70,        # Minimum top probability required for Jev confidence; otherwise escalate to CALL-BACK
}
