import type { Status } from "./api";
import { STATES } from "./format";

export function StateBadge({ status }: Readonly<{ status: Status }>) {
  return <span className={`badge state-${status}`}>{STATES[status]}</span>;
}
