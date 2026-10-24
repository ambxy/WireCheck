import unicodedata
from typing import List
from wire_check.models import SanctionsCandidate, SanctionsResult, EntityResult
from wire_check.config import THRESHOLDS
from wire_check.utils.logger import get_logger

logger = get_logger("sanctions_agent")

try:
    from rapidfuzz.fuzz import token_sort_ratio
    HAS_RAPIDFUZZ = True
except ImportError:
    HAS_RAPIDFUZZ = False
    import difflib

# In-memory cached sanctions database (OFAC, EU, UN consolidated test fixtures)
MOCK_SANCTIONS_LIST = [
    {
        "name": "ACME TERRORIST CORP",
        "aliases": ["ACME GLOBAL TERROR", "AGME CORP"],
        "list_source": "OFAC",
        "identifiers": {"country": "XX", "listing_id": "OFAC-9999"}
    },
    {
        "name": "GLOBAL FRAUD SYNDICATE LTD",
        "aliases": ["GFS HOLDINGS"],
        "list_source": "EU",
        "identifiers": {"country": "YY", "listing_id": "EU-8888"}
    },
    {
        "name": "BADACTOR ENTERPRISES",
        "aliases": [],
        "list_source": "UN",
        "identifiers": {"country": "ZZ", "listing_id": "UN-7777"}
    }
]

def normalize_text(text: str) -> str:
    """Normalizes text for fuzzy matching and transliteration handling."""
    if not text:
        return ""
    # Unicode NFKD normalization to strip diacritics/accents
    nfkd_form = unicodedata.normalize('NFKD', text)
    stripped = "".join([c for c in nfkd_form if not unicodedata.combining(c)])
    # Collapse multiple whitespace into a single space and uppercase
    return " ".join(stripped.upper().split())

def compute_similarity(name1: str, name2: str) -> float:
    """Computes similarity score between 0.0 and 100.0."""
    n1 = normalize_text(name1)
    n2 = normalize_text(name2)
    if n1 == n2:
        return 100.0

    if HAS_RAPIDFUZZ:
        return float(token_sort_ratio(n1, n2))
    else:
        import difflib
        matcher = difflib.SequenceMatcher(None, n1, n2)
        return float(matcher.ratio() * 100.0)

def screen_entity(entity: EntityResult) -> SanctionsResult:
    """Screens the canonical name and aliases of the resolved entity against sanctions lists."""
    names_to_check = [entity.canonical_name] + entity.aliases
    logger.info(f"Screening entity against sanctions lists. Names checked: {names_to_check}")

    candidates: List[SanctionsCandidate] = []
    max_score = 0.0

    hold_threshold = THRESHOLDS.get("sanctions_hold_score", 85.0)
    callback_threshold = THRESHOLDS.get("sanctions_callback_score", 60.0)

    for item in MOCK_SANCTIONS_LIST:
        target_names = [item["name"]] + item["aliases"]
        item_max_score = 0.0
        best_matched_name = item["name"]

        for check_name in names_to_check:
            for t_name in target_names:
                score = compute_similarity(check_name, t_name)
                if score > item_max_score:
                    item_max_score = score
                    best_matched_name = t_name

        if item_max_score >= callback_threshold:
            is_strong = item_max_score >= hold_threshold
            candidate = SanctionsCandidate(
                matched_name=best_matched_name,
                score=item_max_score,
                list_source=item["list_source"],
                identifiers=item["identifiers"],
                is_strong_match=is_strong
            )
            candidates.append(candidate)
            if item_max_score > max_score:
                max_score = item_max_score

    # Determine status
    status = "clear"
    if any(c.is_strong_match for c in candidates):
        status = "strong_match"
    elif candidates:
        status = "near_match"

    logger.info(f"Sanctions screening completed. Status: {status}, Max Score: {max_score}")
    return SanctionsResult(
        candidates=candidates,
        max_score=max_score,
        status=status
    )
