import { vi } from "vitest";
import type {
  Claim,
  ClaimSummary,
  Customer,
  Handler,
  Policy,
  Step,
} from "../api";

export const summary: ClaimSummary = {
  claim_id: "CLM-1001",
  customer_name: "Maya Patel",
  claim_type: "trip_delay",
  summary: "Flight home canceled by the airline",
  amount_claimed: 420,
  submitted_on: "2026-06-24",
  status: "waiting",
};

export const claim: Claim = {
  claim_id: "CLM-1001",
  policy_id: "POL-2001",
  customer_id: "CUS-3001",
  claim_type: "trip_delay",
  submitted_on: "2026-06-24",
  incident_date: "2026-06-18",
  incident_location: "Rome, Italy",
  summary: "Flight home canceled by the airline",
  story: "My flight home from Rome was canceled.",
  items: [
    {
      description: "Airport hotel, one night",
      category: "accommodation",
      amount: 245,
    },
    { description: "Dinner and breakfast", category: "meals", amount: 95 },
    { description: "Taxis", category: "transport", amount: 80 },
  ],
  amount_claimed: 420,
  documents: [
    { name: "Hotel receipt", type: "receipt", content: "One night: $245.00." },
  ],
  status: "waiting",
  decision: null,
  sign_off: null,
  payment: null,
};

export const policy: Policy = {
  policy_id: "POL-2001",
  plan: "premium",
  add_ons: [],
  purchased_on: "2026-04-22",
  sold_through: "Meridian Air checkout",
  trip: {
    destination: "Rome, Italy",
    departs_on: "2026-06-10",
    returns_on: "2026-06-18",
    trip_cost: 3100,
  },
  travelers: ["Maya Patel"],
};

export const customer: Customer = {
  customer_id: "CUS-3001",
  name: "Maya Patel",
  customer_since: "2023-04-11",
  previous_claims: [
    {
      claim_id: "CLM-0412",
      filed_on: "2024-08-19",
      claim_type: "baggage_delay",
      summary: "Checked bag arrived 30 hours late in Lisbon",
      outcome: "approved",
      amount_paid: 140,
    },
  ],
};

export const handlers: Handler[] = [
  {
    handler_id: "HND-01",
    name: "Dana Whitfield",
    role: "Senior Claims Handler",
  },
  { handler_id: "HND-02", name: "Marcus Oyelaran", role: "Claims Handler" },
];

export const steps: Step[] = [
  {
    step_id: 1,
    kind: "tool_call",
    text: 'get_claim({"claim_id": "CLM-1001"})',
    created_at: "2026-10-23T10:00:00+00:00",
  },
];

export function claimRoutes(
  overrides: Partial<Claim> = {},
): Record<string, unknown> {
  return {
    "/api/claims/CLM-1001": { ...claim, ...overrides },
    "/api/policies/POL-2001": policy,
    "/api/customers/CUS-3001": customer,
    "/api/claims/CLM-1001/steps": steps,
    "/api/handlers": handlers,
  };
}

type Answer = (init?: RequestInit) => unknown;

/**
 * Stub fetch: GETs answer from routes by path, and others by "METHOD path".
 * A route can be a function of the request, which runs on each call and can
 * return a Response.
 */
export function stubApi(routes: Record<string, unknown>) {
  const fetchMock = vi.fn((path: string, init?: RequestInit) => {
    const key = init?.method ? `${init.method} ${path}` : path;
    const route = routes[key];
    const body = typeof route === "function" ? (route as Answer)(init) : route;
    if (body === undefined) {
      return Promise.resolve(new Response("Not found", { status: 404 }));
    }
    if (body instanceof Response) return Promise.resolve(body);
    return Promise.resolve(
      typeof body === "string" ? new Response(body) : Response.json(body),
    );
  });
  vi.stubGlobal("fetch", fetchMock);
  return fetchMock;
}
