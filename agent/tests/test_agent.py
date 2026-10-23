import runpy

import pytest
from fastapi.testclient import TestClient
from langchain_core.language_models.fake_chat_models import GenericFakeChatModel
from langchain_core.messages import AIMessage

from agent import main
from backend.main import app


class StubModel(GenericFakeChatModel):
    """A chat model that gives scripted replies in place of a real model."""

    def bind_tools(self, tools, **kwargs):
        return self


@pytest.fixture
def client(tmp_path, monkeypatch):
    monkeypatch.setenv("UNDERCOVER_DB", str(tmp_path / "test.db"))
    monkeypatch.setattr(main, "backend", lambda: TestClient(app))
    with TestClient(app) as client:
        yield client


def calls(*tool_calls):
    return AIMessage(
        content="",
        tool_calls=[
            {"name": name, "args": args, "id": f"{name}-{i}"}
            for i, (name, args) in enumerate(tool_calls)
        ],
    )


def decision(claim_id, payout):
    return {
        "claim_id": claim_id,
        "decision": "approve",
        "payout": payout,
        "reasons": "The claim is covered. The costs are within the limit.",
        "policy_section": "Section 3. Trip Delay",
    }


def stub(*replies):
    return StubModel(messages=iter(replies))


def test_run_approves_and_pays(client):
    llm = stub(
        calls(
            ("get_claim", {"claim_id": "CLM-1001"}),
            ("get_policy", {"policy_id": "POL-2001"}),
            ("get_customer", {"customer_id": "CUS-3001"}),
        ),
        calls(("record_decision", decision("CLM-1001", 420.0))),
        calls(("pay_claim", {"claim_id": "CLM-1001", "amount": 420.0})),
        AIMessage(content="Approved, $420.00."),
    )
    assert main.run("CLM-1001", "thread-1", llm) == "Approved, $420.00."
    claim = client.get("/api/claims/CLM-1001").json()
    assert claim["status"] == "decided"
    assert claim["payment"]["amount"] == 420.0
    steps = client.get("/api/claims/CLM-1001/steps").json()
    assert [step["kind"] for step in steps] == [
        *["tool_call"] * 3,
        *["tool_result"] * 3,
        "tool_call",
        "tool_result",
        "tool_call",
        "tool_result",
        "reply",
    ]
    assert steps[0]["text"] == 'get_claim({"claim_id": "CLM-1001"})'
    assert all(len(step["text"]) <= main.STEP_TEXT_LIMIT for step in steps)


def test_payment_over_the_limit_is_blocked_even_when_the_agent_pays(client):
    llm = stub(
        calls(("record_decision", decision("CLM-1003", 1500.0))),
        calls(("pay_claim", {"claim_id": "CLM-1003", "amount": 1500.0})),
        AIMessage(content="Approved, $1,500.00, waiting for sign-off."),
    )
    main.run("CLM-1003", "thread-1", llm)
    claim = client.get("/api/claims/CLM-1003").json()
    assert claim["status"] == "awaiting_signoff"
    assert claim["payment"] is None
    results = [
        step["text"]
        for step in client.get("/api/claims/CLM-1003/steps").json()
        if step["kind"] == "tool_result"
    ]
    assert results[-1].startswith(
        "Refused: A payout over $1,000.00 needs a handler's sign-off."
    )


def test_tools_have_no_sign_off():
    assert [t.name for t in main.TOOLS] == [
        "get_claim",
        "get_policy",
        "get_customer",
        "record_decision",
        "pay_claim",
    ]


def test_system_prompt_is_the_instructions_then_the_wording(client):
    instructions = client.get("/api/instructions").text
    wording = client.get("/api/policy-wording").text
    assert main.system_prompt() == f"{instructions}\n\n{wording}"


def test_waiting_claims(client):
    client.post("/api/claims/CLM-1001/start", json={"thread_id": "t"})
    waiting = main.waiting_claims()
    assert len(waiting) == 24
    assert "CLM-1001" not in waiting


def test_command_works_the_named_claims(monkeypatch, capsys):
    monkeypatch.setattr(main, "run", lambda claim_id, thread_id: f"done {claim_id}")
    monkeypatch.setattr("sys.argv", ["agent", "CLM-1001", "CLM-1002"])
    runpy.run_module("agent", run_name="__main__")
    assert (
        capsys.readouterr().out == "CLM-1001: done CLM-1001\nCLM-1002: done CLM-1002\n"
    )


def test_command_works_every_waiting_claim(monkeypatch, capsys):
    monkeypatch.setattr(main, "waiting_claims", lambda: ["CLM-1005"])
    monkeypatch.setattr(main, "run", lambda claim_id, thread_id: thread_id)
    monkeypatch.setattr("sys.argv", ["agent"])
    runpy.run_module("agent", run_name="__main__")
    assert capsys.readouterr().out.startswith("CLM-1005: CLM-1005-")


def test_model_name(monkeypatch):
    monkeypatch.setenv("OPENROUTER_API_KEY", "test-key")
    monkeypatch.delenv("MODEL_NAME", raising=False)
    assert main.model().model_name == "openai/gpt-6-luna"
    monkeypatch.setenv("MODEL_NAME", "openrouter/free")
    assert main.model().model_name == "openrouter/free"
