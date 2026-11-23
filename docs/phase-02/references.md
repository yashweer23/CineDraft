# Implementation references

Official sources consulted 20 October 2026. Project-specific structure, game defaults, readiness/error contracts and test strategy are CineDraft design decisions.

- [Vite guide](https://vite.dev/guide/) — development server, build and runtime requirements.
- [Tailwind with Vite](https://tailwindcss.com/docs/installation/using-vite) — Vite plugin and CSS import integration.
- [FastAPI settings](https://fastapi.tiangolo.com/advanced/settings/) — typed environment settings.
- [SQLAlchemy PostgreSQL dialect](https://docs.sqlalchemy.org/en/20/dialects/postgresql.html) — PostgreSQL driver integration; installed SQLAlchemy APIs were also exercised locally.

The installed Starlette test client source prefers `httpx2`, so the locked test dependency uses httpx2 rather than the deprecated fallback. No application code calls third-party movie APIs in this phase.
