"""The UnderCover Agent."""

import json
import os
from typing import Literal

import httpx
from dotenv import load_dotenv
from langchain.agents import create_agent
from langchain_core.language_models import BaseChatModel
from langchain_core.messages import AIMessage, BaseMessage, ToolMessage
from langchain_core.tools import tool
from langchain_openai import ChatOpenAI
from pydantic import SecretStr

load_dotenv(override=True)

BACKEND_URL = "http://localhost:8000"
OPENROUTER_BASE_URL = "https://openrouter.ai/api/v1"
DEFAULT_MODEL = "openai/gpt-6-luna"
STEP_TEXT_LIMIT = 300


def backend() -> httpx.Client:
    """Return a client for the UnderCover backend."""
    return httpx.Client(base_url=BACKEND_URL, timeout=30)


def send(method: str, path: str, body: object) -> httpx.Response:
    """Send one request to the backend."""
    with backend() as client:
        return client.request(method, path, json=body)


def for_model(response: httpx.Response) -> str:
    """Return a response for the model, with a refusal as text it can act on."""
    if response.is_client_error:
        return f"Refused: {response.json()['detail']}"
    response.raise_for_status()
    return response.text


@tool
def get_claim(claim_id: str) -> str:
    """Get a claim in full: the story, the items claimed and the documents."""
    return for_model(send("GET", f"/api/claims/{claim_id}", None))


@tool
def get_policy(policy_id: str) -> str:
    """Get a policy: its plan, add-ons, purchase date, trip dates and travelers."""
    return for_model(send("GET", f"/api/policies/{policy_id}", None))


@tool
def get_customer(customer_id: str) -> str:
    """Get a customer, with their claim history."""
    return for_model(send("GET", f"/api/customers/{customer_id}", None))


@tool
def record_decision(
    claim_id: str,
    decision: Literal["approve", "decline", "refer"],
    payout: float,
    reasons: str,
    policy_section: str,
) -> str:
    """Record your decision on a claim: the payout (0 unless you approve), the
    reasons in two or three sentences, and the policy section it rests on."""
    body = {
        "decision": decision,
        "payout": payout,
        "reasons": reasons,
        "policy_section": policy_section,
    }
    return for_model(send("POST", f"/api/claims/{claim_id}/decision", body))


@tool
def pay_claim(claim_id: str, amount: float) -> str:
    """Pay an approved claim its payout."""
    return for_model(
        send("POST", f"/api/claims/{claim_id}/payment", {"amount": amount})
    )


TOOLS = [get_claim, get_policy, get_customer, record_decision, pay_claim]


def model() -> ChatOpenAI:
    """Return the model named in MODEL_NAME, or GPT-6 Luna by default."""
    name = os.getenv("MODEL_NAME")
    return ChatOpenAI(
        model=name or DEFAULT_MODEL,
        base_url=OPENROUTER_BASE_URL,
        api_key=SecretStr(os.environ["OPENROUTER_API_KEY"]),
        reasoning_effort=None if name else "low",
    )


def system_prompt() -> str:
    """Return the agent's instructions followed by the policy wording."""
    instructions = send("GET", "/api/instructions", None)
    wording = send("GET", "/api/policy-wording", None)
    instructions.raise_for_status()
    wording.raise_for_status()
    return f"{instructions.text}\n\n{wording.text}"


def steps(message: BaseMessage) -> list[tuple[str, str]]:
    """Describe a message as the steps the dashboard shows."""
    if isinstance(message, ToolMessage):
        return [("tool_result", message.text[:STEP_TEXT_LIMIT])]
    if isinstance(message, AIMessage) and message.tool_calls:
        return [
            ("tool_call", f"{call['name']}({json.dumps(call['args'])})")
            for call in message.tool_calls
        ]
    return [("reply", message.text)]


def waiting_claims() -> list[str]:
    """Return the ids of the claims waiting in the queue."""
    response = send("GET", "/api/claims", None)
    response.raise_for_status()
    return [c["claim_id"] for c in response.json() if c["status"] == "waiting"]


def run(claim_id: str, thread_id: str, llm: BaseChatModel | None = None) -> str:
    """Run the agent on one claim, recording each step, and return its reply."""
    send(
        "POST", f"/api/claims/{claim_id}/start", {"thread_id": thread_id}
    ).raise_for_status()
    agent = create_agent(llm or model(), tools=TOOLS, system_prompt=system_prompt())
    reply = ""
    for update in agent.stream(
        {"messages": [{"role": "user", "content": f"Please decide claim {claim_id}."}]},
        config={"configurable": {"thread_id": thread_id}},
        stream_mode="updates",
    ):
        for output in update.values():
            for message in output["messages"]:
                for kind, text in steps(message):
                    send(
                        "POST",
                        f"/api/claims/{claim_id}/steps",
                        {"thread_id": thread_id, "kind": kind, "text": text},
                    ).raise_for_status()
                    reply = text if kind == "reply" else reply
    return reply
