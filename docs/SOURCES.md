# Data Sources & Reference Documentation

Date: 2026-10-24
Project: Wire Check (ASI:One Agent Challenge / Fetch-A-Thon 3.0)

## 1. uAgents & Agent Chat Protocol (ACP)
- **Framework**: Fetch.ai uAgents Python SDK (`uagents`).
- **Communication**: Agent Chat Protocol (ACP) via uAgents message handling and Agentverse registration.
- **Access**: Standard Python package `uagents`.

## 2. ASI1 Interactive Cards
- **Reference**: https://innovationlab.fetch.ai/resources/docs/interactive-cards/asi-interactive-cards
- **Formats**: Form cards, carousel cards, detail view cards, review cards. Payload limit 64 KB.
- **Handling**: Selection JSON from direct `@mention`, natural-language prose from planner-mediated routing, fallback to plain text.

## 3. Jev / TypeSafe System One
- **Reference**: https://docs.typesafe.ai
- **Endpoint**: `https://api.typesafe.ai/v1/systemone`
- **SDK**: `typesafe-sdk` (`TypeSafeClient().system_one(state=..., questions={...})`)
- **Auth**: `TYPESAFE_API_KEY` environment variable.
- **Models**: `jev-latest` (rolling), `jev-1.13.0` (pinned).
- **Question Types**: Choice, Score, Noul. Text-only input, probability distributions per option.

## 4. Entity Verification Sources
- **GLEIF LEI API**: Open API for Legal Entity Identifiers (`https://api.gleif.org/api/v1/...`).
- **UK Companies House API**: Open API for UK company registration (`https://api.company-information.service.gov.uk`). Free API key required.

## 5. Sanctions Lists
- **OFAC (US Treasury)**: Consolidated Sanctions List (SDN and non-SDN).
- **EU Consolidated List**: EU financial sanctions map/XML/CSV.
- **UN Security Council Consolidated List**: XML/JSON formats.
- **Matching**: Fuzzy matching with transliteration handling and secondary identifiers (DOB, country, listing IDs).

## 6. Payment Fraud & Domain Checks
- **IBAN Validation**: Mod-97 validation (ISO 13616) and country code comparison against bank BIC/IBAN structure.
- **RDAP / WHOIS**: Domain age and registrar lookup for invoice email domains.
- **Lookalike Detection**: Levenshtein/Damerau-Levenshtein edit distance, homoglyph detection, TLD swaps against the registered website domain from the Entity agent.
- **DNS / Mail Security**: SPF and DMARC posture verification via DNS record queries (`dnspython`).
