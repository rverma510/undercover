import { expect, test, type APIRequestContext } from "@playwright/test";

// The tests play the agent's part through the API, then check the screens.
test.describe.configure({ mode: "serial" });

async function start(request: APIRequestContext, claimId: string) {
  const response = await request.post(`/api/claims/${claimId}/start`, {
    data: { thread_id: `e2e-${claimId}` },
  });
  expect(response.ok()).toBe(true);
}

async function approve(
  request: APIRequestContext,
  claimId: string,
  payout: number,
) {
  const response = await request.post(`/api/claims/${claimId}/decision`, {
    data: {
      decision: "approve",
      payout,
      reasons:
        "The claim is covered by the policy. The costs are within the limit.",
      policy_section: "Section 3. Trip Delay",
    },
  });
  expect(response.ok()).toBe(true);
}

function pay(request: APIRequestContext, claimId: string, amount: number) {
  return request.post(`/api/claims/${claimId}/payment`, { data: { amount } });
}

test("the queue shows 25 claims waiting", async ({ page }) => {
  await page.goto("/");
  await expect(
    page.getByRole("heading", { name: "Claims queue" }),
  ).toBeVisible();
  await expect(page.locator("tbody tr")).toHaveCount(25);
  await expect(page.getByTestId("count-waiting")).toHaveText("25");
});

test("the agent's steps appear while it works", async ({ page, request }) => {
  await page.goto("/#/claims/CLM-1004");
  await expect(
    page.getByText("The agent has not worked on this claim yet."),
  ).toBeVisible();

  await start(request, "CLM-1004");
  await request.post("/api/claims/CLM-1004/steps", {
    data: {
      thread_id: "e2e-CLM-1004",
      kind: "tool_call",
      text: 'get_claim({"claim_id": "CLM-1004"})',
    },
  });

  await expect(page.locator(".badge")).toHaveText("In progress");
  await expect(
    page.getByText('get_claim({"claim_id": "CLM-1004"})'),
  ).toBeVisible();
  await expect(
    page.getByText("The agent is working on this claim."),
  ).toBeVisible();
});

test("an approval within the limit is paid", async ({ page, request }) => {
  await start(request, "CLM-1001");
  await approve(request, "CLM-1001", 420);
  expect((await pay(request, "CLM-1001", 420)).ok()).toBe(true);

  await page.goto("/#/claims/CLM-1001");
  const decision = page.getByRole("region", { name: "Decision" });
  await expect(page.locator(".badge")).toHaveText("Decided");
  await expect(decision.getByText("Approve", { exact: true })).toBeVisible();
  await expect(decision.getByText("$420.00", { exact: true })).toBeVisible();
  await expect(
    decision.getByText("The claim is covered by the policy.", { exact: false }),
  ).toBeVisible();
  await expect(decision.getByText("Section 3. Trip Delay")).toBeVisible();
  await expect(decision.getByText(/^Paid \$420\.00/)).toBeVisible();
});

test("a payout over $1,000 waits for a handler's sign-off", async ({
  page,
  request,
}) => {
  await start(request, "CLM-1003");
  await approve(request, "CLM-1003", 1500);
  const refused = await pay(request, "CLM-1003", 1500);
  expect(refused.status()).toBe(409);

  await page.goto("/#/claims/CLM-1003");
  await expect(page.locator(".badge")).toHaveText("Waiting for sign-off");
  await expect(page.getByText("Not paid")).toBeVisible();

  await page.getByLabel("Handler").selectOption({ label: "Marcus Oyelaran" });
  await page.getByRole("button", { name: "Sign off $1,500.00" }).click();

  await expect(page.locator(".badge")).toHaveText("Decided");
  await expect(page.getByText(/^Signed off by Marcus Oyelaran/)).toBeVisible();
  await expect(page.getByText(/^Paid \$1,500\.00/)).toBeVisible();
  await expect(page.getByRole("button", { name: /Sign off/ })).toHaveCount(0);
});

test("the queue counts the claims in each state", async ({ page }) => {
  await page.goto("/");
  await expect(page.getByTestId("count-waiting")).toHaveText("22");
  await expect(page.getByTestId("count-in_progress")).toHaveText("1");
  await expect(page.getByTestId("count-decided")).toHaveText("2");
});
