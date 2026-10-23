# Status

The claims pilot, built in phases from `docs/PLAN.md`.

## Built

- `backend/`: FastAPI and SQLite. The database (`backend/undercover.db`, or the path in `UNDERCOVER_DB`) is seeded from `data/` on first start, never from `data/evals/`. Read operations for claims, policies, customers, handlers, the policy wording and the agent's instructions (`backend/instructions.md`). Write operations to start a claim, record the agent's steps and decision, pay a claim and sign off. The backend refuses to pay a payout over $1,000.00 until a handler signs off, and signing off records the payment.
- `agent/`: the UnderCover Agent, `create_agent` on OpenRouter. `run(claim_id, thread_id)` marks the claim in progress, takes its instructions and the policy wording from the API, and records every tool call, tool result and reply as a step. Its tools read the claim, the policy and the customer, record the decision and pay; it has no way to sign off.
- `dashboard/`: React on the brand, with light and dark modes. Three views by the URL hash: the queue with a count in each state (`#/`), a claim in full with its policy and the customer's history (`#/claims/CLM-1001`), and the agent's instructions, read only (`#/instructions`).
- `e2e/`: one test of the queue.

## Running it

- `npm run dev` starts the backend on port 8000 and the dashboard on port 5173.
- `npm run agent -- CLM-1001` runs the agent on one claim, and `npm run agent` on every waiting claim. The backend must be running.
- `npm run reset` wipes the database and reseeds it from `data/`.
- `npm run check` runs every check.
