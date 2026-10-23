import json

import pytest

from backend import db

SIGN_OFF_NEEDED = "A payout over $1,000.00 needs a handler's sign-off."


def start(client, claim_id="CLM-1001", thread_id="thread-1"):
    response = client.post(
        f"/api/claims/{claim_id}/start", json={"thread_id": thread_id}
    )
    assert response.status_code == 200
    return response.json()


def decide(client, decision="approve", payout=420.0, claim_id="CLM-1001"):
    return client.post(
        f"/api/claims/{claim_id}/decision",
        json={
            "decision": decision,
            "payout": payout,
            "reasons": "The delay was covered. The costs are within the limit.",
            "policy_section": "Section 3. Trip Delay",
        },
    )


def pay(client, amount, claim_id="CLM-1001"):
    return client.post(f"/api/claims/{claim_id}/payment", json={"amount": amount})


def sign_off(client, handler_id="HND-01", claim_id="CLM-1001"):
    return client.post(
        f"/api/claims/{claim_id}/sign-off", json={"handler_id": handler_id}
    )


def test_start_marks_the_claim_in_progress(client):
    assert start(client)["status"] == "in_progress"
    assert start(client, thread_id="thread-2")["status"] == "in_progress"


def test_cannot_start_a_decided_claim(client):
    start(client)
    decide(client)
    response = client.post("/api/claims/CLM-1001/start", json={"thread_id": "t"})
    assert response.status_code == 409


def test_steps_of_the_latest_run(client):
    start(client, thread_id="first")
    client.post(
        "/api/claims/CLM-1001/steps",
        json={"thread_id": "first", "kind": "reply", "text": "old run"},
    )
    start(client, thread_id="second")
    for kind, text in [("tool_call", "get_claim"), ("tool_result", "the claim")]:
        response = client.post(
            "/api/claims/CLM-1001/steps",
            json={"thread_id": "second", "kind": kind, "text": text},
        )
        assert response.status_code == 200
    steps = client.get("/api/claims/CLM-1001/steps").json()
    assert [(step["kind"], step["text"]) for step in steps] == [
        ("tool_call", "get_claim"),
        ("tool_result", "the claim"),
    ]


def test_steps_on_an_unknown_claim(client):
    response = client.post(
        "/api/claims/CLM-9999/steps",
        json={"thread_id": "t", "kind": "reply", "text": "x"},
    )
    assert response.status_code == 404


def test_decision_needs_a_claim_in_progress(client):
    assert decide(client).status_code == 409


@pytest.mark.parametrize(
    "body",
    [
        {"decision": "maybe", "payout": 0},
        {"decision": "decline", "payout": 10},
        {"decision": "approve", "payout": -1},
        {"decision": "approve", "payout": 10, "reasons": ""},
    ],
)
def test_decision_is_validated(client, body):
    start(client)
    full = {"reasons": "Reasons.", "policy_section": "Section 3"} | body
    response = client.post("/api/claims/CLM-1001/decision", json=full)
    assert response.status_code == 422


def test_approve_and_pay_within_the_limit(client):
    start(client)
    claim = decide(client).json()
    assert claim["status"] == "decided"
    assert claim["decision"]["decision"] == "approve"
    assert claim["decision"]["payout"] == 420.0
    assert claim["payment"] is None
    paid = pay(client, 420.0).json()
    assert paid["payment"]["amount"] == 420.0


def test_a_payout_of_exactly_the_limit_needs_no_sign_off(client):
    start(client)
    assert decide(client, payout=1000.0).json()["status"] == "decided"
    assert pay(client, 1000.0).status_code == 200


def test_a_payout_over_the_limit_waits_for_sign_off(client):
    start(client)
    assert decide(client, payout=1000.01).json()["status"] == "awaiting_signoff"
    response = pay(client, 1000.01)
    assert response.status_code == 409
    assert response.json()["detail"].startswith(SIGN_OFF_NEEDED)
    assert client.get("/api/claims/CLM-1001").json()["payment"] is None


def test_the_amount_must_match_the_payout(client):
    start(client)
    decide(client, payout=420.0)
    response = pay(client, 900.0)
    assert response.status_code == 409
    assert (
        response.json()["detail"] == "The amount must be the approved payout of $420.00"
    )


@pytest.mark.parametrize("decision", ["decline", "refer"])
def test_cannot_pay_a_claim_that_is_not_approved(client, decision):
    start(client)
    assert decide(client, decision=decision, payout=0).json()["status"] == "decided"
    assert pay(client, 100.0).status_code == 409


def test_cannot_pay_twice(client):
    start(client)
    decide(client)
    pay(client, 420.0)
    assert pay(client, 420.0).status_code == 409


def test_sign_off_pays_the_claim(client):
    start(client, claim_id="CLM-1003")
    decide(client, payout=1500.0, claim_id="CLM-1003")
    claim = sign_off(client, claim_id="CLM-1003").json()
    assert claim["status"] == "decided"
    assert claim["sign_off"]["handler_name"] == "Dana Whitfield"
    assert claim["payment"]["amount"] == 1500.0
    assert pay(client, 1500.0, claim_id="CLM-1003").status_code == 409


def test_sign_off_by_an_unknown_handler(client):
    start(client)
    decide(client, payout=1500.0)
    assert sign_off(client, handler_id="HND-99").status_code == 404


def test_sign_off_needs_a_claim_waiting_for_it(client):
    start(client)
    decide(client, payout=420.0)
    assert sign_off(client).status_code == 409


def test_sign_off_needs_a_handler_who_may_approve_over_the_limit(client):
    conn = db.connect()
    handler = {
        "handler_id": "HND-09",
        "name": "Trainee",
        "role": "Trainee",
        "email": "trainee@undercover.example",
        "can_approve_over_limit": False,
    }
    conn.execute("INSERT INTO handlers VALUES (?, ?)", ("HND-09", json.dumps(handler)))
    conn.commit()
    start(client)
    decide(client, payout=1500.0)
    assert sign_off(client, handler_id="HND-09").status_code == 403
