export type Connection = { status: 'up' | 'down'; message: string };
export type StudioHealth = { api: Connection; database: Connection };

function record(value: unknown): value is Record<string, unknown> {
  return typeof value === 'object' && value !== null;
}

export async function fetchStudioHealth(signal?: AbortSignal): Promise<StudioHealth> {
  const timeout = AbortSignal.timeout(8000);
  const combined = signal ? AbortSignal.any([signal, timeout]) : timeout;
  const [live, ready] = await Promise.allSettled([
    fetch('/api/health', { signal: combined }).then(async response => ({ response, body: await response.json() as unknown })),
    fetch('/api/health/ready', { signal: combined }).then(async response => ({ response, body: await response.json() as unknown })),
  ]);
  if (signal?.aborted) throw new DOMException('Cancelled', 'AbortError');
  const apiUp = live.status === 'fulfilled' && live.value.response.ok
    && record(live.value.body) && live.value.body.status === 'ok'
    && live.value.body.service === 'cinedraft-api';
  const dbUp = ready.status === 'fulfilled' && ready.value.response.ok
    && record(ready.value.body) && ready.value.body.status === 'ready'
    && ready.value.body.database === 'connected';
  return {
    api: apiUp
      ? { status: 'up', message: 'FastAPI is responding.' }
      : { status: 'down', message: 'Start the backend, then check the API proxy address.' },
    database: dbUp
      ? { status: 'up', message: 'PostgreSQL connection verified with SELECT 1.' }
      : { status: 'down', message: apiUp
        ? 'Check that PostgreSQL is running and the backend credentials match.'
        : 'Database readiness cannot be confirmed.' },
  };
}
