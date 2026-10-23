import { cleanup, render, screen } from "@testing-library/react";
import { afterEach, expect, it, vi } from "vitest";
import { ClaimView } from "./ClaimView";
import { claimRoutes, stubApi } from "./test/fixtures";

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
