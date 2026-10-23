"""The UnderCover backend."""

import json
import sqlite3
from collections.abc import AsyncIterator
from contextlib import asynccontextmanager
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
    Handler,
    Payment,
    Policy,
    SignOff,
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
