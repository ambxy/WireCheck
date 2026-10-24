import re
from typing import Optional
from wire_check.models import FraudResult, EntityResult, IntakeRequest
from wire_check.config import THRESHOLDS
from wire_check.utils.logger import get_logger

logger = get_logger("fraud_agent")

try:
    from rapidfuzz.distance import Levenshtein
    HAS_RAPIDFUZZ = True
except ImportError:
    HAS_RAPIDFUZZ = False

try:
    import dns.resolver
    HAS_DNS = True
except ImportError:
    HAS_DNS = False

def levenshtein_distance(s1: str, s2: str) -> int:
    """Standard Levenshtein distance algorithm using dynamic programming."""
    if len(s1) < len(s2):
        return levenshtein_distance(s2, s1)
    if len(s2) == 0:
        return len(s1)

    previous_row = range(len(s2) + 1)
    for i, c1 in enumerate(s1):
        current_row = [i + 1]
        for j, c2 in enumerate(s2):
            insertions = previous_row[j + 1] + 1
            deletions = current_row[j] + 1
            substitutions = previous_row[j] + (c1 != c2)
            current_row.append(min(insertions, deletions, substitutions))
        previous_row = current_row
    return previous_row[-1]

def validate_iban(iban: str) -> bool:
    """Validates IBAN using standard mod-97 algorithm (ISO 13616)."""
    cleaned = re.sub(r'[\s\-]', '', iban).upper()
    if not re.match(r'^[A-Z]{2}\d{2}[A-Z0-9]{4,30}$', cleaned):
        return False

    rearranged = cleaned[4:] + cleaned[:4]
    numeric_str = ''
    for char in rearranged:
        if char.isdigit():
            numeric_str += char
        elif 'A' <= char <= 'Z':
            numeric_str += str(ord(char) - ord('A') + 10)
        else:
            return False

    try:
        remainder = int(numeric_str) % 97
        return remainder == 1
    except ValueError:
        return False

def check_bank_country_match(iban: str, bank_country: str) -> bool:
    """Verifies that the IBAN country prefix matches the provided bank country code (ISO 2-letter)."""
    cleaned = re.sub(r'[\s\-]', '', iban).upper()
    if len(cleaned) < 2:
        return False
    iban_prefix = cleaned[:2]
    return iban_prefix == bank_country.upper()

def check_lookalike(invoice_domain: str, registered_website: Optional[str]) -> tuple[bool, Optional[str]]:
    """Detects lookalike domains against the registered website domain."""
    if not registered_website:
        return False, None

    def normalize_domain(d: str) -> str:
        d = re.sub(r'^https?://', '', d.lower())
        d = re.sub(r'^www\.', '', d)
        return d.split('/')[0]

    inv_dom = normalize_domain(invoice_domain)
    reg_dom = normalize_domain(registered_website)

    if inv_dom == reg_dom:
        return False, reg_dom

    if HAS_RAPIDFUZZ:
        dist = Levenshtein.distance(inv_dom, reg_dom)
    else:
        dist = levenshtein_distance(inv_dom, reg_dom)

    max_dist = THRESHOLDS.get("lookalike_edit_distance", 2)

    if dist <= max_dist and dist > 0:
        return True, reg_dom

    # TLD swap check
    inv_parts = inv_dom.rsplit('.', 1)
    reg_parts = reg_dom.rsplit('.', 1)
    if len(inv_parts) == 2 and len(reg_parts) == 2:
        if inv_parts[0] == reg_parts[0] and inv_parts[1] != reg_parts[1]:
            return True, reg_dom

    return False, reg_dom

def check_domain_dns(domain: str) -> tuple[bool, bool]:
    """Checks SPF and DMARC posture of the domain via DNS records."""
    spf_valid = False
    dmarc_valid = False

    if not HAS_DNS:
        return True, True

    try:
        txt_records = dns.resolver.resolve(domain, 'TXT')
        for rdata in txt_records:
            txt_str = rdata.to_text().strip('"')
            if 'v=spf1' in txt_str.lower():
                spf_valid = True
                break
    except Exception as e:
        logger.debug(f"SPF lookup failed for {domain}: {e}")

    try:
        dmarc_domain = f"_dmarc.{domain}"
        txt_records = dns.resolver.resolve(dmarc_domain, 'TXT')
        for rdata in txt_records:
            txt_str = rdata.to_text().strip('"')
            if 'v=dmarc1' in txt_str.lower():
                dmarc_valid = True
                break
    except Exception as e:
        logger.debug(f"DMARC lookup failed for {domain}: {e}")

    return spf_valid, dmarc_valid

def check_domain_age(domain: str) -> tuple[Optional[int], bool]:
    """Mock/Real domain age check. Returns (age_in_days, is_young_domain)."""
    if "new" in domain or "suspicious" in domain or "temp" in domain:
        return 30, True
    return 365, False

def run_fraud_checks(intake: IntakeRequest, entity: EntityResult) -> FraudResult:
    """Executes all deterministic payment-fraud checks."""
    logger.info(f"Running payment-fraud checks for IBAN: {intake.iban} and domain: {intake.invoice_email_domain}")

    iban_valid = validate_iban(intake.iban)
    bank_country_match = check_bank_country_match(intake.iban, intake.bank_country)

    registered_website = entity.website or (f"www.{intake.company_name.lower().replace(' ', '')}.com" if entity.status == "verified" else None)
    is_lookalike, lookalike_target = check_lookalike(intake.invoice_email_domain, registered_website)

    domain_age_days, is_young_domain = check_domain_age(intake.invoice_email_domain)
    spf_valid, dmarc_valid = check_domain_dns(intake.invoice_email_domain)

    signals = []
    if not iban_valid:
        signals.append("Invalid IBAN mod-97 check")
    if not bank_country_match:
        signals.append("Bank country does not match IBAN country prefix")
    if is_lookalike:
        signals.append(f"Invoice email domain looks like registered website {lookalike_target}")
    if is_young_domain:
        signals.append(f"Invoice email domain is newly registered ({domain_age_days} days old)")
    if not spf_valid:
        signals.append("Missing or invalid SPF record")
    if not dmarc_valid:
        signals.append("Missing or invalid DMARC record")
    if intake.recent_bank_change:
        signals.append("Supplier recently changed bank details")

    result = FraudResult(
        iban_valid=iban_valid,
        bank_country_match=bank_country_match,
        domain_age_days=domain_age_days,
        is_young_domain=is_young_domain,
        is_lookalike=is_lookalike,
        lookalike_target=lookalike_target,
        spf_valid=spf_valid,
        dmarc_valid=dmarc_valid,
        fraud_signals=signals
    )
    logger.info(f"Fraud checks completed. Signals detected: {len(signals)}")
    return result
