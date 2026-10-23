import { useState } from "react";
import { readJson, type Claim, type Handler, type Step } from "./api";
import { dateTime, label, money } from "./format";
import { useResource } from "./useResource";

export function DecisionPanel({ claim }: Readonly<{ claim: Claim }>) {
  const { decision, payment, sign_off: signOff } = claim;

  if (!decision) {
    return (
      <section className="panel">
        <h2>Decision</h2>
        <p className="muted">The agent has not decided this claim yet.</p>
      </section>
    );
  }

  return (
    <section className="panel" aria-label="Decision">
      <h2>Decision</h2>
      <div className="decision">
        <span className="decision-kind">{label(decision.decision)}</span>
        {decision.decision === "approve" && (
          <span className="decision-payout mono">{money(decision.payout)}</span>
        )}
      </div>
      <p>{decision.reasons}</p>
      <dl className="facts">
        <dt>Policy</dt>
        <dd>{decision.policy_section}</dd>
        <dt>Decided</dt>
        <dd>{dateTime(decision.decided_at)}</dd>
        {signOff && (
          <>
            <dt>Sign-off</dt>
            <dd>
              Signed off by {signOff.handler_name},{" "}
              {dateTime(signOff.signed_off_at)}
            </dd>
          </>
        )}
        {decision.decision === "approve" && (
          <>
            <dt>Payment</dt>
            <dd>
              {payment
                ? `Paid ${money(payment.amount)}, ${dateTime(payment.paid_at)}`
                : "Not paid"}
            </dd>
          </>
        )}
      </dl>
    </section>
  );
}

export function SignOffPanel({
  claim,
  onSignedOff,
}: Readonly<{ claim: Claim; onSignedOff: () => void }>) {
  const { data: handlers } = useResource<Handler[]>("/api/handlers", readJson);
  const [handlerId, setHandlerId] = useState("");
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState("");
  const chosen = handlerId || (handlers?.[0]?.handler_id ?? "");

  const signOff = async () => {
    setBusy(true);
    const response = await fetch(`/api/claims/${claim.claim_id}/sign-off`, {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ handler_id: chosen }),
    });
    setBusy(false);
    if (response.ok) {
      onSignedOff();
    } else {
      setError((await readJson<{ detail: string }>(response)).detail);
    }
  };

  return (
    <section className="panel signoff" aria-label="Sign-off">
      <h2>Waiting for sign-off</h2>
      <p>
        The payout is over $1,000.00, so a handler must sign off before it is
        paid.
      </p>
      <div className="signoff-form">
        <label>
          Handler{" "}
          <select
            value={chosen}
            onChange={(event) => {
              setHandlerId(event.target.value);
            }}
          >
            {handlers?.map((handler) => (
              <option key={handler.handler_id} value={handler.handler_id}>
                {handler.name}
              </option>
            ))}
          </select>
        </label>
        <button
          type="button"
          className="button"
          disabled={busy || !chosen}
          onClick={() => void signOff()}
        >
          Sign off {money(claim.decision?.payout ?? 0)}
        </button>
      </div>
      {error && <p role="alert">{error}</p>}
    </section>
  );
}

const KINDS: Record<Step["kind"], string> = {
  tool_call: "Tool call",
  tool_result: "Result",
  reply: "Reply",
};

export function StepsPanel({
  steps,
  working,
}: Readonly<{ steps: Step[]; working: boolean }>) {
  return (
    <section className="panel" aria-label="Agent activity">
      <h2>Agent activity</h2>
      {working && (
        <p className="working">The agent is working on this claim.</p>
      )}
      {steps.length === 0 && !working && (
        <p className="muted">The agent has not worked on this claim yet.</p>
      )}
      <ol className="list steps">
        {steps.map((step) => (
          <li key={step.step_id} className={`step step-${step.kind}`}>
            <span className="step-kind">{KINDS[step.kind]}</span>
            <span className={step.kind === "reply" ? "" : "mono"}>
              {step.text}
            </span>
          </li>
        ))}
      </ol>
    </section>
  );
}
