import { act, cleanup, render, screen } from "@testing-library/react";
import { afterEach, expect, it, vi } from "vitest";
import { App } from "./App";
import { claimRoutes, stubApi, summary } from "./test/fixtures";

afterEach(() => {
  cleanup();
  vi.unstubAllGlobals();
  window.location.hash = "";
});

function go(hash: string) {
  act(() => {
    window.location.hash = hash;
    window.dispatchEvent(new HashChangeEvent("hashchange"));
  });
}

it("shows the queue, a claim and the instructions by the hash", async () => {
  stubApi({
    "/api/claims": [summary],
    "/api/instructions": "# The UnderCover Agent",
    ...claimRoutes(),
  });
  render(<App />);
  expect(
    await screen.findByRole("heading", { name: "Claims queue" }),
  ).toBeDefined();

  go("#/claims/CLM-1001");
  expect(
    await screen.findByRole("heading", { name: "CLM-1001" }),
  ).toBeDefined();

  go("#/instructions");
  expect(await screen.findByText("# The UnderCover Agent")).toBeDefined();
  expect(
    screen
      .getByRole("link", { name: "Agent instructions" })
      .getAttribute("aria-current"),
  ).toBe("page");
});
