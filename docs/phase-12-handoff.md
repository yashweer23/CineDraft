# Next: Phase 12 — gameplay analytics and business intelligence

Start from this cumulative Phase 11 ZIP, API 0.11.0 and migration `0007_phase11`. Run the PostgreSQL suite locally. Preserve the original game, versioned results, comparison history and local ports 5433 / 8001 / 5174 / 5500.

Follow [Phase 12 in the project roadmap](CineDraft_Development_Roadmap.md#phase-12--add-a-small-business-intelligence-layer). Give a local operator a way to answer a product question: where do players leave a draft, and what change might help them finish?

1. Define events for starts, picks, recasts, abandonment, completions and replays. Give each event a stable identity; retrying a command must not count as another player decision. Document exactly what constitutes a session, completion and replay.
2. Separate fixture/demo sessions, internal tests and human playtests. Do not label synthetic activity as real player behavior. Keep hypothetical outcomes separate from official releases.
3. Build SQL summaries of the completion funnel, median time between rounds, talent pick rate, genre popularity and budget allocation. Include denominators, time windows, relevant version, genre and tier filters.
4. Build an internal dashboard with traceable measures, useful empty states and visible sample sizes. Respect ownership and the existing challenge embargo; avoid exposing account identifiers or private film details in public endpoints.
5. Use actual playtest observations, if available, to write a short decision memo about one interface or balance change. If no playtest data exists, label synthetic demonstrations and leave conclusions about actual players open.

Deliver a hands-on README, verifiable SQL queries, retry/ownership tests, a cumulative VS Code ZIP and a trace from at least one dashboard number back to the underlying authorized events. This is the next phase, not functionality already implemented.
