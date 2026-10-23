import { expect, it } from "vitest";
import { date, label, money } from "./format";
import { parseRoute } from "./route";

it("formats money as US dollars", () => {
  expect(money(1250)).toBe("$1,250.00");
  expect(money(0)).toBe("$0.00");
});

it("turns codes into labels", () => {
  expect(label("trip_delay")).toBe("Trip delay");
  expect(label("premium")).toBe("Premium");
});

it("formats dates", () => {
  expect(date("2026-06-24")).toBe("Jun 24, 2026");
});

it("parses routes from the hash", () => {
  expect(parseRoute("")).toEqual({ view: "queue" });
  expect(parseRoute("#/")).toEqual({ view: "queue" });
  expect(parseRoute("#/claims/CLM-1001")).toEqual({
    view: "claim",
    claimId: "CLM-1001",
  });
  expect(parseRoute("#/instructions")).toEqual({ view: "instructions" });
  expect(parseRoute("#/nowhere")).toEqual({ view: "queue" });
});
