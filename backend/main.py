"""The UnderCover backend."""

import json
import sqlite3
from collections.abc import AsyncIterator
from contextlib import asynccontextmanager
from datetime import UTC, datetime
from pathlib import Path
from typing import Annotated

from fastapi import Depends, FastAPI, HTTPException
from fastapi.responses import PlainTextResponse

from backend import db
from backend.models import (
    Claim,
    ClaimSummary,
    Customer,
    Decision,
    DecisionRequest,
    Handler,
    Payment,
    PaymentRequest,
    Policy,
    SignOff,
    SignOffRequest,
    StartRequest,
    Step,
    StepRequest,
)

INSTRUCTIONS = Path(__file__).parent / "instructions.md"


@asynccontextmanager
async def lifespan(_: FastAPI) -> AsyncIterator[None]:
    conn = db.connect()
    db.init(conn)
    conn.close()
    yield


app = FastAPI(title="UnderCover", lifespan=lifespan)
Db = Annotated[sqlite3.Connection, Depends(db.get_db)]


def find(conn: sqlite3.Connection, table: str, key: str, value: str) -> sqlite3.Row:
    """Return one row by its id, or raise 404."""
    row = conn.execute(
        f"SELECT * FROM {table} WHERE {key} = ?",  # noqa: S608
        (value,),
    ).fetchone()
    if row is None:
        raise HTTPException(404, f"{value} not found")
    return row


def now() -> str:
    """Return the current time in UTC, to the second."""
    return datetime.now(UTC).isoformat(timespec="seconds")


def dollars(amount: float) -> str:
    """Format an amount as US dollars, such as $1,250.00."""
    return f"${amount:,.2f}"


def to_claim(conn: sqlite3.Connection, row: sqlite3.Row) -> Claim:
    """Build a claim from its row, with its decision, sign-off and payment."""
    decision = None
    if row["decision"]:
        decision = Decision(
            decision=row["decision"],
            payout=row["payout"],
            reasons=row["reasons"],
            policy_section=row["policy_section"],
            decided_at=row["decided_at"],
        )
    sign_off = None
    if row["signed_off_by"]:
        handler = find(conn, "handlers", "handler_id", row["signed_off_by"])
        sign_off = SignOff(
            handler_id=row["signed_off_by"],
            handler_name=json.loads(handler["data"])["name"],
            signed_off_at=row["signed_off_at"],
        )
    paid = conn.execute(
        "SELECT amount, paid_at FROM payments WHERE claim_id = ?", (row["claim_id"],)
    ).fetchone()
    payment = Payment(amount=paid["amount"], paid_at=paid["paid_at"]) if paid else None
    return Claim(
        **json.loads(row["data"]) | {"status": row["status"]},
        decision=decision,
        sign_off=sign_off,
        payment=payment,
    )


@app.get("/api/health", operation_id="health")
def health() -> dict[str, str]:
    """Check that the backend is running."""
    return {"status": "ok"}


@app.get("/api/claims", operation_id="list_claims")
def list_claims(conn: Db) -> list[ClaimSummary]:
    """List the claims in the queue with where each one stands."""
    rows = conn.execute(
        """SELECT claims.data, claims.status, customers.data AS customer
        FROM claims JOIN customers
        ON customers.customer_id = json_extract(claims.data, '$.customer_id')
        ORDER BY claims.claim_id"""
    ).fetchall()
    return [
        ClaimSummary(
            **json.loads(row["data"]) | {"status": row["status"]},
            customer_name=json.loads(row["customer"])["name"],
        )
        for row in rows
    ]


@app.get("/api/claims/{claim_id}", operation_id="get_claim")
def get_claim(claim_id: str, conn: Db) -> Claim:
    """Get one claim in full, with the agent's decision and any payment."""
    return to_claim(conn, find(conn, "claims", "claim_id", claim_id))


@app.get("/api/policies/{policy_id}", operation_id="get_policy")
def get_policy(policy_id: str, conn: Db) -> Policy:
    """Get a policy: its plan, add-ons, trip and travelers."""
    return Policy.model_validate_json(
        find(conn, "policies", "policy_id", policy_id)["data"]
    )


@app.get("/api/customers/{customer_id}", operation_id="get_customer")
def get_customer(customer_id: str, conn: Db) -> Customer:
    """Get a customer, with their claim history."""
    return Customer.model_validate_json(
        find(conn, "customers", "customer_id", customer_id)["data"]
    )


@app.get("/api/handlers", operation_id="list_handlers")
def list_handlers(conn: Db) -> list[Handler]:
    """List the claims handlers."""
    rows = conn.execute("SELECT data FROM handlers ORDER BY handler_id").fetchall()
    return [Handler.model_validate_json(row["data"]) for row in rows]


@app.get(
    "/api/policy-wording",
    operation_id="get_policy_wording",
    response_class=PlainTextResponse,
)
def get_policy_wording() -> str:
    """Get the policy wording, the contract with the customer, as Markdown."""
    return db.read_data("policy_wording.md")


@app.get(
    "/api/instructions",
    operation_id="get_instructions",
    response_class=PlainTextResponse,
)
def get_instructions() -> str:
    """Get the UnderCover Agent's instructions, as Markdown."""
    return INSTRUCTIONS.read_text(encoding="utf-8")


