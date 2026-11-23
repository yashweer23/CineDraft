# Run and debug CineDraft in VS Code

## Windows quick start

1. Right-click the ZIP → **Extract All**. Do not run files from inside the compressed-folder preview.
2. Open VS Code → **File → Open Folder** → choose the extracted `CineDraft-VSCode` directory. You should see `package.json`, `index.html`, `app.js` and `engine.js` at the top level.
3. Install Node.js 22 or newer if `node --version` is unavailable. Restart VS Code after installation so the terminal picks up PATH changes.
4. Open **Terminal → New Terminal** and run:

```powershell
node --version
npm start
```

5. Open `http://127.0.0.1:5500` in Chrome, Edge or Firefox.

The included server binds only to your own computer. It serves the four game files; there is no external hosting setup. No `npm install` is necessary because all runtime and test dependencies are built into Node.

If PowerShell says scripts are disabled, use `npm.cmd start` or `node scripts/serve.cjs`. You do not need to change machine-wide execution policies. If the port is occupied, run `npm start -- 5501` and open the printed URL instead. Use **Ctrl+C** in the terminal to stop.

## macOS or Linux

Open the extracted folder in VS Code, open its terminal, then run `npm start` with Node 22+. The same address and commands apply. The server resolves assets relative to its own project, not an unrelated terminal directory.

## Python alternative

If you already have Python 3, you can run the unchanged game without Node. From the project root:

Windows:

```powershell
py -m http.server 5500 --bind 127.0.0.1
```

macOS/Linux:

```sh
python3 -m http.server 5500 --bind 127.0.0.1
```

Open the same URL. This standard Python server exposes the project directory to your local browser, including documentation; keep it bound to localhost. The Node server restricts routes to game assets. The provided automated tests require Node, even if you choose Python for serving.

## Editing and debugging

- `styles.css`: colors, spacing, typography, card sizes and breakpoints.
- `app.js`: setup, draft, review, result screens; button behavior and local saves.
- `engine.js`: talent records, fit, costs, offers, affordability and release formulas.
- `index.html`: page shell, script includes and persistent header/footer.

Save a file and refresh the browser. This pack has no bundler or hot reload. The development server sends `Cache-Control: no-store`. Do not double-click `index.html` to test normal saved-game behavior: use the local HTTP URL consistently.

VS Code **Terminal → Run Task** offers “CineDraft: Start locally” and “CineDraft: Run checks.” For debugging, start the server first, choose **Run and Debug → CineDraft: Debug in Chrome (start server first)**, and press F5. Chrome must be installed for that configuration. If you use another browser, its built-in developer tools work without the VS Code launch configuration. Adjust the debug URL if you choose a different port.

Set a breakpoint inside `pick(id)` in `app.js`. Click a candidate and inspect `state.picks`, `state.hand` and `C.spent(state)`. Then step through the update and next render. For deterministic engine exploration, run:

```sh
node -e "const C=require('./engine.js'); const s=C.start('Crime',90,'My test',42); console.table(C.deal(s));"
```

This command deliberately uses the **legacy** $90M budget. The proposed $10M budget cannot be passed to the old engine without implementation changes.

## Progress and reset

Drafts and completed films are saved in the same browser under `cinedraft-v1`. `localhost`, `127.0.0.1` and different ports are different origins; pick one and keep using it. The old hosted game's browser saves are not automatically copied into this pack. They also are not contained inside the ZIP.

To clear only CineDraft's local progress, open your browser's developer console on the local game and run the following **only when you intend to delete those saved drafts and films**:

```js
localStorage.removeItem('cinedraft-v1');
location.reload();
```

## Common problems

| Symptom | Fix |
|---|---|
| `node` is not recognized | Install Node 22+ and restart VS Code |
| `ENOENT package.json` | Open the inner `CineDraft-VSCode` folder or `cd` into it |
| `npm.ps1 cannot be loaded` | Use `npm.cmd start` or `node scripts/serve.cjs` |
| `EADDRINUSE` | Stop the old server with Ctrl+C or choose `npm start -- 5501` |
| Browser refuses connection | Keep the terminal server running and use its printed host/port |
| Font differs offline | Expected system-font fallback; gameplay remains local |
| Saved games seem missing | Confirm browser/profile and exact host/port |
| New designs do not appear | Phase 1 docs describe future work; the original prototype remains unchanged |
| No actual five-film lists | The catalog/credit integration is a later implementation phase |
| F5 cannot launch Chrome | Install Chrome or use your browser normally with developer tools |

## Checks

Run `npm test` (or `npm.cmd test` on restrictive PowerShell setups). The suite checks the legacy engine across 540 drafts and the local server's routes. This is not a performance benchmark or a claim of complete browser coverage. See [verification](verification.md) for this delivery's observed results.
