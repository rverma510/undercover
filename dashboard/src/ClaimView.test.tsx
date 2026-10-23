import { cleanup, fireEvent, render, screen } from "@testing-library/react";
import { afterEach, expect, it, vi } from "vitest";
import { ClaimView } from "./ClaimView";
import { claim, claimRoutes, stubApi } from "./test/fixtures";

afterEach(() => {
  cleanup();
  vi.unstubAllGlobals();
});

it("shows the claim in full with its policy and customer", async () => {
  stubApi(claimRoutes());
  render(<ClaimView claimId="CLM-1001" />);
  expect(
    await screen.findByText("My flight home from Rome was canceled."),
  ).toBeDefined();
  expect(screen.getByText("Airport hotel, one night")).toBeDefined();
  expect(screen.getByText("$245.00")).toBeDefined();
  expect(screen.getByText("$420.00")).toBeDefined();
  expect(screen.getByText("Hotel receipt")).toBeDefined();
  expect(await screen.findByText("Premium")).toBeDefined();
  expect(
    screen.getByText("Rome, Italy, Jun 10, 2026 to Jun 18, 2026"),
  ).toBeDefined();
  expect(await screen.findByText("CLM-0412")).toBeDefined();
  expect(screen.getByText("Waiting")).toBeDefined();
});

it("says when a customer has no earlier claims", async () => {
  stubApi({
    ...claimRoutes(),
    "/api/customers/CUS-3001": {
      customer_id: "CUS-3001",
      name: "Maya Patel",
      customer_since: "2023-04-11",
      previous_claims: [],
    },
  });
  render(<ClaimView claimId="CLM-1001" />);
  expect(await screen.findByText("No earlier claims")).toBeDefined();
});

it("says when the claim cannot be loaded", async () => {
  stubApi({});
  render(<ClaimView claimId="CLM-9999" />);
  expect((await screen.findByRole("alert")).textContent).toBe(
    "Claim CLM-9999 could not be loaded.",
  );
});

it("shows the agent's steps while it works", async () => {
  stubApi(claimRoutes({ status: "in_progress" }));
  render(<ClaimView claimId="CLM-1001" />);
  expect(
    await screen.findByText("The agent is working on this claim."),
  ).toBeDefined();
  expect(
    await screen.findByText('get_claim({"claim_id": "CLM-1001"})'),
  ).toBeDefined();
});

it("signs off a claim and shows it paid", async () => {
  const decision = {
    decision: "approve" as const,
    payout: 1500,
    reasons: "The treatment was covered.",
    policy_section: "Section 7. Emergency Medical",
    decided_at: "2026-10-23T10:00:00+00:00",
  };
  const routes = claimRoutes({ status: "awaiting_signoff", decision });
  routes["POST /api/claims/CLM-1001/sign-off"] = () => {
    routes["/api/claims/CLM-1001"] = {
      ...claim,
      status: "decided",
      decision,
      sign_off: {
        handler_id: "HND-01",
        handler_name: "Dana Whitfield",
        signed_off_at: "2026-10-23T11:00:00+00:00",
      },
      payment: { amount: 1500, paid_at: "2026-10-23T11:00:00+00:00" },
    };
    return {};
  };
  stubApi(routes);
  render(<ClaimView claimId="CLM-1001" />);
  expect(await screen.findByText("Not paid")).toBeDefined();
  await screen.findByRole("option", { name: "Dana Whitfield" });
  fireEvent.click(screen.getByRole("button", { name: "Sign off $1,500.00" }));
  expect(await screen.findByText(/^Paid \$1,500\.00/)).toBeDefined();
  expect(screen.getByText("Decided", { selector: ".badge" })).toBeDefined();
  expect(screen.queryByRole("button", { name: /Sign off/ })).toBeNull();
});
