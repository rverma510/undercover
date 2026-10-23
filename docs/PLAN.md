# Plan: the claims pilot

This plan builds the pilot in `docs/SPEC.md` on the hello-world skeleton in `docs/STATUS.md`. It follows `docs/TECH_STACK.md`, `docs/CODE_STANDARDS.md`, `docs/PROCESS.md` and `docs/BRAND.md`.

## The shape of it

```
dashboard (React)  ──HTTP──▶  backend (FastAPI + SQLite)  ◀──HTTP──  agent (create_agent on OpenRouter)
  queue, claim, steps,          the only owner of the data,           reads claims and its instructions,
  instructions, sign-off        enforces the $1,000 rule               records its decision and its steps
                                      ▲
                                      │ seeded once from data/ (never data/evals/)
```

- **The backend owns the data and the rules.** The $1,000 sign-off rule lives in the backend's payment operation, not in the agent's instructions, so the payment is blocked even if the agent tries to pay. The agent has no sign-off tool, and only a handler, through the dashboard, can sign off.
- **The agent talks only to the backend's API.** It fetches its instructions and the policy wording from the API, reads the claim, the policy and the customer through tools, and records its decision and pays through tools.
- **The dashboard is a view onto the backend, plus one action:** a handler's sign-off.
- **The answer key stays out.** The backend's seed loader reads a fixed list of files in `data/` and never `data/evals/`, so nothing the agent can reach holds a handler's decision. The claims manual is also left out, as the spec says, and so are `data/security/`, `data/knowledge.json` and `data/policy_wording_short.md`.

### Claim states

```
waiting ──start──▶ in_progress ──record decision──▶ decided                 (decline, refer, or approve ≤ $1,000)
                                       └───────────▶ awaiting_signoff ──handler signs off──▶ decided   (approve > $1,000)
```

The dashboard labels them Waiting, In progress, Waiting for sign-off and Decided. The seed data's `open` becomes `waiting`. A referred claim is Decided with the decision Refer, because the agent's work on it is done and a handler picks it up from there.

### Paying a claim

Paying is its own operation that takes the amount, as the tech stack asks. The backend refuses a payment with 409 unless all of these hold:

- the claim's decision is Approve and it has not been paid yet
- the amount equals the payout in the decision
- the payout is $1,000.00 or less, or a handler has signed off

"Over $1,000" means more than $1,000.00, so a payout of exactly $1,000.00 needs no sign-off. When a handler signs off, the backend records the sign-off and the payment of the approved payout together, and the claim becomes Decided. No real money moves: a payment is a row in the database.

### Showing the agent's work

The agent's entry point runs the agent with `stream`, and for every step, which is a tool call, a tool result or the final reply, it posts a short line to the backend. The dashboard polls the claim's steps every two seconds while the claim is In progress. I chose streaming over LangChain middleware because it needs no new concepts and keeps the agent's loop untouched; the harness build on Week 1 Day 5 is where middleware comes in.

### Starting the agent

The agent runs from the command line: `npm run agent -- CLM-1001` works one claim, and `npm run agent` works every waiting claim in the queue, one after another. The dashboard shows each claim moving through its states as the agent works. I chose this over a "Run" button in the dashboard because it keeps the backend from depending on the agent, and the spec asks the dashboard to show the work rather than start it. A button is easy to add later if you want one.

### Data model (SQLite, standard library `sqlite3`)

| Table | Columns |
|---|---|
| `claims` | `claim_id`, `data` (the claim as JSON), `status`, `thread_id`, `decision`, `payout`, `reasons`, `policy_section`, `decided_at`, `signed_off_by`, `signed_off_at` |
| `payments` | `claim_id`, `amount`, `paid_at` |
| `steps` | `step_id`, `claim_id`, `thread_id`, `kind` (`tool_call`, `tool_result`, `reply`), `text`, `created_at` |
| `policies`, `customers`, `handlers` | the id and the record as JSON |

The records from `data/` are stored as JSON because the backend only reads them whole, which keeps the schema small. The database file is `backend/undercover.db` by default, or the path in `UNDERCOVER_DB`; it's ignored by git. The backend seeds it on startup when it's empty, and `npm run reset` wipes and reseeds it. The approval limit comes from `data/company.json`.

### The API

Every operation has an `operation_id`, a one-line docstring and no optional inputs.

