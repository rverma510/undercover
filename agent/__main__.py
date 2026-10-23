"""Work claims: uv run -m agent CLM-1001, or uv run -m agent for every waiting claim."""

import sys
from uuid import uuid4

from agent import main


def work(claim_ids: list[str]) -> None:
    """Run the agent on each claim and print its reply."""
    for claim_id in claim_ids or main.waiting_claims():
        print(f"{claim_id}: {main.run(claim_id, f'{claim_id}-{uuid4().hex[:8]}')}")


if __name__ == "__main__":
    work(sys.argv[1:])
