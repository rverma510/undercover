# Status

The claims pilot is built, as planned in `docs/PLAN.md`.

## Built

- `backend/`: FastAPI and SQLite. The database (`backend/undercover.db`, or the path in `UNDERCOVER_DB`) is seeded from `data/` on first start: the claims, policies, customers and handlers, never `data/evals/` or the claims manual. Read operations for claims, policies, customers, handlers, the policy wording and the agent's instructions (`backend/instructions.md`, with no operation to change them). Write operations to start a claim, record the agent's steps and decision, pay a claim and sign off. The backend refuses to pay a payout over $1,000.00 until a handler signs off, and signing off records the payment.
- `agent/`: the UnderCover Agent, `create_agent` on OpenRouter with `openai/gpt-6-luna` at low reasoning effort, or the model in `MODEL_NAME`. `run(claim_id, thread_id)` marks the claim in progress, takes its instructions and the policy wording from the API, and records every tool call, tool result and reply as a step. Its tools read the claim, the policy and the customer, record the decision and pay; it has no way to sign off.
- `dashboard/`: React on the brand, with light and dark modes. Three views by the URL hash: the queue with a count in each state (`#/`), a claim in full (`#/claims/CLM-1001`), and the agent's instructions, read only (`#/instructions`). The queue refreshes every 3 seconds. A claim refreshes every 2 seconds until it's decided and shows the agent's steps live while it's in progress, the decision with its payout, reasons, policy section and payment, the policy, the customer's claim history, and a sign-off panel when a payout over $1,000.00 is waiting.
- `e2e/`: Playwright tests of the queue, live steps, a paid approval and the sign-off flow. They run on ports 8100 and 5174 with their own freshly seeded database in the system's temp folder, so they never touch dev data.

## Running it

- `npm run dev` starts the backend on port 8000 and the dashboard on port 5173.
- `npm run agent -- CLM-1001` runs the agent on one claim, and `npm run agent` on every waiting claim. The backend must be running.
- `npm run reset` wipes the database and reseeds it from `data/`.
- `npm run check` runs every check.

## Not built yet

Scoring the agent against the handlers' decisions in `data/evals/`, which comes with the evaluations later in the course.