| Operation | Route | Used by |
|---|---|---|
| `health` | `GET /api/health` | dashboard |
| `list_claims` | `GET /api/claims` | dashboard |
| `get_claim` | `GET /api/claims/{claim_id}` | agent, dashboard |
| `get_policy` | `GET /api/policies/{policy_id}` | agent, dashboard |
| `get_customer` | `GET /api/customers/{customer_id}` | agent, dashboard |
| `list_handlers` | `GET /api/handlers` | dashboard |
| `get_policy_wording` | `GET /api/policy-wording` | agent |
| `get_instructions` | `GET /api/instructions` | agent, dashboard |
| `start_claim` | `POST /api/claims/{claim_id}/start` with `thread_id` | agent's entry point |
| `add_step` | `POST /api/claims/{claim_id}/steps` with `thread_id`, `kind`, `text` | agent's entry point |
| `list_steps` | `GET /api/claims/{claim_id}/steps` | dashboard |
| `record_decision` | `POST /api/claims/{claim_id}/decision` with `decision`, `payout`, `reasons`, `policy_section` | agent |
| `pay_claim` | `POST /api/claims/{claim_id}/payment` with `amount` | agent |
| `sign_off_claim` | `POST /api/claims/{claim_id}/sign-off` with `handler_id` | dashboard |

There is no operation to change the instructions, which makes them read only. `list_steps` returns the steps of the claim's latest run, the one whose `thread_id` `start_claim` stored.

### The agent's tools

`get_claim`, `get_policy`, `get_customer`, `record_decision` and `pay_claim`, each a thin call to the API. When the backend refuses a call with a 4xx, the tool returns the backend's message to the model instead of raising, so the agent can see "this payout needs a handler's sign-off" and finish cleanly. That's the one place the agent handles an error.

The system prompt is the instructions from `get_instructions` followed by the policy wording from `get_policy_wording`. The wording is about 8 KB, short enough to send every time, so the model never has to remember to fetch it. The instructions live in `backend/instructions.md` and tell the agent to read the claim, the policy and the customer's history, check the claim against the wording (the covered trip dates, the 90-day filing window, waiting periods, exclusions, the documents each benefit needs), work out the payout by section 10, record the decision with two or three sentences and the section it rests on, and pay an approved claim.

### The dashboard

One page with three views, switched by the URL hash (`#/`, `#/claims/CLM-1001`, `#/instructions`) so we don't add a router library:

- **Queue:** a count of claims in each state, and a table of the claims with id, customer, type, amount claimed, submitted date and a state badge. It refreshes every few seconds.
- **Claim:** the story, the items, the documents, the policy and the customer's claim history; the agent's decision, payout, reasons and policy section; whether it's paid; the agent's steps; and, when it's waiting for sign-off, a handler picker and a Sign off button.
- **Instructions:** the agent's instructions as read-only text.

Brand: Instrument Sans throughout, JetBrains Mono for ids and amounts, the brand colors with light and dark modes from `prefers-color-scheme`. State badges: Waiting in Cerulean, In progress in Marigold, Waiting for sign-off in Coral, Decided in Sea Green. Money shows as $1,250.00.

### Testing

- **pytest** for the backend through FastAPI's `TestClient` on a temporary database, and for the agent with the existing stub model, scripted tool calls and the backend app in-process. Tests never call a model.
- **vitest** with Testing Library for the dashboard components, with `fetch` stubbed.
- **Playwright** end-to-end, on their own ports (backend 8100, dashboard 5174) and their own freshly seeded database, so a test run never touches your dev data. The tests play the agent's part by calling the API directly, then check the screens.
- **Playwright MCP** checks of the running app, by me, as listed in each phase.

## Phase 1: Backend data and read operations

Builds the database, the seed loader and the read side of the API: everything the agent and the dashboard need to look at a claim.

- `backend/db.py`: the schema, a connection per request, and `seed()`, which loads `claims.json`, `policies.json`, `customers.json` and `handlers.json` from `data/`.
- `backend/seed.py` so `uv run -m backend.seed` (`npm run reset`) wipes and reseeds the database.
- `backend/instructions.md`, a first version of the agent's instructions.
- The read operations: `list_claims`, `get_claim`, `get_policy`, `get_customer`, `list_handlers`, `get_policy_wording`, `get_instructions`, with Pydantic response models.
- `backend/*.db` added to `.gitignore`.

Success criteria:

