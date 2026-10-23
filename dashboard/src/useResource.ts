import { useEffect, useState } from "react";

interface Loaded<T> {
  path: string;
  data?: T;
  error?: string;
}

/** Fetch a path, refetching every refreshMs while refreshMs is above 0. */
export function useResource<T>(
  path: string | null,
  read: (response: Response) => Promise<T>,
  refreshMs = 0,
): { data: T | undefined; error: string | undefined } {
  const [loaded, setLoaded] = useState<Loaded<T> | null>(null);

  useEffect(() => {
    if (path === null) return;
    let live = true;
    const load = () =>
      fetch(path)
        .then((response) => {
          if (!response.ok)
            throw new Error(`${path} returned ${String(response.status)}`);
          return read(response);
        })
        .then(
          (data) => {
            if (live) setLoaded({ path, data });
          },
          (error: unknown) => {
            if (live) setLoaded({ path, error: String(error) });
          },
        );
    void load();
    const timer = refreshMs > 0 ? setInterval(() => void load(), refreshMs) : 0;
    return () => {
      live = false;
      clearInterval(timer);
    };
  }, [path, read, refreshMs]);

  const current = loaded !== null && loaded.path === path ? loaded : null;
  return { data: current?.data, error: current?.error };
}
