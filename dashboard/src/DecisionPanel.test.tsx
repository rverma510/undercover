import { cleanup, fireEvent, render, screen } from "@testing-library/react";
import { afterEach, expect, it, vi } from "vitest";
import type { Claim, Decision } from "./api";
import { DecisionPanel, SignOffPanel, StepsPanel } from "./DecisionPanel";
import { claim, handlers, steps, stubApi } from "./test/fixtures";

afterEach(() => {
  cleanup();
  vi.unstubAllGlobals();
});

const approve: Decision = {
  decision: "approve",
  payout: 1500,
  reasons: "The treatment was covered.",
  policy_section: "Section 7. Emergency Medical",
  decided_at: "2026-10-23T10:00:00+00:00",
};

function decided(overrides: Partial<Claim>): Claim {
  return { ...claim, status: "decided", decision: approve, ...overrides };
}

it("says when there is no decision yet", () => {
  render(<DecisionPanel claim={claim} />);
  expect(
    screen.getByText("The agent has not decided this claim yet."),
  ).toBeDefined();
});

it("shows an approval with its payout, reasons, section and payment", () => {
  render(
    <DecisionPanel
      claim={decided({
        payment: { amount: 1500, paid_at: "2026-10-23T11:00:00+00:00" },
        sign_off: {
          handler_id: "HND-01",
          handler_name: "Dana Whitfield",
          signed_off_at: "2026-10-23T11:00:00+00:00",
        },
      })}
    />,
  );
  expect(screen.getByText("Approve")).toBeDefined();
  expect(screen.getByText("$1,500.00")).toBeDefined();
  expect(screen.getByText("The treatment was covered.")).toBeDefined();
  expect(screen.getByText("Section 7. Emergency Medical")).toBeDefined();
  expect(screen.getByText(/^Signed off by Dana Whitfield/)).toBeDefined();
  expect(screen.getByText(/^Paid \$1,500\.00/)).toBeDefined();
});

it("shows an approval that is not paid yet", () => {
  render(<DecisionPanel claim={decided({ status: "awaiting_signoff" })} />);
  expect(screen.getByText("Not paid")).toBeDefined();
});

it("shows a decline without a payout or payment", () => {
  render(
    <DecisionPanel
      claim={decided({
        decision: { ...approve, decision: "decline", payout: 0 },
      })}
    />,
  );
  expect(screen.getByText("Decline")).toBeDefined();
  expect(screen.queryByText("$0.00")).toBeNull();
  expect(screen.queryByText("Not paid")).toBeNull();
});

it("signs off as the chosen handler", async () => {
  const signedOff = vi.fn();
  const fetchMock = stubApi({
    "/api/handlers": handlers,
    "POST /api/claims/CLM-1001/sign-off": {},
  });
  render(
    <SignOffPanel
      claim={decided({ status: "awaiting_signoff" })}
      onSignedOff={signedOff}
    />,
  );
  await screen.findByRole("option", { name: "Marcus Oyelaran" });
  fireEvent.change(screen.getByRole("combobox"), {
    target: { value: "HND-02" },
  });
  fireEvent.click(screen.getByRole("button", { name: "Sign off $1,500.00" }));
  await vi.waitFor(() => {
    expect(signedOff).toHaveBeenCalled();
  });
  expect(fetchMock).toHaveBeenCalledWith(
    "/api/claims/CLM-1001/sign-off",
    expect.objectContaining({
      method: "POST",
      body: '{"handler_id":"HND-02"}',
    }),
  );
});

it("shows why a sign-off was refused", async () => {
  stubApi({
    "/api/handlers": handlers,
    "POST /api/claims/CLM-1001/sign-off": () =>
      Response.json(
        { detail: "CLM-1001 is not waiting for sign-off" },
        { status: 409 },
      ),
  });
  render(
    <SignOffPanel
      claim={decided({ status: "awaiting_signoff" })}
      onSignedOff={vi.fn()}
    />,
  );
  await screen.findByRole("option", { name: "Dana Whitfield" });
  fireEvent.click(screen.getByRole("button", { name: "Sign off $1,500.00" }));
  expect((await screen.findByRole("alert")).textContent).toBe(
    "CLM-1001 is not waiting for sign-off",
  );
});

it("shows the agent's steps", () => {
  render(<StepsPanel steps={steps} working={true} />);
  expect(screen.getByText("The agent is working on this claim.")).toBeDefined();
  expect(screen.getByText("Tool call")).toBeDefined();
  expect(screen.getByText('get_claim({"claim_id": "CLM-1001"})')).toBeDefined();
});

it("says when the agent has not worked on a claim", () => {
  render(<StepsPanel steps={[]} working={false} />);
  expect(
    screen.getByText("The agent has not worked on this claim yet."),
  ).toBeDefined();
});
