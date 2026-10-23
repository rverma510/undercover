import { useEffect, useState } from "react";
import { ClaimView } from "./ClaimView";
import { Instructions } from "./Instructions";
import { Queue } from "./Queue";
import { parseRoute } from "./route";

export function App() {
  const [hash, setHash] = useState(window.location.hash);

  useEffect(() => {
    const onChange = () => {
      setHash(window.location.hash);
    };
    window.addEventListener("hashchange", onChange);
    return () => {
      window.removeEventListener("hashchange", onChange);
    };
  }, []);

  const route = parseRoute(hash);

  return (
    <>
      <header className="header">
        <a className="brand" href="#/">
          UnderCover
        </a>
        <span className="tagline">Claims desk</span>
        <nav className="nav" aria-label="Main">
          <a
            href="#/"
            aria-current={route.view === "instructions" ? undefined : "page"}
          >
            Queue
          </a>
          <a
            href="#/instructions"
            aria-current={route.view === "instructions" ? "page" : undefined}
          >
            Agent instructions
          </a>
        </nav>
      </header>
      <main className="page">
        {route.view === "queue" && <Queue />}
        {route.view === "claim" && <ClaimView claimId={route.claimId} />}
        {route.view === "instructions" && <Instructions />}
      </main>
    </>
  );
}
