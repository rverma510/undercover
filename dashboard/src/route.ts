export type Route =
  | { view: "queue" }
  | { view: "claim"; claimId: string }
  | { view: "instructions" };

export function parseRoute(hash: string): Route {
  const claim = /^#\/claims\/([\w-]+)$/.exec(hash);
  if (claim?.[1]) return { view: "claim", claimId: claim[1] };
  if (hash === "#/instructions") return { view: "instructions" };
  return { view: "queue" };
}
