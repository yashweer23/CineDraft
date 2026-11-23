'use strict';
const fs = require('node:fs');
const path = require('node:path');
const { randomBytes } = require('node:crypto');
const { parseEnv } = require('node:util');
const root = path.resolve(__dirname, '..');

function writeMissing(relative, content) {
  const file = path.join(root, relative);
  try {
    fs.writeFileSync(file, content, { flag: 'wx', mode: 0o600 });
    console.log(`Created ${relative}`);
  } catch (error) {
    if (error.code !== 'EEXIST') throw error;
    console.log(`Kept existing ${relative}`);
  }
}

try {
  const password = randomBytes(24).toString('base64url');
  writeMissing('.env', `POSTGRES_USER=cinedraft\nPOSTGRES_PASSWORD=${password}\nPOSTGRES_DB=cinedraft\nPOSTGRES_PORT=5432\nAPI_PORT=8000\nWEB_PORT=5173\n`);
  const config = parseEnv(fs.readFileSync(path.join(root, '.env'), 'utf8'));
  for (const key of ['POSTGRES_USER', 'POSTGRES_PASSWORD', 'POSTGRES_DB']) {
    if (!config[key] || /[\r\n]/.test(config[key])) throw new Error(`Review ${key} in the root .env; it must be a non-empty single-line value.`);
  }
  function configuredPort(key, fallback) {
    const port = config[key] || fallback;
    if (!/^\d+$/.test(port) || Number(port) < 1 || Number(port) > 65535) throw new Error(`Review ${key} in the root .env; use a port from 1 to 65535.`);
    return port;
  }
  const databasePort = configuredPort('POSTGRES_PORT', '5432');
  const apiPort = configuredPort('API_PORT', '8000');
  const webPort = configuredPort('WEB_PORT', '5173');
  // dotenv interpolation syntax is ambiguous for imported hand-written passwords.
  if (Object.values(config).some(value => value.includes('${'))) throw new Error('Use values without dotenv interpolation syntax in the root .env.');
  writeMissing('backend/.env', [
    'ENVIRONMENT=development', 'DB_HOST=127.0.0.1', `DB_PORT=${databasePort}`,
    `DB_NAME=${JSON.stringify(config.POSTGRES_DB)}`, `DB_USER=${JSON.stringify(config.POSTGRES_USER)}`,
    `DB_PASSWORD=${JSON.stringify(config.POSTGRES_PASSWORD)}`,
    'TMDB_READ_ACCESS_TOKEN=',
    `CORS_ORIGINS=["http://localhost:${webPort}","http://127.0.0.1:${webPort}","http://localhost:4173","http://127.0.0.1:4173"]`, '',
  ].join('\n'));
  writeMissing('frontend/.env', `API_PROXY_TARGET=http://127.0.0.1:${apiPort}\nVITE_LEGACY_URL=http://127.0.0.1:5500\n`);
  console.log('Local configuration is ready. Existing values were not overwritten. Never commit .env files.');
} catch (error) {
  console.error(error.message);
  process.exitCode = 1;
}
