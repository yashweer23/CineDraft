# Phase 2 handoff — full-stack foundation

Phase 1 delivered the six design documents and preserved the runnable Phase 0 prototype. Use this prompt when you are ready to continue in your own VS Code workspace. This pack does not automatically execute Phase 2.

## Copy-ready agent prompt

```text
Continue the existing CineDraft project with Phase 2 only: establish the full-stack development foundation.

First inspect README.md, docs/prototype-audit.md, docs/architecture.md, every document in docs/phase-01/, and the current source. Run the existing checks before modifying behavior. Explain the current structure briefly so I can understand it as I work in VS Code.

The supplied HTML/CSS/JavaScript game is a preserved Phase 0 prototype. The Phase 1 design is the future behavior, not already implemented code. Keep the prototype runnable as a reference while adding the new stack. Do not silently replace root startup commands or reuse old million-valued local saves as integer USD.

Implement:
1. A clear frontend/ backend/ data/ tests/ docs/ layout alongside the preserved prototype.
2. React + TypeScript with Vite and Tailwind, using compatible pinned versions. Build a minimal CineDraft shell and a visible backend-health result.
3. FastAPI with Pydantic configuration, typed health responses, structured errors and development-only CORS origins configured explicitly.
4. PostgreSQL development configuration and a tested database connectivity check using SQLAlchemy. Initialize Alembic configuration if useful, but leave domain models/migrations for Phase 3.
5. .env.example files with placeholders, proper .gitignore rules and startup validation. Keep secrets out of browser code and out of Git.
6. Docker Compose plus documented non-container development commands. The database must not be an undeclared external prerequisite.
7. Basic checks covering the new frontend-to-backend health flow and configuration errors. Retain the legacy engine tests with an explicit label.
8. Minimal CI for the checks you can actually run. Record exact runtime versions and lockfiles.
9. Updated README and Windows-friendly VS Code commands explaining where to run each process and how to stop it.

Preserve these future design constraints in types/config documentation: $10M/$50M/$200M integer-USD tiers; 35% non-talent production reserve; eight unique people; two offer rerolls; one final recast; verified role-specific top-five works visible on candidate cards. Do not claim these are fully implemented in this foundation phase.

Do not implement live TMDB ingestion, a production identity/account system, the complete database domain model, derived talent ratings, the collaboration graph, the authoritative drafting service, the replacement simulator, multiplayer, or deployment in this phase. Those belong to the later roadmap phases. Do not request an API key for a service this phase does not need.

Completion criteria: a fresh checkout starts from the documented commands; the React frontend calls the FastAPI health endpoint; database connectivity is demonstrated; configuration failures are understandable; the preserved prototype still runs; the relevant checks pass or specific blockers are reported honestly.

Finish with changed files, commands I should run myself, what I should see, checks performed, remaining limitations and a brief explanation of each new component. Stop after Phase 2.
```

## Review before moving on

Can you start the services yourself, explain which port belongs to which process, show a successful health response, and distinguish the local static prototype from the new frontend? If yes, proceed to Phase 3 database/API design. If not, resolve setup first; a larger feature prompt will only hide the problem.