@app.post("/api/claims/{claim_id}/start", operation_id="start_claim")
def start_claim(claim_id: str, body: StartRequest, conn: Db) -> Claim:
    """Mark a claim in progress for the agent run with this thread id."""
    row = find(conn, "claims", "claim_id", claim_id)
    if row["status"] not in ("waiting", "in_progress"):
        raise HTTPException(409, f"{claim_id} is already decided")
    conn.execute(
        "UPDATE claims SET status = 'in_progress', thread_id = ? WHERE claim_id = ?",
        (body.thread_id, claim_id),
    )
    conn.commit()
    return get_claim(claim_id, conn)


@app.post("/api/claims/{claim_id}/steps", operation_id="add_step")
def add_step(claim_id: str, body: StepRequest, conn: Db) -> Step:
    """Record one step the agent took on a claim."""
    find(conn, "claims", "claim_id", claim_id)
    created_at = now()
    cursor = conn.execute(
        "INSERT INTO steps (claim_id, thread_id, kind, text, created_at)"
        " VALUES (?, ?, ?, ?, ?)",
        (claim_id, body.thread_id, body.kind, body.text, created_at),
    )
    conn.commit()
    return Step(
        step_id=cursor.lastrowid or 0,
        kind=body.kind,
        text=body.text,
        created_at=created_at,
    )


@app.get("/api/claims/{claim_id}/steps", operation_id="list_steps")
def list_steps(claim_id: str, conn: Db) -> list[Step]:
    """List the steps of the agent's latest run on a claim, in order."""
    row = find(conn, "claims", "claim_id", claim_id)
    rows = conn.execute(
        "SELECT step_id, kind, text, created_at FROM steps"
        " WHERE claim_id = ? AND thread_id = ? ORDER BY step_id",
        (claim_id, row["thread_id"]),
    ).fetchall()
    return [Step(**dict(step)) for step in rows]


@app.post("/api/claims/{claim_id}/decision", operation_id="record_decision")
def record_decision(claim_id: str, body: DecisionRequest, conn: Db) -> Claim:
    """Record the agent's decision on a claim, with its payout and reasons."""
    row = find(conn, "claims", "claim_id", claim_id)
    if row["status"] != "in_progress":
        raise HTTPException(409, f"{claim_id} is not in progress")
    needs_sign_off = body.decision == "approve" and body.payout > db.approval_limit()
    conn.execute(
        """UPDATE claims SET status = ?, decision = ?, payout = ?, reasons = ?,
        policy_section = ?, decided_at = ? WHERE claim_id = ?""",
        (
            "awaiting_signoff" if needs_sign_off else "decided",
            body.decision,
            body.payout,
            body.reasons,
            body.policy_section,
            now(),
            claim_id,
        ),
    )
    conn.commit()
    return get_claim(claim_id, conn)


@app.post("/api/claims/{claim_id}/payment", operation_id="pay_claim")
def pay_claim(claim_id: str, body: PaymentRequest, conn: Db) -> Claim:
    """Pay an approved claim the amount of its payout."""
    claim = get_claim(claim_id, conn)
    limit = db.approval_limit()
    if claim.decision is None or claim.decision.decision != "approve":
        raise HTTPException(409, f"{claim_id} is not approved, so it cannot be paid")
    if claim.payment is not None:
        raise HTTPException(409, f"{claim_id} is already paid")
    if round(body.amount, 2) != round(claim.decision.payout, 2):
        raise HTTPException(
            409,
            f"The amount must be the approved payout of "
            f"{dollars(claim.decision.payout)}",
        )
    if body.amount > limit and claim.sign_off is None:
        raise HTTPException(
            409,
            f"A payout over {dollars(limit)} needs a handler's sign-off. "
            "The payment waits until a handler signs off.",
        )
    conn.execute(
        "INSERT INTO payments VALUES (?, ?, ?)", (claim_id, body.amount, now())
    )
    conn.commit()
    return get_claim(claim_id, conn)


@app.post("/api/claims/{claim_id}/sign-off", operation_id="sign_off_claim")
def sign_off_claim(claim_id: str, body: SignOffRequest, conn: Db) -> Claim:
    """Sign off a payout over the limit as a handler, which pays the claim."""
    row = find(conn, "claims", "claim_id", claim_id)
    handler = Handler.model_validate_json(
        find(conn, "handlers", "handler_id", body.handler_id)["data"]
    )
    if row["status"] != "awaiting_signoff":
        raise HTTPException(409, f"{claim_id} is not waiting for sign-off")
    if not handler.can_approve_over_limit:
        raise HTTPException(403, f"{handler.name} cannot sign off this payout")
    signed_off_at = now()
    conn.execute(
        """UPDATE claims SET status = 'decided', signed_off_by = ?, signed_off_at = ?
        WHERE claim_id = ?""",
        (handler.handler_id, signed_off_at, claim_id),
    )
    conn.execute(
        "INSERT INTO payments VALUES (?, ?, ?)",
        (claim_id, row["payout"], signed_off_at),
    )
    conn.commit()
    return get_claim(claim_id, conn)
