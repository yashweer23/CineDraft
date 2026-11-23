# CineDraft frontend — Phase 10

React, TypeScript and Vite. Follow the [root README](../README.md) for setup and port 5174. Use Node 24.15+ within 24.x.

`App.tsx` renders the guided studio and keeps previous inspectors under Developer tools. `AccountPanel.tsx` handles registration, login, whole-session guest claims and password change. `ChallengePanel.tsx` handles daily entries, rankings and post-deadline seed audit. `studioApi.ts` keeps tokens, exact pending requests and matching draft/roster/challenge context in memory. The studio hides release reports until the API's challenge context allows access; the backend independently enforces that embargo.

From this folder: `npm ci`, `npm test`, `npm run build`, `npm run dev -- --port 5174`. Stop Docker's web service first if using the same host port. Native Vite reads `API_PROXY_TARGET` from this folder's `.env`; root `WEB_PORT` controls Compose and the stack checker.

No token is written to browser storage. Refresh requires account sign-in or guest recovery. An uncertain draft/challenge POST must retain its exact request ID/body; see [recovery](../docs/phase-10/recovery.md). Account tokens are not displayed as guest recovery credentials.

The root README documents browser tooling. `test:browser` checks the guest flow with mock or optional live HTTP. `test:browser:phase10` checks account/challenge UI against invented HTTP responses only. Real account/database behavior still needs local integration verification. See [the packaging record](../docs/phase-10/verification.md).
