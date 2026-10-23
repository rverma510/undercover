import { readJson, type ClaimSummary, type Status } from "./api";
import { date, label, money, STATES } from "./format";
import { StateBadge } from "./StateBadge";
import { useResource } from "./useResource";

const ORDER: Status[] = [
  "waiting",
  "in_progress",
  "awaiting_signoff",
  "decided",
];

export function Queue() {
  const { data: claims, error } = useResource<ClaimSummary[]>(
    "/api/claims",
    readJson,
  );

  if (error) return <p role="alert">The queue could not be loaded.</p>;
  if (!claims) return <p className="muted">Loading the queue</p>;

  return (
    <>
      <h1>Claims queue</h1>
      <section className="tiles" aria-label="Claims by state">
        {ORDER.map((status) => (
          <div className="panel tile" key={status}>
            <span className="tile-count" data-testid={`count-${status}`}>
              {claims.filter((claim) => claim.status === status).length}
            </span>
            <span className="tile-label">
              <span className={`dot state-${status}`} />
              {STATES[status]}
            </span>
          </div>
        ))}
      </section>
      <section className="panel table-wrap">
        <table>
          <thead>
            <tr>
              <th>Claim</th>
              <th>Customer</th>
              <th>Type</th>
              <th>Summary</th>
              <th className="amount">Claimed</th>
              <th>Submitted</th>
              <th>State</th>
            </tr>
          </thead>
          <tbody>
            {claims.map((claim) => (
              <tr key={claim.claim_id}>
                <td>
                  <a
                    className="mono nowrap"
                    href={`#/claims/${claim.claim_id}`}
                  >
                    {claim.claim_id}
                  </a>
                </td>
                <td>{claim.customer_name}</td>
                <td>{label(claim.claim_type)}</td>
                <td>{claim.summary}</td>
                <td className="amount">{money(claim.amount_claimed)}</td>
                <td className="nowrap">{date(claim.submitted_on)}</td>
                <td>
                  <StateBadge status={claim.status} />
                </td>
              </tr>
            ))}
          </tbody>
        </table>
      </section>
    </>
  );
}