- [x] `uv run pytest -q backend` passes, with tests for each operation, 404s for unknown ids, and seeding into an empty database.
- [x] A test asserts the seed loader never opens a path under `data/evals/` and that no response contains a field from the answer key (`calculation`, `failure_class`, `difficulty`).
- [x] `npm run reset` prints that it seeded 25 claims, 50 policies, 49 customers and 3 handlers.
- [x] With `npm run dev:backend` running, `curl -s localhost:8000/api/claims` returns 25 claims, each with `status` `waiting` and the customer's name.
- [x] `curl -s localhost:8000/api/claims/CLM-1001` returns Maya Patel's claim with its 3 items and 4 documents and no decision.
- [x] `curl -s localhost:8000/api/claims/CLM-9999` returns 404.
- [x] `curl -s localhost:8000/api/policy-wording` starts with `# UnderCover Travel Insurance: Policy Wording`; nothing serves the claims manual.
- [x] `curl -s localhost:8000/openapi.json` shows an `operationId` and a one-line description (from the docstring) on every route, and no optional parameters.
- [x] `npm run check:python` passes with coverage of 80% or more.

## Phase 2: Backend decisions, payments and sign-off

Builds the write side: the claim's states, the agent's steps, decisions, payments and the $1,000 rule.

- `start_claim`, `add_step`, `list_steps`, `record_decision`, `pay_claim` and `sign_off_claim`.
- Decision inputs are validated: `decision` is `approve`, `decline` or `refer`; `payout` is 0 unless the decision is approve; `reasons` and `policy_section` are not empty.
- State changes are checked: a claim can start only when Waiting or In progress (a re-run), and a decision can be recorded only when In progress. Anything else returns 409.

Success criteria:

- [ ] `uv run pytest -q backend` passes, with tests for every state change and every refusal below.
- [ ] Recording an approve of $420.00 moves the claim to `decided`; paying $420.00 then records a payment.
- [ ] Recording an approve of $1,000.00 moves the claim to `decided`, and paying $1,000.00 succeeds.
- [ ] Recording an approve of $1,000.01 moves the claim to `awaiting_signoff`, and paying $1,000.01 returns 409 with a message that a handler must sign off, and no payment is recorded.
- [ ] Paying an amount other than the decision's payout, paying a declined or referred claim, and paying twice all return 409.
- [ ] Signing off with a handler id from `handlers.json` records the sign-off and the payment of the payout and moves the claim to `decided`; an unknown handler returns 404; signing off a claim that isn't waiting for sign-off returns 409.
- [ ] `list_steps` returns only the steps of the latest run, in order.
- [ ] A `curl` walk-through against the dev backend shows the same: start CLM-1003, record an approve of $1,500.00, the payment is refused with 409, sign off as HND-01, and `GET /api/claims/CLM-1003` shows it decided, signed off by Dana Whitfield and paid $1,500.00. `npm run reset` afterwards.
- [ ] `npm run check:python` passes with coverage of 80% or more.

## Phase 3: The UnderCover Agent

Replaces the hello-world agent with the claims agent.

- `agent/main.py`: the tools above; `run(claim_id, thread_id)`, which calls `start_claim`, builds the system prompt from the API, streams the agent and posts each step with `add_step`, and returns the final reply. The model stays `openai/gpt-6-luna` at low reasoning effort, or `MODEL_NAME` when set.
- `agent/__main__.py`: `uv run -m agent CLM-1001` works the claims named, and `uv run -m agent` works every waiting claim. `npm run agent` runs it.
- `backend/instructions.md` filled out as described above.

Success criteria:

- [ ] `uv run pytest -q agent` passes, with no model calls: the stub model and the backend app run in-process.
- [ ] A stub run on CLM-1001 that reads the claim, policy and customer, records an approve of $420.00 and pays it leaves the claim `decided` and paid, with each tool call, tool result and the reply recorded as steps.
- [ ] A stub run that approves $1,500.00 and then calls `pay_claim` with $1,500.00 gets the backend's refusal back as a tool result, the run finishes without an error, the claim is `awaiting_signoff` and no payment is recorded.
- [ ] A test asserts the agent's tools are exactly `get_claim`, `get_policy`, `get_customer`, `record_decision` and `pay_claim`, with no sign-off.
- [ ] A test asserts the system prompt is the instructions from the API followed by the policy wording.
- [ ] The existing test that `MODEL_NAME` picks the model still passes.
- [ ] `npm run check:python` passes with coverage of 80% or more.

