'use strict';
const test = require('node:test');
const assert = require('node:assert/strict');
const { spawn } = require('node:child_process');
const path = require('node:path');

test('local server serves the playable files and keeps project internals private', async t => {
  const child = spawn(process.execPath, [path.join(__dirname, '../scripts/serve.cjs'), '0'], {
    stdio: ['ignore', 'pipe', 'pipe']
  });
  t.after(() => child.kill());
  const origin = await new Promise((resolve, reject) => {
    let output = '';
    const timer = setTimeout(() => reject(new Error('Server did not start')), 5000);
    child.on('error', error => { clearTimeout(timer); reject(error); });
    child.on('exit', code => { clearTimeout(timer); reject(new Error(`Server exited: ${code}`)); });
    child.stdout.on('data', bytes => {
      output += bytes;
      const found = output.match(/http:\/\/127\.0\.0\.1:\d+/);
      if (found) { clearTimeout(timer); resolve(found[0]); }
    });
  });
  for (const route of ['/', '/index.html', '/app.js', '/engine.js', '/styles.css']) {
    const response = await fetch(origin + route);
    assert.equal(response.status, 200);
    assert.ok((await response.text()).length > 100);
  }
  assert.equal((await fetch(origin + '/README.md')).status, 404);
  assert.equal((await fetch(origin + '/.env')).status, 404);
  assert.equal((await fetch(origin + '/', { method: 'POST' })).status, 405);
  const head = await fetch(origin + '/engine.js', { method: 'HEAD' });
  assert.equal(head.status, 200);
  assert.equal(await head.text(), '');
});
