import { readJson, type Claim, type Customer, type Policy } from "./api";
import { date, label, money } from "./format";
import { StateBadge } from "./StateBadge";
import { useResource } from "./useResource";

function Story({ claim }: Readonly<{ claim: Claim }>) {
  return (
    <section className="panel">
      <h2>The customer's story</h2>
      <p>{claim.story}</p>
      <dl className="facts">
        <dt>Incident</dt>
        <dd>
          {date(claim.incident_date)}, {claim.incident_location}
        </dd>
        <dt>Submitted</dt>
        <dd>{date(claim.submitted_on)}</dd>
      </dl>
    </section>
  );
}

function Items({ claim }: Readonly<{ claim: Claim }>) {
  return (
    <section className="panel table-wrap">
      <h2>Items claimed</h2>
      <table>
        <thead>
          <tr>
            <th>Item</th>
            <th>Category</th>
            <th className="amount">Amount</th>
          </tr>
        </thead>
        <tbody>
          {claim.items.map((item) => (
            <tr key={item.description}>
              <td>{item.description}</td>
              <td>{label(item.category)}</td>
              <td className="amount">{money(item.amount)}</td>
            </tr>
          ))}
        </tbody>
        <tfoot>
          <tr>
            <th colSpan={2}>Total claimed</th>
            <td className="amount">{money(claim.amount_claimed)}</td>
          </tr>
        </tfoot>
      </table>
    </section>
  );
}

function Documents({ claim }: Readonly<{ claim: Claim }>) {
  return (
    <section className="panel">
      <h2>Documents</h2>
      {claim.documents.map((document) => (
        <article className="document" key={document.name}>
          <h3>{document.name}</h3>
          <span className="muted">{label(document.type)}</span>
          <p>{document.content}</p>
        </article>
      ))}
    </section>
  );
}

function PolicyPanel({ policy }: Readonly<{ policy: Policy }>) {
  return (
    <section className="panel">
      <h2>Policy</h2>
      <dl className="facts">
        <dt>Policy</dt>
        <dd className="mono">{policy.policy_id}</dd>
        <dt>Plan</dt>
        <dd>{label(policy.plan)}</dd>
        <dt>Add-ons</dt>
        <dd>
          {policy.add_ons.length
            ? policy.add_ons.map(label).join(", ")
            : "None"}
        </dd>
        <dt>Bought</dt>
        <dd>{date(policy.purchased_on)}</dd>
        <dt>Trip</dt>
        <dd>
          {policy.trip.destination}, {date(policy.trip.departs_on)} to{" "}
          {date(policy.trip.returns_on)}
        </dd>
        <dt>Trip cost</dt>
        <dd className="mono">{money(policy.trip.trip_cost)}</dd>
        <dt>Travelers</dt>
        <dd>{policy.travelers.join(", ")}</dd>
      </dl>
    </section>
  );
}

function CustomerPanel({ customer }: Readonly<{ customer: Customer }>) {
  return (
    <section className="panel">
      <h2>Customer</h2>
      <dl className="facts">
        <dt>Name</dt>
        <dd>{customer.name}</dd>
        <dt>Customer since</dt>
        <dd>{date(customer.customer_since)}</dd>
      </dl>
      <h3 className="subheading">Earlier claims</h3>
      {customer.previous_claims.length === 0 && <p>No earlier claims</p>}
      <ul className="list">
        {customer.previous_claims.map((previous) => (
          <li key={previous.claim_id}>
            <span className="mono">{previous.claim_id}</span>,{" "}
            {date(previous.filed_on)}: {previous.summary}.{" "}
            {label(previous.outcome)}, paid{" "}
            <span className="mono">{money(previous.amount_paid)}</span>.
          </li>
        ))}
      </ul>
    </section>
  );
}

export function ClaimView({ claimId }: Readonly<{ claimId: string }>) {
  const { data: claim, error } = useResource<Claim>(
    `/api/claims/${claimId}`,
    readJson,
  );
  const { data: policy } = useResource<Policy>(
    claim ? `/api/policies/${claim.policy_id}` : null,
    readJson,
  );
  const { data: customer } = useResource<Customer>(
    claim ? `/api/customers/${claim.customer_id}` : null,
    readJson,
  );

  if (error) return <p role="alert">Claim {claimId} could not be loaded.</p>;
  if (!claim) return <p className="muted">Loading {claimId}</p>;

  return (
    <>
      <a href="#/">Back to the queue</a>
      <section className="claim-header">
        <div className="claim-title">
          <h1>
            <span className="mono">{claim.claim_id}</span>
          </h1>
          <StateBadge status={claim.status} />
        </div>
        <p className="muted">
          {label(claim.claim_type)}, {money(claim.amount_claimed)} claimed by{" "}
          {customer?.name ?? claim.customer_id}. {claim.summary}.
        </p>
      </section>
      <div className="columns">
        <div className="stack">
          <Story claim={claim} />
          <Items claim={claim} />
          <Documents claim={claim} />
        </div>
        <div className="stack">
          {policy && <PolicyPanel policy={policy} />}
          {customer && <CustomerPanel customer={customer} />}
        </div>
      </div>
    </>
  );
}
