import runpy

from backend import db

ANSWER_KEY_FIELDS = [
    "calculation",
    "failure_class",
    "difficulty",
    "over_approval_limit",
]


def test_health(client):
    assert client.get("/api/health").json() == {"status": "ok"}


def test_list_claims(client):
    claims = client.get("/api/claims").json()
    assert len(claims) == 25
    assert {claim["status"] for claim in claims} == {"waiting"}
    assert claims[0] == {
        "claim_id": "CLM-1001",
        "customer_name": "Maya Patel",
        "claim_type": "trip_delay",
        "summary": "Flight home canceled by the airline, rebooked the next morning",
        "amount_claimed": 420.0,
        "submitted_on": "2026-06-24",
        "status": "waiting",
    }


def test_get_claim(client):
    claim = client.get("/api/claims/CLM-1001").json()
    assert claim["customer_id"] == "CUS-3001"
    assert len(claim["items"]) == 3
    assert len(claim["documents"]) == 4
    assert claim["status"] == "waiting"
    assert claim["decision"] is None
    assert claim["sign_off"] is None
    assert claim["payment"] is None


def test_get_policy(client):
    policy = client.get("/api/policies/POL-2001").json()
    assert policy["plan"] == "premium"
    assert policy["trip"]["destination"] == "Rome, Italy"


def test_get_customer(client):
    customer = client.get("/api/customers/CUS-3001").json()
    assert customer["name"] == "Maya Patel"
    assert customer["previous_claims"][0]["claim_id"] == "CLM-0412"


def test_list_handlers(client):
    handlers = client.get("/api/handlers").json()
    assert [handler["name"] for handler in handlers] == [
        "Dana Whitfield",
        "Marcus Oyelaran",
        "Priya Raman",
    ]


def test_unknown_ids(client):
    for path in ["claims/CLM-9999", "policies/POL-9999", "customers/CUS-9999"]:
        assert client.get(f"/api/{path}").status_code == 404


def test_policy_wording(client):
    response = client.get("/api/policy-wording")
    assert response.text.startswith("# UnderCover Travel Insurance: Policy Wording")


def test_instructions(client):
    assert client.get("/api/instructions").text.startswith("# The UnderCover Agent")


def test_seed_reads_only_the_queue_and_records(tmp_path, monkeypatch):
    read = []
    real = db.read_data
    monkeypatch.setattr(db, "read_data", lambda name: read.append(name) or real(name))
    monkeypatch.setenv("UNDERCOVER_DB", str(tmp_path / "seed.db"))
    counts = db.seed(db.connect())
    assert counts == {"claims": 25, "policies": 50, "customers": 49, "handlers": 3}
    assert sorted(read) == [
        "claims.json",
        "customers.json",
        "handlers.json",
        "policies.json",
    ]


def keys(value):
    if isinstance(value, dict):
        return set(value) | {key for item in value.values() for key in keys(item)}
    if isinstance(value, list):
        return {key for item in value for key in keys(item)}
    return set()


def test_no_answer_key_in_responses(client):
    for claim in client.get("/api/claims").json():
        claim_id = claim["claim_id"]
        found = keys(client.get(f"/api/claims/{claim_id}").json())
        assert not found & set(ANSWER_KEY_FIELDS)


def test_init_seeds_only_an_empty_database(tmp_path, monkeypatch):
    monkeypatch.setenv("UNDERCOVER_DB", str(tmp_path / "init.db"))
    conn = db.connect()
    db.init(conn)
    conn.execute("UPDATE claims SET status = 'decided' WHERE claim_id = 'CLM-1001'")
    conn.commit()
    db.init(conn)
    row = conn.execute("SELECT status FROM claims WHERE claim_id = 'CLM-1001'")
    assert row.fetchone()["status"] == "decided"


def test_seed_command(tmp_path, monkeypatch, capsys):
    monkeypatch.setenv("UNDERCOVER_DB", str(tmp_path / "command.db"))
    runpy.run_module("backend.seed", run_name="__main__")
    assert capsys.readouterr().out == (
        "Seeded 25 claims, 50 policies, 49 customers, 3 handlers\n"
    )


def test_every_operation_is_documented_with_required_inputs(client):
    schema = client.get("/openapi.json").json()
    for path in schema["paths"].values():
        for operation in path.values():
            assert operation["operationId"]
            assert "\n" not in operation["description"]
            for parameter in operation.get("parameters", []):
                assert parameter["required"]
