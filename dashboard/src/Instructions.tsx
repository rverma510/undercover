import { readText } from "./api";
import { useResource } from "./useResource";

export function Instructions() {
  const { data, error } = useResource("/api/instructions", readText);

  return (
    <>
      <h1>Agent instructions</h1>
      <p className="muted">
        What the UnderCover Agent is told before it works a claim, followed by
        the policy wording. Read only.
      </p>
      <section className="panel">
        {error && <p role="alert">The instructions could not be loaded.</p>}
        {data && (
          <pre className="text" data-testid="instructions">
            {data}
          </pre>
        )}
      </section>
    </>
  );
}
