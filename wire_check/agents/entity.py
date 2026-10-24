import requests
from typing import Optional
from wire_check.models import EntityResult, IntakeRequest
from wire_check.config import GLEIF_API_URL, COMPANIES_HOUSE_API_KEY
from wire_check.utils.logger import get_logger

logger = get_logger("entity_agent")

def resolve_entity_gleif(company_name: str) -> Optional[EntityResult]:
    """Resolves entity via GLEIF LEI API."""
    try:
        url = f"{GLEIF_API_URL}/lei-records"
        params = {"filter[entity.legalName]": company_name}
        headers = {"Accept": "application/vnd.api+json"}
        response = requests.get(url, params=params, headers=headers, timeout=5)
        if response.status_code == 200:
            data = response.json().get("data", [])
            if data:
                record = data[0]
                attributes = record.get("attributes", {})
                entity_info = attributes.get("entity", {})
                legal_name = entity_info.get("legalName", {}).get("name", company_name)

                # Extract address
                legal_address = entity_info.get("legalAddress", {})
                address_parts = [
                    legal_address.get("addressLines", [""])[0],
                    legal_address.get("city", ""),
                    legal_address.get("country", "")
                ]
                registered_address = ", ".join([p for p in address_parts if p])

                # Extract other names / aliases
                other_names = entity_info.get("otherNames", [])
                aliases = [on.get("name") for on in other_names if on.get("name")]

                return EntityResult(
                    canonical_name=legal_name,
                    aliases=aliases,
                    status="verified",
                    registered_address=registered_address,
                    website=None,  # GLEIF might not have website directly
                    source="GLEIF"
                )
    except Exception as e:
        logger.warning(f"GLEIF API resolution failed for {company_name}: {e}")
    return None

def resolve_entity_companies_house(company_name: str, registration_number: Optional[str] = None) -> Optional[EntityResult]:
    """Resolves entity via UK Companies House API."""
    if not COMPANIES_HOUSE_API_KEY or COMPANIES_HOUSE_API_KEY == "your_companies_house_api_key_here":
        return None

    try:
        url = "https://api.company-information.service.gov.uk/search/companies"
        query = registration_number or company_name
        params = {"q": query}
        # Companies House uses HTTP Basic Auth with API key as username and empty password
        response = requests.get(url, params=params, auth=(COMPANIES_HOUSE_API_KEY, ""), timeout=5)
        if response.status_code == 200:
            items = response.json().get("items", [])
            if items:
                company = items[0]
                canonical_name = company.get("title", company_name)
                company_status = company.get("company_status", "active")
                address_snippet = company.get("address_snippet", "")

                status = "verified" if company_status in ["active", "operating"] else "inactive"

                return EntityResult(
                    canonical_name=canonical_name,
                    aliases=[],
                    status=status,
                    registered_address=address_snippet,
                    website=None,
                    source="Companies House"
                )
    except Exception as e:
        logger.warning(f"Companies House API resolution failed for {company_name}: {e}")
    return None

def resolve_entity(intake: IntakeRequest) -> EntityResult:
    """Resolves legal entity using GLEIF LEI, Companies House, or falls back to unverified explicitly."""
    logger.info(f"Resolving entity for: {intake.company_name} (Country: {intake.country})")

    # 1. Try GLEIF
    result = resolve_entity_gleif(intake.company_name)
    if result:
        logger.info(f"Entity successfully resolved via GLEIF: {result.canonical_name}")
        return result

    # 2. Try UK Companies House if UK or reg number present
    if intake.country.upper() == "GB" or intake.registration_number:
        result = resolve_entity_companies_house(intake.company_name, intake.registration_number)
        if result:
            logger.info(f"Entity successfully resolved via Companies House: {result.canonical_name}")
            return result

    # 3. Explicit unverified fallback (Never guesses)
    logger.warning(f"Entity could not be verified in official registries: {intake.company_name}. Returning explicit 'unverified'.")
    return EntityResult(
        canonical_name=intake.company_name,
        aliases=[],
        status="unverified",
        registered_address=None,
        website=None,
        source="unverified"
    )
