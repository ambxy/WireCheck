# Wire Check

> **Pre-wire AI verification & multi-agent risk screening for small businesses.**
> Built for the **ASI:One Agent Challenge (Fetch-A-Thon 3.0)**. Target prize track: **Overall Winners** & **Best Multi-Agent Workflow**.

[![Innovation Lab](https://img.shields.io/badge/Fetch.ai-Innovation%20Lab-orange)](https://innovationlab.fetch.ai)
[![ASI:One Challenge](https://img.shields.io/badge/ASI:One-Agent%20Challenge-blue)](https://agentverse.ai)
[![uAgents](https://img.shields.io/badge/Framework-uAgents-green)](https://uagents.fetch.ai)

---

## 🚀 Pitch & ASI:One Integration

Small businesses pay unfamiliar overseas suppliers by wire with almost no verification. Business Email Compromise (BEC) and sanctions exposure present severe financial and legal risks.

**Wire Check** is an autonomous multi-agent advisory system running inside **ASI:One** via **Interactive Cards**. Before any wire is initiated, specialist parallel agents verify the legal entity, screen sanctions lists, and analyze payment fraud signals. A fast decision model (**Jev / TypeSafe System One**) alongside deterministic safety rules judges the risk and returns **PROCEED / CALL-BACK / HOLD**, generating an out-of-band call-back verification script. **It never moves money.**

### Agent Chat Protocol (ACP) & ASI:One Discoverability
- **ACP Implemented**: Built using `uagents` message models (`WireCheckQuery` and `WireCheckResponse`) in `wire_check/agents/orchestrator.py` alongside official `ChatProtocol`.
- **ASI:One Routing**: Registered on Agentverse with handle `@wire-check_orchestrator` and configured with description keywords (`research`, `support`, `automation`, `fraud detection`, `compliance`) so the ASI:One LLM automatically routes supplier wire verification prompts to Wire Check.

---

## 👥 Problem & Target Users

- **Problem**: Lack of affordable, real-time supplier verification for SMBs. Manual checks miss lookalike domains, transliterated sanctions aliases, and subtle IBAN/bank mismatches.
- **Target Users**: Small-business owners, bookkeepers, AP (accounts payable) and finance staff.

---

## 📊 Sample Output & Interactive Flow

1. **Intake Form Card**: User fills in supplier name, country, IBAN, bank country, invoice email domain, amount, and recent bank change flag.
2. **Entity Resolution**: Resolves legal entity via GLEIF LEI API and UK Companies House. (Returns explicit `unverified` if coverage is missing; never guesses).
3. **Parallel Specialists**:
   - **Sanctions Agent**: Screens canonical name and aliases against OFAC, EU, and UN consolidated lists with fuzzy matching and transliteration.
   - **Payment-Fraud Agent**: Validates IBAN mod-97 checksum, checks bank vs. company country match, evaluates domain age, detects lookalike domains, and verifies SPF/DMARC DNS records.
4. **Decision Engine & Review Card**: Jev probabilities + safety overrides yield **PROCEED**, **CALL-BACK**, or **HOLD**, complete with evidence and a generated call-back script.

---

## 📐 Architecture & Mermaid Diagram

```mermaid
graph TD
    User[ASI:One User / Interactive Card] -->|Intake Form Submission via ACP| Intake[Intake Agent]
    Intake -->|Normalized Intake| Entity[Entity Resolution Agent]
    
    Entity -->|Canonical Name & Website (Source-of-Truth)| Sanctions[Sanctions Screening Agent]
    Entity -->|Registered Website| Fraud[Payment-Fraud Agent]
    
    Sanctions -->|Sanctions Score & Candidates| Decision[Decision Engine (Jev + Rules + Overrides)]
    Fraud -->|Fraud Signals & IBAN Status| Decision
    
    Decision -->|PROCEED / CALL-BACK / HOLD + Call-back Script| ASI1[ASI:One Interactive Review Card]
```

*Mandatory Dependency Rule*: The Entity agent's resolved canonical name and website feed **both** the Sanctions screen and the Fraud domain comparison. If an entity is `unverified`, downstream agents run in a degraded mode and `PROCEED` is strictly forbidden.

---

## ⚖️ Decision Rules & Jev AI + Safety Overrides

| Risk Indicator | Condition | Rule / Override Result |
|---|---|---|
| **Sanctions Match** | Score $\ge$ 85% (OFAC/EU/UN) | **HOLD** (Hard Safety Override) |
| **Sanctions Near-Match** | Score 60% – 84.9% | **CALL-BACK** |
| **IBAN Validity** | Failed ISO 13616 mod-97 checksum | **HOLD** (Hard Safety Override) |
| **Domain Impersonation** | Lookalike domain + Young domain ($<180$ days) | **HOLD** (Hard Safety Override) |
| **Entity Status** | Unverified in GLEIF / Companies House | **CALL-BACK** (`PROCEED` forbidden) |
| **Email Posture** | Missing or invalid SPF / DMARC | **CALL-BACK** |
| **Clean Verification** | All checks pass & Jev confident | **PROCEED** |

### Jev (TypeSafe System One) Integration
- **Endpoint**: `https://api.typesafe.ai/v1/systemone` (Model: `jev-1.13.0`)
- **Design**: Returns calibrated probability distributions for `PROCEED`, `CALL-BACK`, and `HOLD`.
- **Hard Safety Overrides**: Applied *after* Jev; overrides can only make the decision *stricter* (e.g., Jev says PROCEED, but an invalid IBAN forces HOLD).
- **Reliability Fallback**: Automatic retry with backoff; on timeout or API key omission, falls back gracefully to `RulesDecisionEngine` labeled as `decided by rules fallback`.

---

## 📂 Data Sources & Access Terms

1. **GLEIF LEI API**: Open access for Legal Entity Identifier verification (`https://api.gleif.org`).
2. **UK Companies House API**: Open official registry (`https://api.company-information.service.gov.uk`). Free API key.
3. **Sanctions Lists**: Consolidated OFAC (US), EU, and UN financial sanctions lists.
4. **TypeSafe Jev AI**: Probabilistic classification API (`https://docs.typesafe.ai`).

---

## 💳 Payment Protocol & Monetization Model

- **Model**: Per-check micro-fee priced low for occasional SMB use ($0.50 per audit).
- **Implementation**: Sub-agent agent-to-agent payment protocol hooks stubbed behind `wire_check/agents/orchestrator.py` and marked **Planned** for future Fetch.ai ledger integration.

---

## 🛡️ Reliability & Error Handling

- Timeouts and exponential backoff on all external API requests.
- Graceful degradation: A failed API call or missing Jev key never silently defaults to `PROCEED` — it defaults to explicit `CALL-BACK` or `HOLD`.

---

## ⚙️ Setup and Run Instructions

### Prerequisites
- Python 3.10+
- `pip`

### Environment Configuration
Copy `.env.example` to `.env` and fill in your keys:
```bash
cp .env.example .env
```

### Installation
```bash
pip install -r requirements.txt
pip install uagents litellm
```

### Running Local Tests
Run the complete unit and end-to-end test suite:
```bash
py wire_check/tests/run_tests.py
```

### Running the Orchestrator uAgent (Mailbox Mode)
```bash
py -m wire_check.agents.orchestrator
```

---

## 🗺️ Project Structure

```
wire_check/
├── __init__.py
├── config.py              # Configuration, decision thresholds, and environment settings
├── models.py              # Pydantic / dataclass data models
├── agents/
│   ├── __init__.py
│   ├── intake.py          # Intake logic & ASI:One form cards
│   ├── entity.py          # Entity resolution (GLEIF & Companies House)
│   ├── sanctions.py       # Sanctions screening (OFAC, EU, UN fuzzy matching)
│   ├── fraud.py           # Payment-fraud agent (IBAN mod-97, RDAP, lookalike, DNS SPF/DMARC)
│   ├── decision.py        # Decision Engine (Jev TypeSafe + Rules + Hard Overrides)
│   └── orchestrator.py    # Orchestrator agent & ACP integration
├── utils/
│   ├── __init__.py
│   ├── typesafe_client.py # TypeSafe Jev API client with retry & fallback
│   └── logger.py          # Structured logging
├── cards/
│   ├── __init__.py
│   └── templates.py       # ASI1 Interactive Cards (Form, Carousel, Detail, Review)
└── tests/
    ├── __init__.py
    ├── run_tests.py       # Comprehensive test runner
    ├── test_fraud.py
    ├── test_entity.py
    ├── test_sanctions.py
    ├── test_decision.py
    ├── test_orchestrator.py
    └── test_cards.py
```

---

## ⚠️ Limitations & Disclaimer
- **Advisory Only**: Wire Check provides decision support and risk scoring; it never initiates or executes wire transfers.
- **Probabilistic Models**: Jev AI and fuzzy sanctions matching require human review for near-matches.
- **Unverified Status**: "Unverified" means the entity was not found in automated open registries, not that the entity is fraudulent.

---

## 🗺️ Roadmap
- [x] Phase 0-5: Core agents, fraud logic, entity resolution, sanctions screening, Jev decision engine.
- [x] Phase 6-7: Orchestrator, ACP, ASI1 Interactive Cards, Mailbox setup, local test suite.
- [ ] Live Agentverse registration & ASI:One production deployment (`TODO: add URL`).
- [ ] Payment Protocol ledger-backed micro-payments.

---

## 📜 License
MIT License.

---
🤖 Generated with [Claude Code](https://claude.com/claude-code)
Co-Authored-By: Claude Code <noreply@anthropic.com>
