'use strict';
const fs = require('node:fs');
const path = require('node:path');
const { parseEnv } = require('node:util');

function webOrigin() {
  if (process.env.CINEDRAFT_WEB_URL) return process.env.CINEDRAFT_WEB_URL;
  let config = {};
  try {
    config = parseEnv(fs.readFileSync(path.resolve(__dirname, '../.env'), 'utf8'));
  } catch (error) {
    if (error.code !== 'ENOENT') throw error;
  }
  const port = process.env.WEB_PORT || config.WEB_PORT || '5173';
  if (!/^\d+$/.test(port) || Number(port) < 1 || Number(port) > 65535) {
    throw new Error('Review WEB_PORT; use a port from 1 to 65535.');
  }
  return `http://127.0.0.1:${port}`;
}

async function main() {
  const origin = webOrigin();
  const live = await fetch(new URL('/api/health', origin), { signal: AbortSignal.timeout(8000) });
  const body = await live.json();
  if (!live.ok || body.status !== 'ok' || body.service !== 'cinedraft-api') {
    throw new Error('The frontend proxy did not return a valid CineDraft API health response.');
  }
  console.log('Frontend -> Vite proxy -> FastAPI: connected.');
  const ready = await fetch(new URL('/api/health/ready', origin), { signal: AbortSignal.timeout(8000) });
  const result = await ready.json();
  if (ready.ok && result.status === 'ready' && result.database === 'connected') {
    console.log('FastAPI -> PostgreSQL: SELECT 1 passed.');
    return;
  }
  if (ready.status === 503 && result.error?.code === 'database_unavailable') {
    if (process.argv.includes('--allow-db-down')) {
      console.log('PostgreSQL is unavailable; the expected structured 503 response was verified. This is NOT a successful database check.');
      return;
    }
    throw new Error('API is reachable, but PostgreSQL is not ready. Start/check the database.');
  }
  throw new Error('Unexpected database readiness response.');
}
main().catch(error => { console.error(error.message); process.exitCode = 1; });
