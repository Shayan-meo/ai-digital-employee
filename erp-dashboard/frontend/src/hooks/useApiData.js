import { useState, useEffect } from 'react';

export function useApiData(fetchFn, deps = []) {
  const [data, setData] = useState(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState(null);

  useEffect(() => {
    let cancelled = false;
    setLoading(true);
    fetchFn()
      .then(result => {
        if (!cancelled) {
          setData(result);
          setError(null);
        }
      })
      .catch(err => {
        if (!cancelled) setError(err.message);
      })
      .finally(() => {
        if (!cancelled) setLoading(false);
      });
    return () => { cancelled = true; };
  }, deps);

  return { data, loading, error, refetch: () => {
    setLoading(true);
    fetchFn().then(setData).catch(e => setError(e.message)).finally(() => setLoading(false));
  }};
}
