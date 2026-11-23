#!/usr/bin/env node
'use strict';
const http = require('node:http');
const fs = require('node:fs/promises');
const path = require('node:path');
const root = path.resolve(__dirname, '..');
const args = process.argv.slice(2);
if (args.length > 1 || (args.length && !/^\d+$/.test(args[0]))) {
  console.error('Usage: npm start -- [port]');
  process.exit(1);
}
const port = Number(args[0] ?? 5500);
if (!Number.isInteger(port) || port < 0 || port > 65535) {
  console.error('Choose a port between 0 and 65535.');
  process.exit(1);
}
const routes = new Map([
  ['/', ['index.html', 'text/html']],
  ['/index.html', ['index.html', 'text/html']],
  ['/app.js', ['app.js', 'text/javascript']],
  ['/engine.js', ['engine.js', 'text/javascript']],
  ['/styles.css', ['styles.css', 'text/css']]
]);
const server = http.createServer(async (req, res) => {
  if (!['GET', 'HEAD'].includes(req.method)) {
    res.writeHead(405, { Allow: 'GET, HEAD' });
    res.end('Method not allowed');
    return;
  }
  const route = routes.get((req.url || '').split('?')[0]);
  if (!route) {
    res.writeHead(404, { 'Content-Type': 'text/plain; charset=utf-8' });
    res.end('Not found');
    return;
  }
  try {
    const bytes = await fs.readFile(path.join(root, route[0]));
    res.writeHead(200, {
      'Content-Type': route[1] + '; charset=utf-8',
      'Content-Length': bytes.length,
      'Cache-Control': 'no-store',
      'X-Content-Type-Options': 'nosniff'
    });
    res.end(req.method === 'HEAD' ? undefined : bytes);
  } catch (error) {
    console.error('Could not read application file:', error.message);
    res.writeHead(500);
    res.end('Could not read application file. Check the terminal.');
  }
});
server.on('error', error => {
  console.error(error.code === 'EADDRINUSE'
    ? 'Port is already in use. Try: npm start -- 5501'
    : error.message);
  process.exitCode = 1;
});
server.listen(port, process.env.CINEDRAFT_HOST || '127.0.0.1', () => {
  console.log(`CineDraft: http://127.0.0.1:${server.address().port}`);
  console.log('Press Ctrl+C to stop. Edit a source file and refresh the browser.');
});
for (const signal of ['SIGINT', 'SIGTERM']) {
  process.on(signal, () => server.close());
}
