import { cleanup, fireEvent, render, screen } from "@testing-library/react";
import { afterEach, expect, it, vi } from "vitest";
import { readText } from "./api";
import { stubApi } from "./test/fixtures";
import { useResource } from "./useResource";

afterEach(() => {
  cleanup();
  vi.unstubAllGlobals();
});

function Probe({ refreshMs }: Readonly<{ refreshMs: number }>) {
  const { data, reload } = useResource("/api/value", readText, refreshMs);
  return (
    <>
      <p>{data ?? "loading"}</p>
      <button type="button" onClick={reload}>
        Reload
      </button>
    </>
  );
}

it("refetches on an interval", async () => {
  let count = 0;
  stubApi({ "/api/value": () => `value ${String(++count)}` });
  render(<Probe refreshMs={20} />);
  expect(await screen.findByText("value 1")).toBeDefined();
  expect(await screen.findByText("value 3")).toBeDefined();
});

it("fetches once without a refresh, and again on reload", async () => {
  let count = 0;
  const fetchMock = stubApi({ "/api/value": () => `value ${String(++count)}` });
  render(<Probe refreshMs={0} />);
  expect(await screen.findByText("value 1")).toBeDefined();
  await new Promise((resolve) => setTimeout(resolve, 50));
  expect(fetchMock).toHaveBeenCalledTimes(1);
  fireEvent.click(screen.getByRole("button", { name: "Reload" }));
  expect(await screen.findByText("value 2")).toBeDefined();
});
