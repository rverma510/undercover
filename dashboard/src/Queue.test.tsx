import { cleanup, render, screen, within } from "@testing-library/react";
import { afterEach, expect, it, vi } from "vitest";
import { Queue } from "./Queue";
import { stubApi, summary } from "./test/fixtures";

afterEach(() => {
  cleanup();
  vi.unstubAllGlobals();
});

it("shows the claims and a count in each state", async () => {
  stubApi({
    "/api/claims": [
      summary,
      {
        ...summary,
        claim_id: "CLM-1002",
        status: "awaiting_signoff",
        amount_claimed: 1150,
      },
    ],
  });
  render(<Queue />);
  const link = await screen.findByRole("link", { name: "CLM-1001" });
  expect(link.getAttribute("href")).toBe("#/claims/CLM-1001");
  expect(screen.getByTestId("count-waiting").textContent).toBe("1");
  expect(screen.getByTestId("count-awaiting_signoff").textContent).toBe("1");
  expect(screen.getByTestId("count-decided").textContent).toBe("0");
  const row = screen.getByRole("link", { name: "CLM-1002" }).closest("tr");
  expect(row).not.toBeNull();
  const cells = within(row as HTMLElement);
  expect(cells.getByText("$1,150.00")).toBeDefined();
  expect(cells.getByText("Waiting for sign-off")).toBeDefined();
  expect(cells.getByText("Trip delay")).toBeDefined();
});

it("says when the queue cannot be loaded", async () => {
  stubApi({});
  render(<Queue />);
  expect(await screen.findByRole("alert")).toBeDefined();
});
