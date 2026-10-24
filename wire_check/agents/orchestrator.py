import time
from typing import Optional
from wire_check.models import IntakeRequest, WorkflowResponse
from wire_check.agents.entity import resolve_entity
from wire_check.agents.sanctions import screen_entity
from wire_check.agents.fraud import run_fraud_checks
from wire_check.agents.decision import make_decision
from wire_check.config import AGENT_SEED
from wire_check.utils.logger import get_logger

logger = get_logger("orchestrator_agent")

def run_wire_check_workflow(intake: IntakeRequest) -> WorkflowResponse:
    """Executes the end-to-end Wire Check multi-agent workflow:
    Intake -> Entity Resolution -> Sanctions & Payment-Fraud -> Decision Engine.
    Enforces the mandatory Source-of-Truth dependency: Entity canonical name & website feed Sanctions and Fraud.
    """
    start_time = time.time()
    logger.info(f"Starting Wire Check workflow for supplier: {intake.company_name} (Amount: ${intake.amount:,.2f})")

    # Step 1: Entity Resolution
    entity_res = resolve_entity(intake)

    # Step 2: Sanctions screening (using canonical name & aliases from Entity agent)
    sanctions_res = screen_entity(entity_res)

    # Step 3: Payment-fraud checks (using entity website reference)
    fraud_res = run_fraud_checks(intake, entity_res)

    # Step 4: Decision Engine (Jev / Rules + Safety Overrides)
    decision_res = make_decision(intake, entity_res, sanctions_res, fraud_res)

    total_duration_ms = (time.time() - start_time) * 1000.0
    logger.info(f"Workflow completed in {total_duration_ms:.1f}ms. Final Decision: {decision_res.decision}")

    return WorkflowResponse(
        intake=intake,
        entity=entity_res,
        sanctions=sanctions_res,
        fraud=fraud_res,
        decision=decision_res
    )

# uAgents integration setup for Agentverse & ASI:One (Agent Chat Protocol)
try:
    from uagents import Agent, Context, Model, Protocol
    from uagents.experimental.chat_agent import ChatProtocol, LLMConfig
    HAS_UAGENTS = True
except ImportError:
    HAS_UAGENTS = False

if HAS_UAGENTS:
    class WireCheckQuery(Model):
        company_name: str
        country: str
        registration_number: Optional[str] = None
        iban: str
        bank_country: str
        invoice_email_domain: str
        amount: float
        recent_bank_change: bool = False

    class WireCheckResponse(Model):
        status: str
        decision: str
        evidence: list[str]
        callback_script: Optional[str] = None

    # Initialize Agent with mailbox=True and port 8001 (name restored to wire_check_orchestrator)
    wire_check_agent = Agent(
        name="wire_check_orchestrator",
        seed=AGENT_SEED,
        mailbox=True,
        port=8001
    )
    logger.info("Initialized Wire Check Agent with official ChatProtocol and mailbox=True.")

    # 1. Include official ChatProtocol with publish_manifest=True so Agentverse recognizes official ACP signature
    official_chat_proto = ChatProtocol(llm_config=LLMConfig.asi1(), tools={})
    wire_check_agent.include(official_chat_proto, publish_manifest=True)

    # 2. Define custom protocol for Wire Check workflow queries & responses
    wire_check_proto = Protocol(name="WireCheckWorkflow", version="1.0")

    @wire_check_proto.on_message(model=WireCheckQuery, replies={WireCheckResponse})
    async def handle_wire_check_query(ctx: Context, sender: str, msg: WireCheckQuery):
        ctx.logger.info(f"Received Wire Check query from {sender} for company {msg.company_name}")
        intake = IntakeRequest(
            company_name=msg.company_name,
            country=msg.country,
            registration_number=msg.registration_number,
            iban=msg.iban,
            bank_country=msg.bank_country,
            invoice_email_domain=msg.invoice_email_domain,
            amount=msg.amount,
            recent_bank_change=msg.recent_bank_change
        )
        response = run_wire_check_workflow(intake)
        await ctx.send(
            sender,
            WireCheckResponse(
                status="success",
                decision=response.decision.decision,
                evidence=response.decision.evidence,
                callback_script=response.decision.callback_script
            )
        )

    wire_check_agent.include(wire_check_proto)

if __name__ == "__main__":
    if HAS_UAGENTS:
        print("Starting Wire Check Orchestrator uAgent...")
        wire_check_agent.run()
    else:
        print("uAgents package not installed. Run 'pip install uagents' or check requirements.")
