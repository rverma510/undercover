# Status

The claims pilot, built in phases from `docs/PLAN.md`.

## Built

- `backend/`: FastAPI and SQLite. The database (`backend/undercover.db`, or the path in `UNDERCOVER_DB`) is seeded from `data/` on first start, never from `data/evals/`. Read operations for claims, policies, customers, handlers, the policy wording and the agent's instructions (`backend/instructions.md`). Write operations to start a claim, record the agent's steps and decision, pay a claim and sign off. The backend refuses to pay a payout over $1,000.00 until a handler signs off, and signing off records the payment.
- `agent/`: still the hello-world agent.
- `dashboard/`: still the hello-world page.
- `e2e/`: one test of that page.

## Running it

- `npm run dev` starts the backend on port 8000 and the dashboard on port 5173.
- `npm run reset` wipes the database and reseeds it from `data/`.
- `npm run check` runs every check.