## Phase 4: Dashboard views

Builds the three read-only views on the brand.

- Google Fonts and the brand's colors as CSS variables, with light and dark modes.
- The Queue, Claim and Instructions views, switched by the URL hash, with a small typed API client in `dashboard/src/api.ts`.
- Shared helpers for money (`$1,250.00`) and state labels and colors.

Success criteria:

- [ ] `npx vitest run --root dashboard --coverage` passes, with tests for each view, the money formatter and the hash routing, and statement coverage of 80% or more.
- [ ] `npm run check:ts` passes: Prettier, ESLint, `tsc` in strict mode with no `any`.
- [ ] With `npm run dev` running, the Playwright MCP shows at `http://localhost:5173`: the queue with 25 claims, a count of 25 Waiting, and each claim's id in JetBrains Mono and amount as dollars.
- [ ] Clicking CLM-1001 opens `#/claims/CLM-1001` with the story, the 3 items, the 4 documents, the Premium policy for Rome, and Maya Patel's earlier claim CLM-0412.
- [ ] `#/instructions` shows the instructions as text, with nothing to edit.
- [ ] A Playwright MCP screenshot in light mode and one in dark mode (`browser_emulate_media`) show the brand backgrounds (`#F0F4F5` and `#04232E`), rounded panels without outlines and the four state colors.
- [ ] The browser console shows no errors.

## Phase 5: Live progress, sign-off and end-to-end tests

Adds the parts that move: the steps while the agent works, the states updating, and the handler's sign-off.

- The Claim view polls the claim and its steps every two seconds while it's In progress, and the Queue refreshes every few seconds.
- The Claim view shows the decision, the payout, the reasons and the policy section once decided, and the payment or the sign-off.
- The sign-off panel: a handler picker from `list_handlers` and a Sign off button, shown only when the claim is waiting for sign-off.
- Playwright on its own ports and database, set in `playwright.config.ts` and through an environment variable for the Vite proxy's target.

Success criteria:

- [ ] vitest passes with tests for polling, the decision panel and the sign-off panel, at 80% coverage or more.
- [ ] `npm run e2e` passes, with tests that play the agent through the API and check the screens:
  - [ ] the queue shows 25 claims waiting
  - [ ] after starting a claim and posting steps, the claim shows In progress and the steps appear without a reload
  - [ ] after an approve of $420.00 and its payment, the claim shows Decided, Approve, $420.00, the reasons, the section and Paid
  - [ ] after an approve of $1,500.00 and a refused payment, the claim shows Waiting for sign-off and Not paid; choosing a handler and clicking Sign off shows Decided, signed off by that handler, and Paid $1,500.00
  - [ ] the e2e run leaves the dev database untouched
- [ ] The Playwright MCP shows the same sign-off flow on the dev servers, with no console errors.
- [ ] `npm run check` passes.

## Phase 6: The real agent, and the hand-over

Runs the real agent on real claims, then tidies up for you.

- A short `README.md` section on running the pilot, and `docs/STATUS.md` brought up to date.

Success criteria (the agent runs use your OpenRouter key on `openai/gpt-6-luna`, or set `MODEL_NAME=openrouter/free` for free; these are the only checks that call a model):

- [ ] With `npm run dev` running, `npm run agent -- CLM-1001` finishes, and the Playwright MCP shows CLM-1001 moving through In progress, with its steps appearing, to Decided with a decision, two or three sentences of reasons and a policy section.
- [ ] `npm run agent -- CLM-1003` (emergency medical, $3,800.00 claimed) finishes. If the agent approves more than $1,000.00, the claim shows Waiting for sign-off and `GET /api/claims/CLM-1003` shows no payment until a handler signs off in the dashboard.
- [ ] I report both decisions to you. I don't score them against `data/evals/`, which waits for the evaluations on Week 2 Day 4.
- [ ] `npm run reset` returns the queue to 25 waiting claims.
- [ ] `docs/STATUS.md` describes what's built and how to run it: `npm run dev`, `npm run agent`, `npm run reset`.
- [ ] `npm run check` passes, and I report its results.

## Out of scope for the pilot

From the spec: the claims manual, sign-in, real payments and messages to customers. Also scoring the agent against the handlers' decisions, which needs `data/evals/` and comes with the evaluations later in the course, and anything from the later briefs in `labs/`.
