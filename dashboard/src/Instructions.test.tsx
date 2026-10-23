import { cleanup, render, screen } from "@testing-library/react";
import { afterEach, expect, it, vi } from "vitest";
import { Instructions } from "./Instructions";
import { stubApi } from "./test/fixtures";

afterEach(() => {
  cleanup();
  vi.unstubAllGlobals();
});

it("shows the instructions as read-only text", async () => {
  stubApi({
    "/api/instructions": "# The UnderCover Agent\n\nYou decide claims.",
  });
  render(<Instructions />);
  const text = await screen.findByTestId("instructions");
  expect(text.textContent).toBe("# The UnderCover Agent\n\nYou decide claims.");
  expect(screen.queryByRole("textbox")).toBeNull();
  expect(screen.queryByRole("button")).toBeNull();
});

it("says when the instructions cannot be loaded", async () => {
  stubApi({});
  render(<Instructions />);
  expect(await screen.findByRole("alert")).toBeDefined();
});
